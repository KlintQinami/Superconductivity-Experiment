#!/usr/bin/env python

import csv
import numpy as np
import pyqtgraph as pg
import pyqtgraph.exporters
import subprocess
import sys
import threading
import time
import visa


from PyQt4.QtCore import *
from PyQt4.QtGui  import *


class AppForm(QMainWindow):


    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.data = []
        self.create_main()
        self.setGeometry(100, 100, 800, 800)
        self.setWindowTitle("Superconductivity Lab")
        try:
            self.get_devices()
        except Exception:
            QMessageBox.about(self, "Error", "Instruments not found")
        return


    def create_btns(self):
        self.save_btn = QPushButton("Save data", self)
        self.start_btn = QPushButton("Start", self)
        self.stop_btn = QPushButton("Stop", self)
        self.set_parameters_btn = QPushButton("Set parameters", self)
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
            pt_interval = int(self.pt_interval_input.text())
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


    def check_devices(self):
        if (not self.lakeshore or not self.keithley):
            print "Error: Missing GPIB Device"
            return -1
        is2182aConnected = self.keithley.query('SOUR:DELT:NVPR?')
        if int(is2182aConnected) != 1:
            print "Keithley 2182 Voltmeter is not connected"
            return -1
        return 0


    def get_devices(self):
        '''Try finding experiment devices and returning them'''
        subprocess.check_call("gpib_config")
        rm = visa.ResourceManager('@py')
        instruments = rm.list_resources()
        self.lakeshore = None
        self.keithley = None
        self.voltmeter = None
        for inst in instruments[1:]:
            dev = rm.open_resource(inst)
            dev_name = dev.query('*IDN?')
            if 'LSCI' in dev_name:
                self.lakeshore = dev
                print "Lakeshore ( " + dev_name[:-2] + " ) found"
                continue
            if '6220' in dev_name:
                self.keithley = dev
                print "Keithley 6220 ( " + dev_name[:-2] + " ) found"
                continue
            if '2182' in dev_name:
                self.voltmeter = dev
                print "Keithley 2182 ( " + dev_name[:-2] + " ) found"
                continue
        return
   

    def temp_follow_loop(self):
        new_templ = float(self.lakeshore.query('KRDG?a'))
        new_diode = float(self.lakeshore.query('SRDG?a'))
        new_tempu = float(self.lakeshore.query('KRDG?b'))
        self.keithley.write('INIT:IMM')
        time.sleep(self.num_delta_points * self.delta_delay + 0.1)
        self.keithley.write('TRAC:DATA?')
        time.sleep(self.num_delta_points * self.delta_delay + 0.1)
        self.keithley.read()
        self.keithley.write('CALC2:FORM MEAN')
        self.keithley.write('CALC2:STAT ON')
        self.keithley.write('CALC2:IMM')
        self.keithley.write('CALC2:DATA?')
        avg_voltage = float(self.keithley.read())
        avg_ohms = abs(avg_voltage / self.sample_curr)
        self.data.append([new_templ, new_tempu, new_diode, self.sample_curr, 
            avg_voltage, avg_ohms])
        self.update_plot()
        time.sleep(self.pt_interval)
        return

        
    def temp_follow_f(self):
        new_templ = float(self.lakeshore.query('KRDG?a'))
        temp_sign = np.sign(new_templ - self.t_param)
        new_temp_sign = temp_sign
        while temp_sign == new_temp_sign:
            if self.stop:
                return
            self.temp_follow_loop()
            new_temp_sign = np.sign(self.data[-1][1] - self.t_param)
        print "Temperature " + str(self.t_param) + " reached"
        return


    def temp_follow_a(self):
        for i in range(int(round(self.t_param))):
            if self.stop:
                return
            self.temp_follow_loop()
        print "Collected " + str(int(round(self.t_param))) + " datapoints"
        return


    def temp_follow_m(self):
        if (self.temp_follow == "f"):
            self.temp_follow_f()
        elif (self.temp_follow == "a"):
            self.temp_follow_a()
        return


    def update_plot(self):
        self.x[self.graph_index] = self.data[-1][1]
        self.y[self.graph_index] = self.data[-1][-1]
        self.graph_index += 1
        if self.graph_index >= self.x.shape[0]:
            tmp = self.x
            tms = self.y
            self.x = np.empty(self.x.shape[0] * 2)
            self.x[:tmp.shape[0]] = tmp
            self.y = np.empty(self.y.shape[0] * 2)
            self.y[:tms.shape[0]] = tms
        self.curve.setData(self.x[:self.graph_index], 
        self.y[:self.graph_index])

        print self.data[-1]
        app.processEvents()
        return


    def arm_keithley(self):
        self.keithley.write('SYST:COMM:SER:SEND "VOLT:RANGE ' + \
                str(self.dvm_range) + '"')
        self.keithley.write('*RST')
        self.keithley.write('SOUR:DELT:HIGH ' + str(self.sample_curr))
        self.keithley.write('SOUR:DELT:DEL ' + str(self.delta_delay))
        self.keithley.write('SOUR:DELT:COUN ' + str(self.num_delta_points))
        self.keithley.write('TRAC:CLE')
        self.keithley.write('SOUR:DELT:ARM')
        print "Keithley 6220 is armed (locked and loaded)"
        time.sleep(10)
        return


    def disarm_keithley(self):
        if (self.keithley):
            self.keithley.write('SOUR:SWE:ABOR')
            self.keithley.write('TRAC:CLE')
            print "Keithley 6220 is disarmed"
        return


    def start_exp(self):
        if (not self.keithley or not self.lakeshore):
            try:
                self.get_devices()
                if (self.check_devices()):
                    QMessageBox.about(self, 'Error', "Instruments not found")
                    return
            except Exception:
                print "Start error"
                QMessageBox.about(self, 'Error', "Instruments not found")
                return
        self.stop = False
        self.arm_keithley()
        self.temp_follow_m()
        return


    def stop_exp(self):
        if (self.keithley and self.lakeshore):
            self.stop = True
            self.disarm_keithley()
            self.keithley.close()
            self.lakeshore.close()
            self.keithley = None
            self.lakeshore = None
        return


    def save_data(self):
        try:
            outfile = QFileDialog.getSaveFileName(self, "Save File")
            with open(outfile, "wb") as f:
                f.write("new_tempu,new_templ,new_diode,sample_curr," + \
                        "avg_voltage,avg_ohms\n")
                writer = csv.writer(f, delimiter=',')
                for line in self.data:
                    writer.writerow(line)
            return
        except Exception:
            QMessageBox.about(self, 'Error', 'Nothing was saved.')
        return


    def set_plot(self):
        self.plot.setTitle("Resistance vs Temperature")
        self.plot.setLabel('left', 'Resistance', units='ohms')
        self.plot.setLabel('bottom', 'Temperature', units='kelvin')
        self.curve = self.plot.plot(pen="b", symbol='o', symbolPen=None, 
                symbolSize=5, symbolBrush=(255,255,255,255))
        self.plot.setDownsampling(mode='peak')
        self.plot.setClipToView(True)
        self.plot.enableAutoRange(x=True)
        self.plot.enableAutoRange(y=True)
        pg.setConfigOptions(antialias=True)
        self.x = np.empty(100)
        self.y = np.empty(100)
        self.graph_index = 0
        return


    def create_main(self):
        page = QWidget()
        self.create_btns()
        self.create_lines()
        self.setCentralWidget(page)
        self.plot = pg.PlotWidget()
        self.set_plot()
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

