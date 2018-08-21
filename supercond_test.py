#!/usr/bin/env python
import sys
import numpy as np
import pyqtgraph as pg
import visa
import subprocess
import pyqtgraph.exporters
import time
import csv

from PyQt4.QtCore import *
from PyQt4.QtGui import *

def get_devices():
    '''Try finding experiment devices and returning them'''
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


def check_devices(lakeshore, keithley):
    if (not lakeshore or not keithley):
        print "Error: Missing GPIB Device"
        return -1
    is2182aConnected = keithley.query('SOUR:DELT:NVPR?')
    if int(is2182aConnected) != 1:
        print "Keithley 2182 Voltmeter is not connected"
        return -1
    return 0


def arm_keithley(keithley, dvmRange, sampleCurr, deltaDelay, numDeltaPoints):
    keithley.write('SYST:COMM:SER:SEND "VOLT:RANGE ' + str(dvmRange) + '"')
    keithley.write('*RST')
    keithley.write('SOUR:DELT:HIGH ' + str(sampleCurr))
    keithley.write('SOUR:DELT:DEL ' + str(deltaDelay))
    keithley.write('SOUR:DELT:COUN ' + str(numDeltaPoints))
    keithley.write('TRAC:CLE')
    keithley.write('SOUR:DELT:ARM')
    time.sleep(10)
    print "Keithley 6220 is armed (locked and loaded)"
    return


def disarm_keithley(keithley):
    keithley.write('SOUR:SWE:ABOR')
    keithley.write('TRAC:CLE')
    print "Keithley 6220 is disarmed"
    return


def temp_follow_loop(lakeshore, keithley, sampleCurr, numDeltaPoints, 
        deltaDelay):
    newTempl = float(lakeshore.query('KRDG?a'))
    newDiode = float(lakeshore.query('SRDG?a'))
    newTempu = float(lakeshore.query('KRDG?b'))
    keithley.write('INIT:IMM')
    time.sleep(numDeltaPoints * deltaDelay + 0.1)
    keithley.write('TRAC:DATA?')
    time.sleep(numDeltaPoints * deltaDelay + 0.1)
    keithley.read()
    keithley.write('CALC2:FORM MEAN')
    keithley.write('CALC2:STAT ON')
    keithley.write('CALC2:IMM')
    keithley.write('CALC2:DATA?')
    avgVoltage = float(keithley.read())
    avgOhms = avgVoltage / sampleCurr
    return [newTempu, newTempl, newDiode, sampleCurr, avgVoltage, avgOhms]


def temp_follow_f(lakeshore, keithley, tParam, sampleCurr,
        ptInterval, numDeltaPoints, deltaDelay):
    '''Collect data until the temperature tParam is reached'''
    newTempl = float(lakeshore.query('KRDG?a'))
    tempSign = np.sign(newTempl - tParam)
    newTempSign = tempSign
    data = []
    while tempSign == newTempSign:
        newData = temp_follow_loop(lakeshore, keithley, sampleCurr, 
                numDeltaPoints, deltaDelay)
        data.append(newData)
        time.sleep(ptInterval)
        newTempSign = np.sign(newData[1] - tParam)
    return data


def temp_follow_a(lakeshore, keithley, tParam, sampleCurr, ptInterval, 
        numDeltaPoints, deltaDelay):
    '''Collect tParam number of data points'''
    data = []
    for i in range(tParam):
        newData = temp_follow_loop(lakeshore, keithley, sampleCurr, 
                numDeltaPoints, deltaDelay)
        data.append(newData)
        time.sleep(ptInterval)
    return data


def temp_follow(lakeshore, keithley, tempFollow, tParam, sampleCurr, dvmRange, 
        ptInterval, numDeltaPoints, deltaDelay):
    if (tempFollow == "f"):
        return temp_follow_f(lakeshore, keithley, tParam, sampleCurr, 
                ptInterval, numDeltaPoints, deltaDelay)
    elif (tempFollow == "a"):
        return temp_follow_a(lakeshore, keithley, tParam, sampleCurr, 
                ptInterval, numDeltaPoints, deltaDelay)
    return


def superconductivity_ul(tempFollow, tParam, sampleCurr, dvmRange, ptInterval,
        numDeltaPoints, deltaDelay):
    lakeshore, keithley, voltmeter = get_devices() 
    if (check_devices(lakeshore, keithley)):
        return -1
    arm_keithley(keithley, dvmRange, sampleCurr, deltaDelay, numDeltaPoints)
    data = temp_follow(lakeshore, keithley, tempFollow, tParam, sampleCurr, 
            dvmRange, ptInterval, numDeltaPoints, deltaDelay)
    disarm_keithley(keithley)
    keithley.close()
    lakeshore.close()
    return data


