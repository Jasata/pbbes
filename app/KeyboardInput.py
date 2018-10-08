#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# PATE Bias Board Evaluation Software (pbbes) 2018
#
# KeyboardInput.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.09.24  Initial version.
#   0.2     2018.10.02  STDIO now recovers from non-blocking mode on exit.
#   1.0     2018.10.04  Finalized for release.
#   1.0.1   2018.10.08  Updated with Philipp's Linux F1 .. F4 escape sequences.
#
# Because I could not get F1..F4 or ESC with curses tools...
# (and because I had higher urgency in just getting this done than
#  trying to find out what the issue was all about...)
#
import os
import sys
import tty
import fcntl
import select
import termios
import logging

_moduleName = os.path.basename(os.path.splitext(__file__)[0])
_fileName   = os.path.basename(__file__)

# RULE: Translated sequence MUST be two or more chacter string!
# This is what distinquishes non-printable characters from printable.
translate = {
    b'\x1b'                 : "ESC",
    b'\x1bOP'               : "F1",         # Philipp's OS
    b'\x1b\x5b\x31\x31\x7e' : "F1",         # Debian, Rasbian (and apparently other derivants)
    b'\x1bOQ'               : "F2",
    b'\x1b\x5b\x31\x32\x7e' : "F2",
    b'\x1bOR'               : "F3",
    b'\x1b\x5b\x31\x33\x7e' : "F3",
    b'\x1bOS'               : "F4",
    b'\x1b\x5b\x31\x34\x7e' : "F4",
    b'\x1b[15~'             : "F5",
    b'\x1b[17~'             : "F6",
    b'\x1b[18~'             : "F7",
    b'\x1b[19~'             : "F8",
    b'\x1b[20~'             : "F9",
    b'\x1b[21~'             : "F10",
    b'\x1b[23~'             : "F11",
    b'\x1b[24~'             : "F12",
    b'\x1b[1~'              : "HOME",
    b'\x1b[2~'              : "INS",
    b'\x1b[3~'              : "DEL",
    b'\x1b[4~'              : "END",
    b'\x1b[5~'              : "PAGEUP",
    b'\x1b[6~'              : "PAGEDOWN",
    b'\x1b[A'               : "UP",
    b'\x1b[B'               : "DOWN",
    b'\x1b[C'               : "RIGHT",
    b'\x1b[D'               : "LEFT",
    b'\x1bOA'               : "UP",         # x86 Debian 9
    b'\x1bOB'               : "DOWN",       # x86 Debian 9
    b'\x1bOC'               : "RIGHT",      # x86 Debian 9
    b'\x1bOD'               : "LEFT",       # x86 Debian 9
    b'\x7f'                 : "BACKSPACE",
    b'\n'                   : "ENTER",      # b'\x1b[2~\x1b'
    b'\r'                   : "ENTER",      # curses...does this to us....
    b'\x09'                 : "TAB",
    b'\x1b[Z'               : "SHIFT-TAB"
}

