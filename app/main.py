#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# PATE Bias Board Evaluation Software (pbbes) 2018
#
# main.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.09.20  Initial version.
#   0.2     2018.09.22  Refactored to use widget style objects.
#   0.3     2018.09.23  Switched to curses instead of raw escape codes.
#   0.4     2018.09.30  Interval adjustments implemented.
#   0.5     2018.10.01  Serial timeouts implemented.
#   0.6     2018.10.02  Start-up screen remodeled.
#   1.0     2018.10.04  Finalized.
#
import os
import sys
import csv
import time
import curses
import serial
import logging
import logging.handlers
import platform
import argparse

__moduleName = os.path.basename(os.path.splitext(__file__)[0])
__fileName   = os.path.basename(__file__)


# Will be replaced if termination is not clean
_exit_message = "Program terminated normally."

import Widget
from KeyboardInput      import KeyboardInput, InputConsumerManagement
from Device             import Device
from IntervalScheduler  import IntervalScheduler
from startup            import startup_screen
# PEP 396 -- Module Version Numbers https://www.python.org/dev/peps/pep-0396/
__version__ = "1.0.0"
__author__  = "Jani Tammi <jasata@utu.fi>"
VERSION = __version__
HEADER  = """
=============================================================================
University of Turku, Department of Future Technologies
ForeSail-1 / PATE Bias Board Evaluation Software
Version {}, 2018 {}
""".format(__version__, __author__)

#
# Built in configuration defaults
#
class Config():
    Heartbeat   = 0.05      # Responsiveness of terminal (sec)
    Interval    = 10        # Bias Board measurement polling interval (sec)
    Timewindow  = 0.05      # Event triggering grouping tolerance (sec)
    Device      = '/dev/ttyUSB0'
    Baudrate    = 115200
    Parity      = serial.PARITY_NONE
    ByteSize    = serial.EIGHTBITS
    StopBits    = serial.STOPBITS_ONE
    Timeout     = 0.1       # 100ms for R/W timeouts
    # logging levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    LogLevel    = "DEBUG"
    @staticmethod
    def serial_parameters():
        return ",".join([
            str(Config.Baudrate),
            str(Config.ByteSize),
            str(Config.Parity),
            str(Config.StopBits)
        ])


#
# Check requirements
#
def check_requirements():
    """Silently passes or raises an exception if criterias are not met"""

    # Require Python 3.5 or newer
    v = platform.python_version_tuple()
    if (int(v[0]) < 3) or (int(v[0]) > 2 and int(v[1]) < 5):
        raise ValueError(
            "Python version 3.5 or greater is required! " +
            "Current version is {}.{}.{}"
            .format(*v)
        )


    # Require pySerial 3.3 or newer (serial.Serial(exclusive=True|False))
    # pySerial uses non-standard .VERSION instead of .__version__
    v = serial.VERSION.split('.')
    if (int(v[0]) < 3) or (int(v[0]) == 3 and int(v[1]) < 3):
        raise ValueError(
            "pySerial version 3.3 or greater required! " + \
            "(current: " + serial.VERSION + ")"
        )

    return



