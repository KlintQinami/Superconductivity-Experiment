#!/usr/bin/env python
import sys
import numpy as np
import pyqtgraph as pg
import visa
import subprocess
import pyqtgraph.exporters

def get_devices():
    subprocess.check_call("gpib_config")
    rm = visa.ResourceManager('@py')
    instruments = rm.list_resources()
    lakeshore = None
    keithley = None
    voltmeter = None
    for inst in instruments[1:]:
        dev = rm.open_resource(inst)
        dev_name = dev.query('*IDN?')
        if 'LSCI' in dev_name:
            lakeshore = dev
            print "Lakeshore ( " + dev_name[:-2] + " ) found"
            continue
        if '6220' in dev_name:
            keithley = dev
            print "Keithley 6220 ( " + dev_name[:-2] + " ) found"
            continue
        if '2182' in dev_name:
            voltmeter = dev
            print "Keithley 2182 ( " + dev_name[:-2] + " ) found"
            continue
    return lakeshore, keithley, voltmeter

def temp_follow_f(lakeshore, keithley, voltmeter):
    return

def superconductivity_ul(tempFollow, tParam, sampleCurr, dvmRange, ptInterval):
    numDeltaPoints = 25
    deltaDelay = 1
    lakeshore, keithley, voltmeter = get_devices() 
    print "SOUR:DELT:NVPR: " + keithley.query('SOUR:DELT:NVPR?')
    keithley.write('SYST:COMM:SER:SEND "VOLT:RANGE ' + str(dvmRange) + '"')
    keithley.write('*RST')
    keithley.write('SOUR:DELT:HIGH ' + str(sampleCurr))
    keithley.write('SOUR:DELT:DEL ' + str(deltaDelay))
    keithley.write('SOUR:DELT:COUN ' + str(numDeltaPoints))
    keithley.write('TRAC:CLE')
    keithley.write('SOUR:DELT:ARM')
    print "KRDG?: " + lakeshore.query('KRDG?')
    print "KRDG?a: " + lakeshore.query('KRDG?a')
    print "SRDG?a: " + lakeshore.query('SRDG?a')
    print "KRDG?b: " + lakeshore.query('KRDG?b')
    keithley.write('INIT:IMM')
    print "Keith TRAC:DATA?: " + keithley.query('TRAC:DATA?')
    print "Volt TRAC:DATA?: " + voltmeter.query('TRAC:DATA?')

if __name__ == "__main__":
    superconductivity_ul("f", 1, 0.01, 1, 1)
