#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# PATE Bias Board Evaluation Software (pbbes) 2018
#
# Device.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.09.22  Initial version.
#   0.2     2018.10.01  Timeouts implemented.
#   1.0     2018.10.04  Finalized for release.
#
# REQUIRES pySerial version 3.3 or greater!
# serial.Serial(exclusive=True|False)
#
# Class modeling PATE Bias Board. Implements protocol and provides
# few other features...
import os
import sys
import time
import serial
import select
import logging

_moduleName = os.path.basename(os.path.splitext(__file__)[0])
_fileName   = os.path.basename(__file__)

class Device:
    port        = None
    cmds        = []        # list of issued (state altering) commands
    logfile     = None
    def __init__(
        self,
        device      = '/dev/ttyUSB0',
        baudrate    = 115200,
        parity      = None,
        bytesize    = 8,
        stopbits    = 1,
        timeout     = None,
        log         = True
    ):
        self.port = serial.Serial(
            port          = device,
            baudrate      = baudrate,
            parity        = parity,
            bytesize      = bytesize,
            stopbits      = stopbits,
            timeout       = timeout,
            write_timeout = timeout,
            exclusive     = True
        )
        self.port.flushInput()
        if log is True:
            self.logfile = open(
                "serial.log",
                'w',
                buffering = 1
            )
    def version(self):
        return self.__transact('VERS?\n')
    def meas(self, n):
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        try:
            # .__trasact() checks for 'OK' already
            val = self.__transact('MEAS{:02}?\n'.format(n))
            if n in (0,1,2,3):
                return int(val[:3])
            elif n in (4,5,18):
                return int(val[:4])
            elif n in (6,10,11,12,13,15,17):
                return int(val[:2])
            elif n in (14,16):
                return int(val[:2])
            elif n == 99:
                return [int(x) for x in val.split()]
            else:
                log.critical("Unhandled selector n={}!".format(n))
                return 'n={:02}'.format(n)
        except KeyboardInterrupt:
            # User CTRL-C terminate, do not report, re-raise
            raise
    def pwm(self, n, x = None):
        """Get/Set PWM<n> duty cycle value
        Without x or x == None: PWMn? otherwise: PWMnSx"""
        # Exceptions fall through - we cannot tolerate protocol failures
        # during state altering commands. Let it crash.
        if x is None:
            cmd = 'PWM{}?\n'.format(n)
            val = self.__transact(cmd)
        else:
            cmd = 'PWM{}S{:03}\n'.format(n, x)
            val = self.__transact(cmd)
            self.cmds.append(cmd)
        return int(val)
    def commands(self):
        """Return all state altering stored commands as a comma separated list
        and delete all stored commands from the list."""
        cmds = ",".join(self.cmds).replace('\n', ' ')
        del self.cmds[:]
        return cmds
    def serial_parameters(self):
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
            str(self.port.baudrate),
            bits(self.port.bytesize),
            parity(self.port.parity),
            stopbits(self.port.stopbits)
        ])

    def _write(self, cmd):
        """Simply records the sent command into serial.log and writes it out"""
        try:
            self.port.write(cmd.encode('utf-8'))
        except serial.serialutil.SerialTimeoutException as err:
            log.exception("Serial write timeout!")
            raise
        if self.logfile is not None:
            self.logfile.write(cmd)
    def _read(self, timeout = 1, size = 1024):
        """Reads up to 1kB and writes the response into serial.log.
        timeout parameter is seconds. Raises ValueError on timeout.
        NOTE: port must be in non-blocking mode!"""
        try:
            rlist, _, _ = select.select([self.port], [], [], timeout)
            if not rlist: # timeout
                raise ValueError(
                    "Port read timeout ({}) exceeded!"
                    .format(timeout)
                )
            # else there is data, read (non-blocking)
            chunk = self.port.read(size = size).decode('ascii')
            if self.logfile is not None:
                self.logfile.write(chunk)
            return chunk
        except KeyboardInterrupt:
            # User CTRL-C terminate, do not report, re-raise
            raise
        except:
            # Report and re-raise all other exceptions
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).exception("Serial read failure!")
            raise

    def __transact(self, cmd):
        """Send command and read reply until OK<LF> or ERROR<LF>
        Returns a reply string (or "OK", if reply has no message)
        or raises an exception."""
        def readln():
            log = logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            )
            try:
                # .readline() returns bytes until '\n' or
                # as much as is available when timeout occurs
                line = self.port.readline()
                # If the last character is not '\n', we had a timeout
                if line[-1:] != b'\n':
                    raise ValueError(
                        "Serial read timeout! ({}s)".format(self.port.timeout)
                    )
                # REALLY confusing... returned type absolutely should be bytes!
                #line = self.port.readline().decode('ascii', 'ignore')[:-1]
                # Success: return decoded value
                return line[:-1].decode('utf-8')
            except KeyboardInterrupt:
                # User CTRL-C terminate, do not report, re-raise
                raise
            except ValueError:
                # Timeout! Let 200 ms pass and discard input buffer
                time.sleep(0.2)
                self.port.flushInput()
                raise
            except:
                log.exception("Unexpected exception during .readln()!")
                raise
        # __transact() block begins
        try:
            self.port.write(cmd.encode('utf-8'))
        except serial.serialutil.SerialTimeoutException as err:
            log.exception("Serial write timeout!")
            raise
        if self.logfile is not None:
            self.logfile.write(cmd)
        # Give the bias board little time to respond
        #time.sleep(0.05)
        # Read response(s)
        response = '(uninitialized)'
        try:
            response = readln()
            if self.logfile is not None:
                self.logfile.write(response + '\n')
            if response == 'OK':
                return response
            elif response == 'ERROR':
                raise ValueError("Device replied 'ERROR'")
            else:
                value = response
                response = readln()
                if self.logfile is not None:
                    self.logfile.write(response + '\n')
                if response == 'OK':
                    return value
                else:
                    raise ValueError("Device did not end with 'OK'")
        except (KeyboardInterrupt, ValueError):
            # User CTRL-C terminate, do not report, re-raise
            raise
        except:
            # Report and re-raise all other exceptions
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).exception(
                "Serial command-response transaction failure! response:'{}'"
                .format(response)
            )
            raise
    # support for with -statement
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.port is not None:
            self.port.close()


# EOF
