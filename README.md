# Foresail-1 PATE Bias Board evaluation software
_Version 1.0 / 2018-10-04 / JTa_

Sole purpose of this software is to allow Bias Board developer to
periodically retrieve data from evaluation/housekeeping MCU in the
development version of the PCB. Software also allows issuing PWM
duty values for channels 1 thru 4.

This utility performs a calibration (command 'RRR') twice upon start-up.
Retrieved values are stored into a CSV file (named as date and time).
Data retrieval interval is 10 seconds by default.

Interfacing is done via serial device file (default '/dev/ttyUSB0').

## Requirements

1. Linux operating system
2. Python 3.5 or newer
3. pySerial 3.3 or newer (pip3 install pyserial)
4. Items: bias board and USB to RS-232 adapter

## Usage (simplified)

- Run './main.py'
- Press CTRL-C to exit (NOTE: may need to do it twice)

- Start-up screen allows operator to define a session specific label which will be written into the CSV file header. (Press enter for none.)
- Main screen allows to change PWM duty (F1 .. F4 keys), measurement interval (F9 key) and exists on CTRL-C.

## Output

1. .CSV file, named with date and time.
2. 'pbbes.log' containing debug, error and exception information that is generated during the execution.
3. 'serial.log' containing all sent and received messages.

## Tip:

Open two additional terminals and follow 'pbbes.log' and 'serial.log' in them.
Issue commands:

    tail -f pbbes.log

    tail -f serial.log

## Commandline options

    ./main.py -h

    -d [DEVICE]     Device file. Default: '/dev/ttyUSB0'
    -l [LEVEL]      pbbes.log logging level. Default: DEBUG
    -i [SECONDS]    Measurement interval. Default: 10

## Testing/development

A dummy bias board stand-in, 'pbb-emulator.py' is provided. Using this,
the main.py can be ran by connecting two USB/RS-232 adapters to the system
and running the dummy-emulator in one port and the pbbes on another.
