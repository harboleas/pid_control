#! /usr/bin/python
##############################################################################
#
# PID GUI 
#
# Description:
#   Interfaz para el ajuste interactivo de los parametros del
#   algoritmo PID que fue implementado en Arduino  
#
# Author:
#   Hugo Arboleas <harboleas@citedef.gob.ar>
#
##############################################################################
# 
# Copyright 2015 Hugo Arboleas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from PyQt4 import QtCore 
from PyQt4 import QtGui
from PyQt4.Qwt5 import *
from main_window import *
import sys
import serial
import struct
import time


class Adquisicion(QtCore.QThread) :   
    "Thread para la adquisicion de datos serie"

    def __init__(self, port) :
        QtCore.QThread.__init__(self)

        self.port = port
                
    def run(self) :
        while True :
            # Leo la process variable (2 Bytes) enviada por el arduino  
            data_read = self.port.read(2) 
            if len(data_read) == 2 :
                data = struct.unpack("h", data_read)[0]   # convierte 2 bytes a int 
                self.emit(QtCore.SIGNAL("data_ready"), data) 
            self.msleep(5)    
         

class App(QtGui.QMainWindow) :

    def __init__(self) :

        self.app = QtGui.QApplication(sys.argv)
        QtGui.QWidget.__init__(self)

        self.main_win = Ui_MainWindow()
        self.main_win.setupUi(self)

        self.main_win.pid_on.lower()
        self.main_win.pid_off.lower()
        self.main_win.pid_on.setVisible(False)
        
        try :
            # Provoco un reset del Arduino para una conexion limpia
            arduino = serial.Serial("/dev/ttyUSB0")
            arduino.setDTR(False)
            time.sleep(1)
            arduino.flushInput()
            arduino.setDTR(True)
            arduino.close()

            self.port = serial.Serial("/dev/ttyUSB0", 115200, timeout = 0)    
        except :
            self.port = None
            print("No se puede abrir el puerto")
	else :
            self.adquisicion = Adquisicion(self.port)
            QtCore.QObject.connect(self.adquisicion, QtCore.SIGNAL("data_ready"), self.update_data)
	    self.adquisicion.start()

        self.main_win.plot.insertLegend(QwtLegend(), QwtPlot.BottomLegend) 
        self.main_win.plot_e.insertLegend(QwtLegend(), QwtPlot.BottomLegend) 

        self.main_win.plot.setCanvasBackground(QtCore.Qt.black)
        self.main_win.plot.setAxisScale(0, 0, 10000)
        self.pv_graf = QwtPlotCurve("Process Variable")
        self.pv_graf.attach(self.main_win.plot)
        self.pv_graf.setPen(QtGui.QPen(QtCore.Qt.blue, 2))

        self.sp_graf = QwtPlotCurve("Set Point")
        self.sp_graf.attach(self.main_win.plot)
        self.sp_graf.setPen(QtGui.QPen(QtCore.Qt.green, 2))

        self.main_win.plot_e.setCanvasBackground(QtCore.Qt.black)
        self.main_win.plot_e.setAxisScale(0, -1000, 1000)
        self.e_graf = QwtPlotCurve("error")
        self.e_graf.attach(self.main_win.plot_e)
        self.e_graf.setPen(QtGui.QPen(QtCore.Qt.red, 2))

        self.pv_y = [0 for i in range(300)]   
        self.sp_y = [0 for i in range(300)]
        self.e_y = [0 for i in range(300)]
        self.x = range(300)

        self.pid_on = 0
        self.set_param()
        self.show()
        self.app.exec_()        # Lazo principal
    
    def set_param(self) :

        self.sp = self.main_win.sp.value()
        self.Ts = self.main_win.Ts.value()
        self.Kp = self.main_win.Kp.value()
        self.Ki = self.main_win.Ki.value()
        self.Kd = self.main_win.Kd.value()
        if self.port :
            self.port.write(struct.pack("B", self.pid_on))     # Envia 1 byte (PID on/off)
            self.port.write(struct.pack("B", self.Ts))         # Envia 1 byte (Ts = Tiempo de muestreo)
            self.port.write(struct.pack("f", self.Kp))         # Envia 4 bytes (Kp)
            self.port.write(struct.pack("f", self.Ki))         # Envia 4 bytes (Ki)
            self.port.write(struct.pack("f", self.Kd))         # Envia 4 bytes (Kd)
            self.port.write(struct.pack("h", self.sp))         # Envia 2 bytes (Set Point)

    def on(self) :          

        self.main_win.boton_pid_on.setDisabled(True)
        self.main_win.boton_pid_off.setEnabled(True)
        self.main_win.pid_on.setVisible(True)
        self.main_win.pid_off.setVisible(False)
        self.pid_on = 1
        self.set_param()

    def off(self) :

        self.main_win.boton_pid_on.setEnabled(True)
        self.main_win.boton_pid_off.setDisabled(True)
        self.main_win.pid_off.setVisible(True)
        self.main_win.pid_on.setVisible(False)
        self.pid_on = 0
        self.set_param()

    def update_data(self, data) :

        # Actualiza los datos de los graficos
        # cada vez que recibe un dato del arduino (cada Ts ms)

        self.pv_y = self.pv_y[1:] + [data] 
        self.sp_y = self.sp_y[1:] + [self.sp]
        self.e_y = self.e_y[1:] + [self.sp - data]

        self.main_win.pv.display(data)
        self.main_win.e.display(self.sp - data)
        
        self.pv_graf.setData(self.x, self.pv_y)
        self.sp_graf.setData(self.x, self.sp_y)
        self.e_graf.setData(self.x, self.e_y)

        self.main_win.plot.replot()
        self.main_win.plot_e.replot()

if __name__ == "__main__" :   
    app = App()         

# vim: set ts=8 sw=4 tw=0 et :
