#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# PATE Bias Board Evaluation Software (pbbes) 2018
#
# IntervalScheduler.py - Jani Tammi <jasata@utu.fi>
#   0.1     2018.06.27  Initial version.
#   0.2     2018.09.22  Adapted for PBBES.
#   0.3     2018.09.30  Added .reset() function.
#   1.0     2018.10.04  Finalized for release.
#
#   Arguments:
#       heartbeat       Interval in seconds
#       measurement     Interval in seconds
#       time_window     Time window in seconds
#
#   This version of event "ticker" (hard coded for PaTe Bias Board
#   Evaluation Software purpose) sleeps whatever duration is needed
#   to trigger the next event.
#   Implementation also features a "time window" that collects all
#   events that trigger within that window of time, thereby reducing
#   the number of calls. This also means that any event can trigger
#   early (at most <time_window> amount time early).
#
#
#   .next()
#   ================================================================
#
#   Blocking function that returns an (integer) field of event flags
#   that list triggered events. There is no flag clearing
#   functionality. Caller is responsible for dealing with all
#   triggered events.
#
#   Function call also reschedules each triggered event.
#
#
#
import os
import sys
import time
import logging

# Module privates
_moduleName = os.path.basename(os.path.splitext(__file__)[0])
_fileName   = os.path.basename(__file__)

class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __missing__(self, key):
        """Return None if non-existing key is accessed"""
        return None

class IntervalScheduler():
    # Event flags
    HEARTBEAT   = 0x01
    MEASUREMENT = 0x02
    def __init__(
        self,
        heartbeat   = 0.2,
        measurement = 60.0,
        time_window = 0.01
    ):
        now = time.time()
        self.Heartbeat              = DotDict()
        self.Heartbeat.INTERVAL     = heartbeat
        self.Heartbeat.NEXTEVENT    = now + self.Heartbeat.INTERVAL
        self.Measurement            = DotDict()
        self.Measurement.INTERVAL   = measurement
        self.Measurement.NEXTEVENT  = now + self.Measurement.INTERVAL
        self.time_window            = time_window

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def restart(self):
        """Simply reset .NEXTEVENT timestamps"""
        now = time.time()
        self.Heartbeat.NEXTEVENT    = now + self.Heartbeat.INTERVAL
        self.Measurement.NEXTEVENT  = now + self.Measurement.INTERVAL

    def measurement(self, interval = None):
        """Give no arguments to 'get', give an argument to 'set'"""
        if interval is not None:
            self.Measurement.INTERVAL = interval
        return self.Measurement.INTERVAL

    def next(self):
        """Sleep until next event(s) and return them as flags"""
        now = time.time()
        # next event is the one with smallest triggering time
        next_event = min(
            self.Heartbeat.NEXTEVENT,
            self.Measurement.NEXTEVENT
        )
        # Sleep until next triggered event (skip negative duration)
        sleep_duration = next_event - now
        if sleep_duration > 0:
            time.sleep(sleep_duration)
        # trigger_time is the time *before* which events are triggered
        trigger_time = now + self.time_window
        events = 0x00
        # Compile fields and reschedule events that fired
        if self.Heartbeat.NEXTEVENT < trigger_time:
            events |= self.HEARTBEAT
            self.Heartbeat.NEXTEVENT += self.Heartbeat.INTERVAL
        if self.Measurement.NEXTEVENT < trigger_time:
            events |= self.MEASUREMENT
            self.Measurement.NEXTEVENT += self.Measurement.INTERVAL

        return events

#
# Usage example
#
if __name__ == "__main__":

    with IntervalScheduler(0.2, 10, 0.2) as event:
        while True:
            events = event.next()
            print("[", end = '')
            print("H" if events & IntervalScheduler.HEARTBEAT else " ", end = '')
            print("M" if events & IntervalScheduler.MEASUREMENT else " ", end = '')
            print("]", end = '')
            sys.stdout.flush()

# EOF
