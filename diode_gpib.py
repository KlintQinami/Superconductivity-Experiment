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
        self.setWindowTitle("Superconductivity Diode Lab")
        self.keithley = None
        self.voltmeter = None
        self.lakeshore = None
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
        self.curr_l_input = QLineEdit()
        self.curr_h_input = QLineEdit()
        self.curr_inc_input = QLineEdit()
        self.num_meas_input = QLineEdit()
        return


    def add_lines(self):
        self.rows = QFormLayout()
        self.rows.addRow("Current High [amps]: ", self.curr_h_input)
        self.rows.addRow("Current Low [amps]: ", self.curr_l_input)
        self.rows.addRow("Current Increment [amps]: ", self.curr_inc_input)
        self.rows.addRow("# Measurements per point: ", self.num_meas_input)
        self.rows.addRow(self.set_parameters_btn)
        return


    def set_params(self):
        try:
            curr_h = float(self.curr_h_input.text())
            curr_l = float(self.curr_l_input.text())
            curr_inc = float(self.curr_inc_input.text())
            num_meas = int(self.num_meas_input.text())
            self.curr_h = curr_h
            self.curr_l = curr_l
            self.curr_inc = curr_inc
            self.num_meas = num_meas
            success_message = \
                "Parameters set to: \n" + \
                "Current High: " + str(self.curr_h) + "\n" + \
                "Current Low: " + str(self.curr_l) + "\n" + \
                "Current Increment: " + str(self.curr_inc) + "\n" + \
                "# Measurements per point " + str(self.num_meas)
            QMessageBox.about(self, "Success", success_message)
        except Exception as inst:
            QMessageBox.about(self, 'Error', str(inst.args))
        return


    def check_devices(self):
        if (not self.lakeshore or not self.keithley or not self.voltmeter):
            print "Error: Missing GPIB Device"
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
   

    def initialize_keithleys(self):
        self.compliance = 105
        self.keithley.write('*RST')
        self.keithley.write('SOUR:CURR:COMP ' + str(self.compliance))
        self.keithley.write('SOUR:CURR:RANG:AUTO ON')

        self.voltmeter.write('*RST')
        self.voltmeter.write('*CLS')
        self.voltmeter.write('SAMP:COUN 1')
        self.voltmeter.write('READ?')
        print "Test Volts: " + str(self.voltmeter.read())
        return


    def diode_measurement(self):
        curr_r = self.curr_l
        self.keithley.write('OUTP ON')
        while curr_r < self.curr_h + self.curr_inc:
            self.keithley.write('SOUR:CURR ' + str(curr_r))
            v_sum = 0
            tl_sum = 0
            tu_sum = 0
            for i in range(self.num_meas):
                tl_sum += float(self.lakeshore.query('KRDG?a'))
                tu_sum += float(self.lakeshore.query('KRDG?b'))
                time.sleep(0.1)
                v_sum += float(self.voltmeter.query('READ?'))
            self.data.append([v_sum/self.num_meas, 
                curr_r, 
                tl_sum/self.num_meas, tu_sum/self.num_meas, 
                (tl_sum + tu_sum)/(2 * self.num_meas)])
            self.update_plot()
            curr_r += self.curr_inc
        return

        
    def update_plot(self):
        self.x[self.graph_index] = self.data[-1][0]
        self.y[self.graph_index] = self.data[-1][1]
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
    

    def start_exp(self):
        if (not self.keithley or not self.lakeshore or not self.voltmeter):
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
        self.initialize_keithleys()
        print "[voltage, current, templ, tempu, tempavg]"
        self.diode_measurement()
        print "Data run completed"
        return


    def stop_exp(self):
        if (self.keithley):
            self.stop = True
            self.keithley.write('OUTP OFF')
            self.keithley.write('SOUR:CLE')
            self.keithley.close()
            self.lakeshore.close()
            self.voltmeter.close()
            self.keithley = None
            self.lakeshore = None
            self.voltmeter = None
        return


    def save_data(self):
        try:
            outfile = QFileDialog.getSaveFileName(self, "Save File")
            with open(outfile, "wb") as f:
                f.write("voltage,current,templ,tempu,tempavg\n")
                writer = csv.writer(f, delimiter=',')
                for line in self.data:
                    writer.writerow(line)
            return
        except Exception:
            QMessageBox.about(self, 'Error', 'Nothing was saved.')
        return


    def set_plot(self):
        self.plot.setTitle("Current vs Voltage")
        self.plot.setLabel('left', 'Current', units='amps')
        self.plot.setLabel('bottom', 'Voltage', units='volts')
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