class KeyboardInput():
    chunk = None
    raw   = None
    def __init__(self, fd = sys.stdin):
        # Has to be here; __enter__ is too late
        self.old_settings = termios.tcgetattr(fd)
        # I know of no way to remove stdin buffering or flush the buffer so that
        # I get to read all the accumulated characters...
        # stdin has to be "reopened" without buffering
        self.raw = os.fdopen(fd.fileno(), 'rb', buffering=0)

        # Normally, the tty driver buffers typed characters until a newline or
        # carriage return is typed. The cbreak routine disables line buffering
        # and erase/kill character-processing (interrupt and flow control
        # characters are unaffected), making characters typed by the user
        # immediately available to the program.
        tty.setcbreak(self.raw.fileno())

        # Set the file into non-blocking mode
        self.flag = fcntl.fcntl(self.raw.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(self.raw.fileno(), fcntl.F_SETFL, self.flag | os.O_NONBLOCK)
    def __has_data(self):
        return select.select([self.raw], [], [], 0) == ([self.raw], [], [])
    # Iteration
    def __iter__(self):
        self.chunk = self.raw.read(5)
        return self
    def __next__(self):
        log = logging.getLogger(
            _fileName + ":" + self.__class__.__name__ + "." + \
            sys._getframe().f_code.co_name + "()"
        )
        if self.chunk is None:
            raise StopIteration
        try:
            key = translate[self.chunk]
            self.chunk = None
            log.debug("key: '{}'".format(key))
            return key
        except KeyError:
            log.debug(
                "key '{}' not found in dictionary!"
                .format(self.chunk)
            )
            pass # ...and continue with below code
        # Unrecognized escape sequences
        if self.chunk[:1] == b'\x1b':
            # Read until empty (should have more intelligent handling)
            while self.__has_data():
                self.raw.read(1024)
            raise StopIteration
        else:
            # return just one character
            try:
                ch = self.chunk[:1].decode('utf-8')
            except:
                # Swallow non-decodables
                ch = '?' # debug!!
            self.chunk = self.chunk[1:]
            # replenish empty chunk with more/None
            if self.chunk == b'':
                self.chunk = self.raw.read(5)
            log.debug("key '{}'".format(ch))
            return ch

    # with -statement
    def __enter__(self):
        # Still necessary, even though sys.stdin is "reopened"
        # and changes applied to new handle. Ie. handle does not
        # retain properties, but the actual device file.
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        termios.tcsetattr(self.raw, termios.TCSADRAIN, self.old_settings)
        fcntl.fcntl(self.raw.fileno(), fcntl.F_SETFL, self.flag & ~os.O_NONBLOCK)
        self.raw.close()

#
# Class that consumes input and reports active consumer state with return values
# A consumer example (obviously not useful)
class InputConsumer():
    active = False
    buffer = ''
    value  = ''
    def __init__(self, trigger):
        self.trigger = trigger
    def process_input(self, key):
        # inactive
        if self.active == False:
            if key == self.trigger:
                self.active = True
            return self.active
        # active
        if key in ("ESC", self.trigger):
            self.buffer = ''
            self.active = False
            return self.active
        elif key in ("DEL", "BACKSPACE"):
            if len(self.buffer) > 0:
                self.buffer = self.buffer[:-1]
            print(self.buffer)
        elif key == "ENTER":
            self.value = self.buffer
            self.buffer = ''
            self.active = False
        elif len(key) == 1:
            self.buffer += key
            print(self.trigger, self.buffer)
        else:
            print("beep!")
        return self.active

#
# KeyboardInput consumer management
#
#   Registers objects that implement .process_input(key).
#   Initially, offers the key to all registered consumers, until one returns
#   True, indicating that the key triggered that consumer for input.
#   ConsumerManagement will keep supplying that activated consumer with all
#   key inputs, until it returns False (indicating that processing has ended).
#   Next input is again offered to all registered consumers in hope that one
#   of them triggers for input.
#
# What is this good for?
#
#   This has been created for a console application which essentially only
#   displays data, but has to be able to change some parameters occasionally.
#   In this implementation, operator is expected to press F<n> key to activate
#   input for a parameter. The responsible display widget (implementing
#   consumer .process_input()) will deal with the keystrokes until the
#   input session is terminated and parameter is either updated or input was
#   cancelled.
#
#   UI may have any number of such parameters, which means there may be many
#   consumers.
#
class InputConsumerManagement():
    consumers = []
    active_consumer = None
    def __init__(self):
        pass
    def add(self, consumer):
        self.consumers.append(consumer)
    def input(self, key):
        if self.active_consumer is None:
            for consumer in self.consumers:
                if consumer.process_input(key):
                    self.active_consumer = consumer
                    break
        else:
            if not self.active_consumer.process_input(key):
                self.active_consumer = None

#
# Usage example
#
if __name__ == "__main__":
    from IntervalScheduler import IntervalScheduler
    print("Exit with CTRL-C...")
    try:
        event = IntervalScheduler(0.05, 10, 0)
        manage = InputConsumerManagement()
        manage.add(InputConsumer("F1"))
        manage.add(InputConsumer("F2"))
        manage.add(InputConsumer("F3"))
        manage.add(InputConsumer("F4"))
        manage.add(InputConsumer("F9"))

        keep_running = True
        with KeyboardInput() as keyboad_input:
            while keep_running:
                # event.next() blocks/sleeps until next event
                if event.next() & event.MEASUREMENT:
                    print("MEASUREMENT", end='')
                for key in keyboad_input:
                    manage.input(key)
                    # if key == 'ESC':
                    #     keep_running = False
                    #     break
                    # print(key, end='')
                sys.stdout.flush()

    finally:
        pass

# EOF