###############################################################################
#
# Program entry
#
if __name__ == "__main__":

    #
    # Parse commandline
    #
    def check_interval(value):
        """Custom interval argparse validator"""
        interval = int(value)
        if interval < 1 or interval > 999:
            raise argparse.ArgumentTypeError(
                "Interval must be between 1 and 999. {} is an invalid value!"
                .format(value)
            )
        return interval
    #
    parser = argparse.ArgumentParser(
        description = HEADER
    )
    parser.add_argument(
        '-d',
        '--device',
        help = "Set serial port device. Default: '{}'".format(Config.Device),
        nargs = '?',
        dest = "device",
        const = "DEVICE",
        default = Config.Device,
        type = str
    )
    parser.add_argument(
        '-l',
        '--log',
        help = "Set logging level. Default: {}".format(Config.LogLevel),
        choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        nargs = '?',
        dest = "loglevel",
        const = "LEVEL",
        default = Config.LogLevel,
        type = str.upper
    )
    parser.add_argument(
        '-i',
        '--interval',
        help = "Set measurement interval (seconds). Default: {}".format(Config.Interval),
        nargs = '?',
        dest = 'interval',
        const = 'SECONDS',
        default = Config.Interval,
        type = check_interval
    )
    args = parser.parse_args()
    Config.Device   = args.device
    Config.LogLevel = args.loglevel
    Config.Interval = args.interval

    #
    # Setup logging
    #
    logging.basicConfig(
        level       = Config.LogLevel,
        filename    = "pbbes.log",
        format      = '%(asctime)s %(levelname)s %(name)s: %(message)s',
        datefmt     = '%H:%M:%S'
    )
    log = logging.getLogger(
        __fileName + ":" + \
        sys._getframe().f_code.co_name + "()"
    )


    #
    # Log start-up messages
    #
    log.info("Program execution started (version {})".format(__version__))
    log.info("Measurement interval = {} seconds".format(Config.Interval))


    #
    # Check requirements
    #
    try:
        check_requirements()
    except ValueError as err:
        print(str(err))
        log.critical(str(err))
        os._exit(-1)


    #
    # Open serial port
    #
    try:
        dev = Device(
            device   = Config.Device,
            baudrate = Config.Baudrate,
            parity   = Config.Parity,
            stopbits = Config.StopBits,
            bytesize = Config.ByteSize,
            timeout  = Config.Timeout
        )
        # Log it and dev.version() issues a VERS? command to test connectivity
        log.info(
            "Device '{}' ({}) connected to Bias Board '{}'"
            .format(
                Config.Device,
                dev.serial_parameters(),
                dev.version()
            )
        )
    except serial.serialutil.SerialException as err:
        log.exception("Unable to communicate with the serial port!")
        print("To allow non-root user access to serial device:")
        print("    sudo usermod -a -G dialout $USER")
        print(str(err))
        os._exit(-1)
    except ValueError as err:
        log.exception("{} ({})".format(err, dev.serial_parameters()))
        print(
            "Unsuccessful communication test on port '{}' ({})!"
            .format(Config.Device, dev.serial_parameters())
        )
        print(str(err))
        os._exit(-1)
    except:
        log.exception("Unable to communicate with bias board!")
        print("Unexpected error! Please see pbbes.log for details.")
        os._exit(-1)



    #
    # Start-up screen (ask for optional label for CSV header)
    #
    #       User can give a label (stored in the CSV header).
    #       Start-up also calibrates(?) the bias board by issuing
    #       'RRR' -command twice (as requested by Philipp).
    #
    try:
        # Execute start-up procedures and receive Device instance and label str
        label = startup_screen(dev, HEADER)
    except:
        log.exception("Start-up procedures failed!")
        print("Program execution terminated abnormally. See 'pbbes.log'")
        os._exit(-1)


    #
    # Create Main UI and start executing
    #
    try:
        # Initialize curses
        stdscr = Widget.init()

        # Setup event scheduler (IntervalWidget needs it)
        event = IntervalScheduler(
            Config.Heartbeat,
            Config.Interval,
            Config.Timewindow
        )

        # Create (and draw) Widgets
        with \
        Widget.TableWidget(device = dev) as tbl, \
        Widget.PWMLabelWidget() as lbl, \
        Widget.PWMWidget(device = dev, channel = 1) as pwm1, \
        Widget.PWMWidget(device = dev, channel = 2) as pwm2, \
        Widget.PWMWidget(device = dev, channel = 3) as pwm3, \
        Widget.PWMWidget(device = dev, channel = 4) as pwm4, \
        Widget.IntervalWidget(scheduler = event) as ivc, \
        KeyboardInput() as keyboard:

            # Register widgets as input consumers
            # See KeyboardInput.py for implementation details
            manage = InputConsumerManagement()
            manage.add(pwm1)
            manage.add(pwm2)
            manage.add(pwm3)
            manage.add(pwm4)
            manage.add(ivc)

            # Enable data logging into CSV file
            tbl.set_csv_writer(label)

            # (re)start timers
            event.restart()

            while True:
                # Sleep until next event
                if event.next() & event.MEASUREMENT:
                    # get and draw
                    tbl.get()
                # Handle keyboard input on every event
                for key in keyboard:
                    manage.input(key)

    except KeyboardInterrupt:
        log.debug("Program terminated with CTRL-C")
    except:
        log.exception("Abnormal program termination!")
        _exit_message = \
            "\u001b[31;1m" \
            "Abnormal program termination! See log for details." \
            "\u001b[0m"
    finally:
        # Cleanup on exit
        Widget.cleanup()
        print(_exit_message)

# EOF