def write_data(filename, data):
    with open(filename, "wb") as outfile:
        writer = csv.writer(outfile, delimiter=',')
        for line in data:
            writer.writerow(line)
    return

class AppForm(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.create_main()
        self.setGeometry(100, 100, 800, 800)
        self.setWindowTitle("Superconductivity Lab")
        return

    def create_btns(self):
        self.save_btn = QPushButton("Save data", self)
        self.start_btn = QPushButton("Start", self)
        self.stop_btn = QPushButton("Stop", self)
        self.set_parameters_btn = QPushButton("Set parameters", self)
        self.save_btn.clicked.connect(self.save_data)
        self.start_btn.clicked.connect(self.start_exp)
        self.stop_btn.clicked.connect(self.stop_exp)
        self.set_parameters_btn.clicked.connect(self.set_params)
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.resize(self.save_btn.minimumSizeHint())
        return

    def create_lines(self):
        self.temp_follow_input = QLineEdit()
        self.t_param_input = QLineEdit()
        self.sample_curr_input = QLineEdit()
        self.dvm_range_input = QLineEdit()
        self.pt_interval_input = QLineEdit()
        self.num_delta_points_input = QLineEdit()
        self.delta_delay_input = QLineEdit()
        return

    def add_lines(self):
        self.rows = QFormLayout()
        self.rows.addRow("Temperature follow (a or f): ", 
                self.temp_follow_input)
        self.rows.addRow("T param (eg. 1): ", self.t_param_input)
        self.rows.addRow("Sample current [amps] (eg. 0.01): ", 
                self.sample_curr_input)
        self.rows.addRow("DVM range (eg. 1): ", self.dvm_range_input)
        self.rows.addRow("PT interval (eg. 1): ", self.pt_interval_input)
        self.rows.addRow("Number of delta points (eg. 10): ", 
                self.num_delta_points_input)
        self.rows.addRow("Delta delay (eg. 0.1): ", self.delta_delay_input)
        self.rows.addRow(self.set_parameters_btn)
        return

    def set_params(self):
        try:
            temp_follow = self.temp_follow_input.text()
            if temp_follow != "a" and temp_follow != "f":
                raise Exception('temp_follow', "not 'a' or 'f'")
            self.temp_follow = temp_follow
            t_param = float(self.t_param_input.text())
            sample_curr = float(self.sample_curr_input.text())
            dvm_range = float(self.dvm_range_input.text())
            pt_interval =int(self.pt_interval_input.text())
            num_delta_points = int(self.num_delta_points_input.text())
            delta_delay = float(self.delta_delay_input.text())
            self.t_param = t_param
            self.sample_curr = sample_curr
            self.dvm_range = dvm_range
            self.pt_interval = pt_interval
            self.num_delta_points = num_delta_points
            self.delta_delay = delta_delay
            success_message = \
                "Parameters set to: \n" + \
                "Temperature Follow: " + str(self.temp_follow) + "\n" + \
                "TParam: " + str(self.t_param) + "\n" + \
                "Sample Curr: " + str(self.sample_curr) + "\n" + \
                "DVM Range: " + str(self.dvm_range) + "\n" + \
                "PT Interval: " + str(self.pt_interval) + "\n" + \
                "# Delta Points: " + str(self.num_delta_points) + "\n" + \
                "Delta Delay: " + str(self.delta_delay) + "\n"
            QMessageBox.about(self, "Success", success_message)

        except Exception as inst:
            QMessageBox.about(self, 'Error', str(inst.args))
        return

    def start_exp(self):
        return

    def stop_exp(self):
        return

    def save_data(self):
        return

    def create_main(self):
        page = QWidget()
        self.create_btns()
        self.create_lines()
        self.setCentralWidget(page)
        self.plot = pg.PlotWidget()
        self.add_lines()
        vbox = QGridLayout()
        vbox.addLayout(self.rows, 0, 0, 1, 3)
        vbox.addWidget(self.plot)
        vbox.addWidget(self.start_btn)
        vbox.addWidget(self.stop_btn)
        vbox.addWidget(self.save_btn)
        page.setLayout(vbox)
        return

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = AppForm()
    form.show()
    app.exec_()

