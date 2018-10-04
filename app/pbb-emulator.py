#! /usr/bin/env python3
#
# pbb-emulator.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.09.23  Initial version.
#   0.2     2018.09.25  Modified to match protocol changes of 2018-09-25.
#   0.3     2018.09.16  Commandline arguments added.
#   1.0     2018.10.04  RRR command added, finalized.
#
#   PATE Bias Board (limited) emulator
#   For developing PBBES software
#   Needs pyserial (ver.3.3+) module:
#
#       pip3 install pyserial
#
#   Implements:
#       VERS?
#       MEASnn?
#       PWMn?
#       PWMnSxxx
#       RRR
#
#
import os
import sys
import time
import random
import serial
import platform
import argparse

__version__ = "1.0"
__fileName   = os.path.basename(__file__)


# Initial PWM channel values
_pwm = [0, 25, 25, 25, 35]

class Cfg:
    device   = "/dev/ttyUSB0"
    baudrate = 115200
    bits     = serial.EIGHTBITS
    parity   = serial.PARITY_NONE
    stopbits = serial.STOPBITS_ONE
    @staticmethod
    def serial_parameters():
        def bits(v):
            if v == serial.EIGHTBITS:
                return '8'
            elif v == serial.SEVENBITS:
                return '7'
            elif v == serial.SIXBITS:
                return '6'
            elif v == serial.FIVEBITS:
                return '5'
            else:
                return '?'
        def parity(v):
            if v == serial.PARITY_NONE:
                return 'N'
            elif v == serial.PARITY_EVEN:
                return 'E'
            elif v == serial.PARITY_ODD:
                return 'O'
            elif v == serial.PARITY_MARK:
                return 'M'
            elif v == serial.PARITY_SPACE:
                return 'S'
            else:
                return '?'
        def stopbits(v):
            if v == serial.STOPBITS_ONE:
                return '1'
            elif v == serial.STOPBITS_ONE_POINT_FIVE:
                return '1.5'
            elif v == serial.STOPBITS_TWO:
                return '2'
            else:
                return '?'
        return ",".join([
            str(Cfg.baudrate),
            bits(Cfg.bits),
            parity(Cfg.parity),
            stopbits(Cfg.stopbits)
        ])

def meas(code):
    if code in ['00', '01', '02', '03']:
        return "{:03} V\nOK\n".format(random.randint(0,999))
    elif code in ['04', '05', '18']:
        return "{:04} mV\nOK\n".format(random.randint(0,9999))
    elif code in ['06', '10', '11', '12', '13', '15', '17']:
        return "{:02} mA\nOK\n".format(random.randint(0,99))
    elif code in ['14', '16']:
        return "{:02} C\nOK\n".format(random.randint(0,99))
    elif code == '99':
        def mA():
            m = random.randint(-99,99)
            return "{1:0{0}d}".format(2 if m >=0 else 3, m)
        return  "{:03} {:03} {:03} {:03} {:04} {:04} {} " \
                "0 0 0 {} {} {} {} {:02} {} {:02} {} {:04}\nOK\n" \
                .format(
                    random.randint(0,999),  # 00 Bias V T1D1
                    random.randint(0,999),  # 01 Bias V T1D2
                    random.randint(0,999),  # 02 Bias V T2D1
                    random.randint(0,999),  # 03 Bias V T2D2
                    random.randint(0,9999), # 04 MOSFET #1
                    random.randint(0,9999), # 05 MOSFET #2
                    mA(),                   # 06 Total Bias generator supply current
                    mA(),                   # 10 Bias mA T1D1
                    mA(),                   # 11 Bias mA T1D2
                    mA(),                   # 12 Bias mA T2D1
                    mA(),                   # 13 Bias mA T2D2
                    random.randint(0,70),   # 14 Temp near board supply voltage converters
                    mA(),                   # 15 Current consump. by amp AD8236
                    random.randint(0,70),   # 16 Temp near bias high voltage converters
                    mA(),                   # 17 Current consump. by amp OP481
                    random.randint(0,3400)  # 18 Analog supply voltage 3V3
                )
    else:
        return "ERROR\n"

def rrr(bus):
    def w(s):
        bus.write(s.encode('ascii'))
        print(s, end='')
    w("Zero levels are to be calibrated.\n")
    w("Shutting down, please wait")
    for i in "..........":
        time.sleep(0.5) # seems to be 500ms between dots... ("SW Ver 0.5a built Sep 25 2018")
        w(i)
    w("\n")
    w("6       19      36      -7      296\n")
    w("OK\n")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description = \
        "University of Turku, Department of Future Technologies\n" + \
        "Foresail-1 / PATE Bias Board emulator (for developing pbbes)\n" + \
        "pbb-emulator version {}, 2018 <jasata@utu.fi>\n".format(__version__)
    )
    parser.add_argument(
        '-p',
        '--port',
        help = "Set serial port device",
        nargs = '?',
        dest = "port",
        const = "PORT",
        default = Cfg.device,
        type = str
    )
    args = parser.parse_args()
    Cfg.device = args.port

    print("{} version {}".format(__fileName, __version__))
    print(
        "Running on Python ver.{} on {} {}" \
        .format(
            platform.python_version(),
            platform.system(),
            platform.release()
        )
    )
    print("pySerial ver.{}".format(serial.VERSION))
    print(
        "Opening {} ({})..."
        .format(
            Cfg.device,
            Cfg.serial_parameters()
        ),
        end = ''
    )
    bus = serial.Serial(
        port          = Cfg.device,
        baudrate      = Cfg.baudrate,
        bytesize      = Cfg.bits,
        parity        = Cfg.parity,
        stopbits      = Cfg.stopbits,
        timeout       = None,
        write_timeout = None,
        exclusive     = True
    )
    print(" '{}' OK".format(bus.name))
    print(_pwm)
    print("Waiting for commands...")

    #
    # Main loop
    #
    try:
        while True:
            reply = ""
            cmd = bus.readline().decode('ascii', 'ignore')[:-1]
            print(cmd + " ", end = '')

            # process command
            if cmd[:4] == 'MEAS':
                nn = cmd[4:6]
                reply = meas(nn)
            elif cmd == 'VERS?':
                reply = "{} version {}\nOK\n".format(__fileName, __version__)
            elif cmd[:3] == 'PWM' and cmd[4:5] == 'S':
                # PWMnSxxx
                print(_pwm)
                try:
                   n = int(cmd[3:4])
                except:
                   n = -1
                if n not in (1, 2, 3, 4):
                    print("Invalid selector n={} ".format(n), end='')
                    reply = "ERROR\n"
                else:
                    try:
                        x = int(cmd[5:8])
                        _pwm[n] = x
                        reply = "{:03}\nOK\n".format(x)
                    except:
                        print("Error setting _pwm[{}] = {} ".format(n, cmd[5:8]), end='')
                        reply = "ERROR\n"
            elif cmd[:3] == 'PWM' and cmd[4:5] == '?':
                try:
                    n = int(cmd[3:4])
                except:
                    n = -1
                if n in (1,2,3,4):
                    reply = "{:03}\nOK\n".format(_pwm[n])
                else:
                    reply = "ERROR\n"
            elif cmd == 'RRR':
                rrr(bus)
                continue    # Do not go down to the usual bus.write()!
            else:
                reply = "ERROR\n"
                print(
                    "unrecognized command '{}'! " \
                    .format(cmd),
                    end = ''
                )
            bus.write(reply.encode('ascii'))
            print("'" + reply.replace('\n', '\\n') + "'")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print('interrupted!')
        bus.close()

# EOF
