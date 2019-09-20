from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


import serial
import serial.tools.list_ports

import yaml

from syringeController import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.disableAll_btn.pressed.connect(self.disableAll)
        self.jogAllForwardBtn.pressed.connect(self.jogAllForward)
        self.jogAllBackBtn.pressed.connect(self.jogAllBackwards)

        # setup serial ports
        self.activePort = None
        self.refreshBtn.pressed.connect(self.refreshPorts)
        self.connectBtn.pressed.connect(self.connectPort)
        self.refreshPorts()

        self.jogCtrlBox.setEnabled(False)
        self.disableAll_btn.setEnabled(False)
        self.startAll_btn.setEnabled(False)
        self.stopAll_btn.setEnabled(False)

        self.actionOpen_Config.triggered.connect(self.openConfig)
        self.actionSave_Config.triggered.connect(self.saveConfig)

        # Setup channel buttons
        for n in range(5):
            getattr(self, 's%s_groupBox' % (n+1)).setEnabled(False)
            getattr(self, 'jogFwdBtn_%s' % (n+1)).pressed.connect(lambda v=n: self.jogForward(v))
            getattr(self, 'jogBackBtn_%s' % (n+1)).pressed.connect(lambda v=n: self.jogBackwards(v))
            getattr(self, 'startMove_%s' % (n+1)).pressed.connect(lambda v=n: self.startMove(v))
            getattr(self, 'stopMove_%s' % (n+1)).pressed.connect(lambda v=n: self.stopMove(v))
            getattr(self, 'disableBtn_%s' % (n+1)).pressed.connect(lambda v=n: self.disableMotor(v))

        #setup progress timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.checkProgress)
        self.timer.start(1000)

        self.show()

    # Movement Functions
    def disableMotor(self, slidernum):
        cmdstr = 'E%d 0' % slidernum
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)

    def disableAll(self):
        for i in range(5):
            disableMotor(i)

    def jogForward(self, slidernum):
        cmdstr = 'E%d 1' % slidernum
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)

        jogamt = self.jogAmt.value()
        cmdstr = 'J %d %d'%(slidernum,jogamt)
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print('jog forward%s' % slidernum)

    def jogBackwards(self, slidernum):
        cmdstr = 'E%d 1' % slidernum
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)

        jogamt = self.jogAmt.value()
        cmdstr = 'J %d %d'%(slidernum,-jogamt)
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print('jog backwards %s'%slidernum)

    def jogAllForward(self):
        for i in range(5):
            self.jogForward(i)

    def jogAllBackwards(self):
        for i in range(5):
            self.jogBackwards(i)

    def startMove(self, slidernum):
        #send parameters

        rate = getattr(self, 'rate_%d' % (slidernum+1)).value() # rate, ml/hr
        amt = getattr(self, 'duration_%d' % (slidernum+1)).value() # Amount, mL
        syringeSize = getattr(self, 'syringeDiam_%d' % (slidernum+1)).value() # syringe size, mm/ml 
        retract = getattr(self, 'retractAmt_%d' % (slidernum+1)).value()

        stepsMM = 400 #steps/mm

        time = amt/rate * 60 * 60 # seconds

        steps = syringeSize * amt * stepsMM # total steps
        retractSteps = retract * stepsMM #retract steps

        microseconds_per_step = (time*1000000)/steps


        cmdstr = 'P%dR%d' % (slidernum, microseconds_per_step)
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)

        cmdstr = 'P%dS%d' % (slidernum, steps)
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)

        cmdstr = 'P%dE%d' % (slidernum, retractSteps)
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)


        #enable stepper

        cmdstr = 'E%d 1' % slidernum
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)

        cmdstr = 'M%s 1' % slidernum
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print(cmdstr)
        print('start move %s' % slidernum)

        getattr(self, 'jogFwdBtn_%d' % (slidernum+1)).setEnabled(False)
        getattr(self, 'jogBackBtn_%d' % (slidernum+1)).setEnabled(False)
        getattr(self, 'startMove_%d' % (slidernum+1)).setEnabled(False) 
        getattr(self, 'rate_%d' % (slidernum+1)).setEnabled(False)
        getattr(self, 'duration_%d' % (slidernum+1)).setEnabled(False)
        getattr(self, 'syringeDiam_%d' % (slidernum+1)).setEnabled(False)
    
    def startAllMoves(self):
        for i in range(5):
            self.startMove(i)

    def stopMove(self, slidernum):
        cmdstr = 'M%s 0' % slidernum
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        print('stop move %s'%slidernum)
        getattr(self, 'jogFwdBtn_%d' % (slidernum+1)).setEnabled(True)
        getattr(self, 'jogBackBtn_%d' % (slidernum+1)).setEnabled(True)
        getattr(self, 'startMove_%d' % (slidernum+1)).setEnabled(True) 
        getattr(self, 'rate_%d' % (slidernum+1)).setEnabled(True)
        getattr(self, 'duration_%d' % (slidernum+1)).setEnabled(True)
        getattr(self, 'syringeDiam_%d' % (slidernum+1)).setEnabled(True)

    def stopAllMoves(self):
        for i in range(5):
            self.stopMove(i)
    # Connection Functions

    def checkProgress(self):
        if(self.activePort == None):
            return
        cmdstr = 'S'
        cmdstr = cmdstr.encode()
        self.activePort.write(cmdstr)
        
        line = ""
        while(self.activePort.in_waiting > 0): # Get most recent line
            line = self.activePort.readline().decode()

        tok = line.split("/")

        if(len(tok) != 5):
            return

        for t in tok:
            p = t.split(":")
            slidernum = int(p[0])
            prog = int(p[1])
            if(prog > 100):
                prog = 100
            getattr(self, 'moveProgress_%d' % slidernum).setValue(prog)
            if(prog < 100 and prog != 0):
                getattr(self, 'jogFwdBtn_%d' % (slidernum)).setEnabled(False)
                getattr(self, 'jogBackBtn_%d' % (slidernum)).setEnabled(False)
                getattr(self, 'startMove_%d' % (slidernum)).setEnabled(False) 
                getattr(self, 'rate_%d' % (slidernum)).setEnabled(False)
                getattr(self, 'duration_%d' % (slidernum)).setEnabled(False)
                getattr(self, 'syringeDiam_%d' % (slidernum)).setEnabled(False)
            else:
                getattr(self, 'jogFwdBtn_%d' % (slidernum)).setEnabled(True)
                getattr(self, 'jogBackBtn_%d' % (slidernum)).setEnabled(True)
                getattr(self, 'startMove_%d' % (slidernum)).setEnabled(True) 
                getattr(self, 'rate_%d' % (slidernum)).setEnabled(True)
                getattr(self, 'duration_%d' % (slidernum)).setEnabled(True)
                getattr(self, 'syringeDiam_%d' % (slidernum)).setEnabled(True)

    def refreshPorts(self):
        ports = serial.tools.list_ports.comports()
        self.portComboBox.clear()

        for p in ports:
            self.portComboBox.addItem(p.device)

    def connectPort(self):
        pn = self.portComboBox.currentText()
        print("Connecting to port %s"%pn)
        self.activePort = serial.Serial(pn,timeout = 1)
        print(self.activePort.name)
        self.jogCtrlBox.setEnabled(True)
        self.disableAll_btn.setEnabled(True)
        self.startAll_btn.setEnabled(True)
        self.stopAll_btn.setEnabled(True)
        for n in range(5):
            getattr(self, 's%s_groupBox' % (n+1)).setEnabled(True)


    def closeEvent(self, event):
        print("closing!")
        if(self.activePort != None):
            self.activePort.close()

    def saveConfig(self):
        filename = QFileDialog.getSaveFileName(self, 'Save File', '/', 'Config File (*.syr)')
        print(filename[0])

        if(len(filename[0]) != 0 and len(filename[1])!=0):
            data = {}

            general = {}
            general['jogamt'] = self.jogAmt.value()
            general['comport'] = self.portComboBox.currentText()
            data['general'] = general
            
            syringes = []
            for i in range(5):
                #for each syringe, create a dict
                syrdict = {}
                syrdict['rate'] = getattr(self, 'rate_%d' % (i+1)).value()
                syrdict['amt'] = getattr(self, 'duration_%d' % (i+1)).value()
                syrdict['syringeSize'] = getattr(self, 'syringeDiam_%d' % (i+1)).value()

                syrdict['retractBool'] = getattr(self, 'retractAtEnd_%d' % (i+1)).isChecked()
                syrdict['retractAmt'] = getattr(self, 'retractAmt_%d' % (i+1)).value()

                syrdict['notes'] = getattr(self,'notes_%d' % (i+1)).toPlainText()
                syringes.append(syrdict)
            data['syringes'] = syringes

            print(yaml.dump(data))

            f = open(filename[0],'w')
            f.write(yaml.dump(data))
            f.close()


    def openConfig(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File', '/', 'Config Files (*.syr)')
        print(filename[0])
        if(len(filename[0]) != 0):
            f = open(filename[0])
            data = yaml.load(f)

            general = data['general']

            self.jogAmt.setValue(general['jogamt'])


            for i in range(self.portComboBox.count()):
                if(self.portComboBox.itemText(i) == general['comport']):
                    self.portComboBox.setCurrentIndex(i)
                    break

            syringes = data['syringes']
            for i in range(5):
                syrdict = syringes[i]
                getattr(self, 'rate_%d' % (i+1)).setValue(syrdict['rate'])
                getattr(self, 'duration_%d' % (i+1)).setValue(syrdict['amt'])
                getattr(self, 'syringeDiam_%d' % (i+1)).setValue(syrdict['syringeSize'])

                getattr(self, 'retractAtEnd_%d' % (i+1)).checked = syrdict['retractBool']
                getattr(self, 'retractAmt_%d' % (i+1)).setValue(syrdict['retractAmt'])

                getattr(self,'notes_%d' % (i+1)).clear()
                getattr(self,'notes_%d' % (i+1)).appendPlainText(syrdict['notes'])
            f.close()

if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName("Syringe Controller")

    window = MainWindow()
    app.exec_()
