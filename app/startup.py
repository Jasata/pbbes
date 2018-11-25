#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# PATE Bias Board Evaluation Software (pbbes) 2018
#
# startup.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.10.01  Initial version.
#   0.2     2018.10.02  Nearly completed (missing 'RRR' handling)
#   1.0     2018.10.04  Implemented 'RRR' calibration. Finalized.
#   1.0     2018.11.25  Fixed script name in this header.
#
#       Start-up screen that allows the operator to enter a free-form string
#       'label' (to be writting in the CSV header).
#       Performs calibration(?) by issuing command ('RRR') twice, as specified.
#
import os
import sys
import time
import serial
import logging
import platform

__moduleName = os.path.basename(os.path.splitext(__file__)[0])
__fileName   = os.path.basename(__file__)


ESC = '\x1b['     # Actually, '\x1b', but all sequences here also use '['
def _(s):
    sys.stdout.write(s)
    sys.stdout.flush()

class terminal:
    @staticmethod
    def erase():
        _(ESC + '2J')
    @staticmethod
    def clear():
        _(ESC + 'c')
    @staticmethod
    def home():
        _(ESC + 'H')
    @staticmethod
    # zero indeces, Y starts from up, X from left
    def move(x, y):
        _(ESC + '{};{}H'.format(str(y),str(x)))
    @staticmethod
    def reset_font():
        _(ESC + '0m')
    @staticmethod
    def set_bold():
        _(ESC + '1m')
    @staticmethod
    def set_dim():
        _(ESC + '2m')
    @staticmethod
    def set_standout():
        _(ESC + '3m')
    @staticmethod
    def set_underline():
        _(ESC + '4m')
    @staticmethod
    def set_blink():
        _(ESC + '5m')
    @staticmethod
    # General code '6m' is unknown to me
    def set_revered():
        _(ESC + '7m')
    @staticmethod
    def set_invisible():
        _(ESC + '8m')
    @staticmethod
    def set_black():
        _(ESC + '30m')
    @staticmethod
    def set_red():
        _(ESC + '31m')
    @staticmethod
    def set_green():
        _(ESC + '32m')
    @staticmethod
    def set_yellow():
        _(ESC + '33m')
    @staticmethod
    def set_blue():
        _(ESC + '34m')
    @staticmethod
    def set_magenta():
        _(ESC + '35m')
    @staticmethod
    def set_cyan():
        _(ESC + '36m')
    @staticmethod
    def set_white():
        _(ESC + '37m')


def show_system_info():
    print(
        "Running on Python ver.{} on {} {}" \
        .format(
            platform.python_version(),
            platform.system(),
            platform.release()
        )
    )
    # If the number of cores cannot be determined, multiprocessing.cpu_count()
    # raises NotImplementedError, but os.cpu_count() returns None.
    print(
        "{} cores are available ({} cores in current OS)" \
        .format(
            os.cpu_count() or "Unknown number of",
            platform.architecture()[0]
        )
    )
    print("pySerial ver.{}\n".format(serial.VERSION))



#
# Module's "main" function
#
def startup_screen(dev, hdr):
    """Queries operator for 'label' which will be stored in CSV header.
    Also calibrates the bias board by issuing 'RRR' -command twice.
    (As has been requested)"""
    log = logging.getLogger(
        __fileName + ":" + \
        sys._getframe().f_code.co_name + "()"
    )
    log.debug("Start-up screen ")


    terminal.erase()
    terminal.home()
    terminal.set_bold()
    terminal.set_blue()
    print(hdr)
    show_system_info()
    terminal.reset_font()

    sys.stdin.flush()
    label = input("Enter label/note for the session (max 80 characters):\n")


    #
    # Calibration ('RRR')
    #
    #       This is not implemented into the Device.py:Device class because
    #       unlike other command-response type transactions, this command will
    #       output dots ('.') every 500ms while waiting for the capacitors to
    #       discharge. How long does this take (or thus, the number of dots)
    #       cannot be predetermined.
    #
    #       Following requirements are set for this functionality:
    #       - Output needs to be shown to the operator realtime.
    #       - Timeout/failure should be assumed if no new data (dots) have
    #         arrived for 1000 ms. (bias board fails to complete the cycle)
    #       - Transaction is completed only by either "ERROR\n" or "OK\n"
    #
    old_serial_timeout = dev.port.timeout
    dev.port.timeout = 0 # non-blocking
    # Do it twice
    for n in range(0, 2):
        terminal.set_yellow()
        print("Calibration #{}".format(n + 1))
        terminal.reset_font()
        dev._write("RRR\n")
        buffer = ''
        try:
            while True:
                chunk = dev._read(timeout = 1, size = 1024)
                print(chunk, end='')
                sys.stdout.flush()
                buffer += chunk
                if buffer[-3:] == 'OK\n':
                    break
                if buffer[-6:] == 'ERROR\n':
                    log.error("Calibration failure!")
                    raise ValueError("Calibration ('RRR') failure!")
        except Exception as err:
            log.exception("Exception while calibrating!")
            raise
        time.sleep(0.2) # Little delay before second calibration

    # Restore (read) timeout and return with label
    dev.port.timeout = old_serial_timeout
    log.debug(
        "Calibration complete! Serial port read timeout (re)set to '{}'"
        .format(dev.port.timeout)
    )


    #
    # Return with label (max 80 characters)
    #
    return label[:80]

# EOF
