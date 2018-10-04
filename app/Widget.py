#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# PATE Bias Board Evaluation Software (pbbes) 2018
#
# Data.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.09.22  Initial version.
#   0.2     2018.09.23  Modified to use curses instead of war escape sequences
#   0.3     2018.09.30  Clean-up.
#   1.0     2018.10.04  Finalized for release.
#
# ASCII display components/widgets.
import os
import sys
import csv
import time
import random
import curses
import logging
import datetime

# Module privates
_moduleName = os.path.basename(os.path.splitext(__file__)[0])
_fileName   = os.path.basename(__file__)
_screen     = None      # curses screen

# curses color pair identifiers
PWM_INACTIVE    = 0x01
PWM_ACTIVE      = 0x02
IVAL_INACTIVE   = 0x03
IVAL_ACTIVE     = 0x04
EXIT_INACTIVE   = 0x05
FIELD_INACTIVE  = 0x0a
FIELD_ACTIVE    = 0x0b

def init():
    global _screen
    _screen = curses.initscr()  # initialize curses screen

    # Verify that we have standard screen dimensions (or greater)
    _screen.clear()
    ydim, xdim = _screen.getmaxyx()
    if ydim < 24 or xdim < 80:
        raise ValueError(
            "Minimum supported terminal dimensions are 80x24 characters! " +
            "Current: {}x{}".format(xdim, ydim)
        )

    curses.noecho()             # turn off auto echoing of keypress on to screen
    curses.cbreak()             # enter break mode where pressing Enter key
                                # after keystroke is not required for it to register
    curses.curs_set(False)      # Hide cursor
    _screen.keypad(1)           # enable special Key values such as curses.KEY_LEFT etc

    # curses: 8 basic colors
    #   1 COLOR_BLACK   2 COLOR_RED     3 COLOR_GREEN   4 COLOR_YELLOW
    #   5 COLOR_BLUE    6 COLOR_MAGENTA 7 COLOR_CYAN    8 COLOR_WHITE
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(PWM_INACTIVE,      curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(PWM_ACTIVE,        curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(IVAL_INACTIVE,     curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(IVAL_ACTIVE,       curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(EXIT_INACTIVE,     curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(FIELD_INACTIVE,    curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(FIELD_ACTIVE,      curses.COLOR_BLACK, curses.COLOR_WHITE)

    logging.getLogger(
        _fileName + ":" + \
        sys._getframe().f_code.co_name + "()"
    ).debug("Terminal initialization complete")
    return _screen

def cleanup():
    # Cleanup on exit, restore terminal
    # To be called by main.py's try .. finally
    if _screen is not None:
        _screen.keypad(0)
    curses.echo()
    curses.nocbreak()
    curses.endwin()     # Without this call, termial will remain screwed
    logging.getLogger(
        _fileName + ":" + \
        sys._getframe().f_code.co_name + "()"
    ).debug("Terminal clean up complete")


###############################################################################
# Class that implements measurement table's ASCII display
###############################################################################
class TableWidget():
    xpos    = 0
    ypos    = 0
    rows    = 19    # number of data rows
    data    = []
    csvfile = None
    csvwrtr = None
    def __init__(self, device, xpos = None, ypos = None):
        assert(_screen is not None)
        self.xpos   = xpos or self.xpos
        self.ypos   = ypos or self.ypos
        self.Device = device
        for _ in range(0, self.rows):
            self.data.append(None)
        self.get() # Retrieve first row and display
    def set_csv_writer(self, label = None):
        """Create CSV file and write headers"""
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        try:
            self.csvfile = open(
                time.strftime(
                    "%Y-%m-%d %H.%M.%S.csv",
                    time.localtime(time.time())
                ),
                'w'
            )
            self.csvwrtr = csv.writer(self.csvfile, dialect = 'excel')
            # Meta-header
            self.csvwrtr.writerow((
                'Started',
                time.strftime(
                    "%Y-%m-%d %H.%M.%S",
                    time.localtime(time.time())
                )
            ))
            self.csvwrtr.writerow(('Label', label))
            self.csvwrtr.writerow(('Firmware', self.Device.version()))
            # Data header
            self.csvwrtr.writerow(self.__csv_header())
        except:
            log.exception("Failed creating CSV file!")
            raise
        log.debug("File '{}' opened".format(self.csvfile.name))
        # return handle in case caller wants to mess with it
        # closing of the file is taken care of in __exit__()
        return self.csvfile
    def add(self, row):
        # Add to end, remove from beginning
        self.data.append(row)
        self.data.pop(0)
        # write CSV
        if self.csvwrtr is not None:
            self.csvwrtr.writerow(row)
    def clear():
        assert(_screen is not None)
        _screen.clear() # TODO: clear only widget portion
        _screen.refresh()
    def draw(self):
        assert(_screen is not None)
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        # two-row header on top
        _screen.addstr(
            self.ypos, self.xpos,
            "Time     I(t) T1D1 T1D2 T2D1 T2D2 T1D1 T1D2 T2D1 T2D2 FET1 FET2 Supp Supp Bias  ",
            curses.A_REVERSE
        )
        _screen.addstr(
            self.ypos + 1, self.xpos,
            "           mA    V    V    V    V   mA   mA   mA   mA   mV   mV   mV   'C   'C  ",
            curses.A_REVERSE
        )
        # Start printing self.data list from row to
        y = 2
        for row in self.data:
            rowstr = ""
            if row is not None:
                # Skip last (assumed to be "commands" column)
                for val in row[:-1]:
                    if isinstance(val, str):
                        rowstr += " {} ".format(val[0:3])
                    elif isinstance(val, datetime.datetime):
                        rowstr+= val.strftime("%H:%M:%S ")
                    elif isinstance(val, int):
                        rowstr += '{:4d} '.format(val)
                    elif isinstance(val, float):
                        rowstr += str(val).zfill(4) + ' '
                    else:
                        rowstr += ' (?) '
                        log.error(
                            'Unhandled Type: ' + str(type(val)) + ' "' + str(val) + '"'
                        )
                # If last (and hidden) column contains something, they are
                # issued commands. Bold such rows to indicate post-command data
                _screen.addstr(
                    self.ypos + y, self.xpos, rowstr[:80].ljust(80),
                    curses.A_BOLD if row[-1] != '' else curses.A_NORMAL
                )
            y += 1
        _screen.refresh()
    def get(self):
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        try:
            meas = self.Device.meas(99)
        except KeyboardInterrupt:
            raise
        except ValueError as err:
            # Fake it, so that the user still sees a row for this interval tick
            log.error("MEAS99? query failure! '{}'".format(err))
            meas = ['ERR' for x in range(0,19)]
        if isinstance(meas, list):
            # .add() will also write CSV row
            self.add(
                (
                datetime.datetime.now(),
                meas[6],
                meas[0],
                meas[1],
                meas[2],
                meas[3],
                meas[10],
                meas[11],
                meas[12],
                meas[13],
                meas[4],
                meas[5],
                meas[18],
                meas[14],
                meas[16],
                self.Device.commands()
                )
            )
            self.draw()
        else:
            log.error("Device.meas(99) returned type '{}'".format(type(meas)))
    def __csv_header(self):
        return (
            "Datetime",
            "Total bias generators supply current (mA)",
            "Bias voltage Tube 1 Detector 1 (V)",
            "Bias voltage Tube 1 Detector 2 (V)",
            "Bias voltage Tube 2 Detector 1 (V)",
            "Bias voltage Tube 2 Detector 2 (V)",
            "Bias generator supply current Tube 1 Detector 1 (mA)",
            "Bias generator supply current Tube 1 Detector 2 (mA)",
            "Bias generator supply current Tube 2 Detector 1 (mA)",
            "Bias generator supply current Tube 2 Detector 2 (mA)",
            "Radiation sensing MOSFET 1 drain voltage (mV)",
            "Radiation sensing MOSFET 2 drain voltage (mV)",
            "Analog Supply voltage (mV)",
            "Supply voltage converter temperature (C)",
            "Bias (high voltage) converter temperature (C)",
            "Commands"
        )
    # support with -statement
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.csvfile is not None:
            self.csvfile.close()
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).debug("File '{}' closed".format(self.csvfile.name))




###############################################################################
# PWM LABEL Widget - The right most static
###############################################################################
class PWMLabelWidget():
    xpos    = 0
    ypos    = 21
    def __init__(self, xpos = None, ypos = None):
        self.xpos = xpos or self.xpos
        self.ypos = ypos or self.ypos
        self.draw()
    def draw(self):
        # PWM Label widget takes 6 characters in width
        assert(_screen is not None) # global _screen
        header  = "      "
        value   = "VALUE "
        bottom  = header
        try:
            _screen.addstr(self.ypos,     self.xpos, header, curses.A_REVERSE)
            _screen.addstr(self.ypos + 1, self.xpos, value,  curses.A_NORMAL)
            _screen.addstr(self.ypos + 2, self.xpos, bottom, curses.A_NORMAL)
        except curses.error:
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).exception(".xpos={}, .ypos={}".format(self.xpos, self.ypos))
        _screen.refresh()
    # support with -statement
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        pass

###############################################################################
# New PWM Widget - instantiate one for each PWM
###############################################################################
class PWMWidget():
    xpos    = None
    ypos    = 21
    channel = None
    device  = None
    # Input consumer
    active  = False
    trigger = None
    buffer  = ''
    value   = 999
    def __init__(
        self,
        device,
        channel,
        trigger     = None,
        xpos        = None,
        ypos        = None
    ):
        assert(_screen is not None) # module-global _screen
        assert(channel > 0 and channel < 5)
        self.xpos    = xpos or (6 + (channel - 1) * 11)
        self.ypos    = ypos or self.ypos
        self.channel = channel
        self.trigger = trigger or 'F' + str(channel)
        self.device  = device
        self.value   = self.device.pwm(self.channel)
        self.draw()
    def draw(self):
        # Each PWM widget takes 11 characters in width
        assert(_screen is not None) # global _screen
        _p = _screen.addstr
        x = self.xpos
        y = self.ypos
        label   = "     PWM{:d}  ".format(self.channel)
        button  = " F{0:d} PWM{0:d} ".format(self.channel)
        if self.active:
            value   = "{:03d}-> {:>3}".format(self.value, self.buffer)
        else:
            value   = "      {:03d}  ".format(self.value)
        try:
            _p(y,     x, label,  curses.A_REVERSE)
            if self.active:
                _p(y + 1, x, value,  curses.color_pair(FIELD_ACTIVE))
                _p(y + 2, x, button, curses.color_pair(PWM_ACTIVE))
            else:
                _p(y + 1, x, value,  curses.color_pair(FIELD_INACTIVE))
                _p(y + 2, x, button, curses.color_pair(PWM_INACTIVE))
        except curses.error:
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).exception(
                "channel={}, xpos={}, ypos={}, buffer='{}'"
                .format(self.channel, self.xpos, self.ypos, self.buffer)
            )
        _screen.refresh()
    def process_input(self, key):
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        # inactive
        if self.active == False:
            if key == self.trigger:
                self.active = True
                log.debug("ch{} input activated".format(self.channel))
        # active
        elif key in ("ESC", self.trigger):
            self.buffer = ''
            self.active = False
            log.debug("ch{} input deactivated".format(self.channel))
        elif key in ("DEL", "BACKSPACE"):
            if len(self.buffer) > 0:
                self.buffer = self.buffer[:-1]
        elif key == "ENTER":
            log.debug("buffer='{}', value={}".format(self.buffer, self.value))
            if self.buffer != '':
                self.__set(int(self.buffer))
                self.buffer = ''
                log.info("ch{} PWM set to {}".format(self.channel, self.value))
            else:
                log.debug("buffer was empty, value not set!")
            self.active = False
        elif len(key) == 1 and key.isdigit():
            if len(self.buffer) < 3:
                self.buffer += key
            else:
                curses.beep()
        else:
            curses.beep()
            log.debug(
                "ch{} input: {} (len: {})"
                .format(self.channel, key, len(key))
            )
        # Always draw and return
        self.draw()
        return self.active
    def __set(self, val):
        """Issue PWMnSxxx command"""
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        try:
            self.value = self.device.pwm(self.channel, val)
            self.draw()
        except:
            log.exception("Set PWM{} failed!".format(self.channel))
            # This should be notified to user somehow in the UI
    def __get(self):
        """PWMn? command"""
        try:
            self.value = self.device.pwm(self.channel)
        except:
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).exception("Get PWM{} failed!".format(self.channel))
        return self.value
    # support with -statement
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        pass



###############################################################################
# Class that implements Interval ASCII display
###############################################################################
class IntervalWidget():
    xpos            = 50
    ypos            = 21
    scheduler       = None      # obj reference to IntervalScheduler instance
    # Input consumer
    active          = False
    trigger         = 'F9'
    buffer          = ''
    def __init__(
        self,
        xpos            = None,
        ypos            = None,
        trigger         = None,
        scheduler       = None
    ):
        assert(_screen is not None)
        self.xpos       = xpos or self.xpos
        self.ypos       = ypos or self.ypos
        self.trigger    = trigger or self.trigger
        self.scheduler  = scheduler
        self.draw()
    def draw(self):
        from main import __version__ as app_version
        assert(_screen is not None)
        width = 80 - self.xpos
        version_string = ("ver." + app_version + " ").rjust(width)
        try:
            _screen.addstr(
                self.ypos, self.xpos,
                version_string,
                curses.A_REVERSE
            )
            if self.active:
                _screen.addstr(self.ypos + 1, self.xpos, " " * 28, curses.A_NORMAL)
                _screen.addstr(
                    self.ypos + 1, self.xpos,
                    "  {:3d} -> {:>3} "
                    .format(self.scheduler.measurement(), self.buffer),
                   curses.color_pair(FIELD_ACTIVE)
                )
                _screen.addstr(
                    self.ypos + 2, self.xpos,
                    " F9 Interval ",
                    curses.color_pair(IVAL_ACTIVE)
                )
            else:
                _screen.addstr(self.ypos + 1, self.xpos, " " * 30, curses.A_NORMAL)
                _screen.addstr(
                    self.ypos + 1, self.xpos,
                    "    Interval: {:3d} seconds"
                    .format(self.scheduler.measurement()),
                   curses.color_pair(FIELD_INACTIVE)
                )
                _screen.addstr(
                    self.ypos + 2, self.xpos,
                    " F9 Interval ",
                    curses.color_pair(IVAL_INACTIVE)
                )
            _screen.addstr(
                self.ypos + 2, self.xpos + 15,
                " CTRL+C Quit ",
                curses.color_pair(EXIT_INACTIVE)
            )
        except curses.error:
            logging.getLogger(
                _fileName + ":" + self.__class__.__name__ + "." + \
                sys._getframe().f_code.co_name + "()"
            ).exception(
                "xpos={}, ypos={}, buffer='{}'"
                .format(self.xpos, self.ypos, self.buffer)
            )
        _screen.refresh()
    def process_input(self, key):
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        # inactive
        if self.active == False:
            if key == self.trigger:
                self.active = True
                log.debug("Input activated")
        # active
        elif key in ("ESC", self.trigger):
            self.buffer = ''
            self.active = False
            log.debug("Input deactivated")
        elif key in ("DEL", "BACKSPACE"):
            if len(self.buffer) > 0:
                self.buffer = self.buffer[:-1]
        elif key == "ENTER":
            log.debug(
                "buffer='{}', value={}"
                .format(self.buffer, self.scheduler.measurement())
            )
            if self.buffer != '':
                self.scheduler.measurement(int(self.buffer))
                self.buffer = ''
                log.info(
                    "Interval set to {}"
                    .format(self.scheduler.measurement())
                )
            else:
                log.debug("buffer was empty, value not set!")
            self.active = False
        elif len(key) == 1 and key.isdigit():
            if len(self.buffer) < 3:
                self.buffer += key
            else:
                curses.beep()
        else:
            curses.beep()
            log.debug(
                "Input: {} (len: {})"
                .format(key, len(key))
            )
        # Always draw and return
        self.draw()
        return self.active

    # support with -statement
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        pass



# EOF
