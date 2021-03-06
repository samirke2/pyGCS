#!/usr/bin/pythonw
# -*- coding: UTF-8 -*-

'''
MIT License

Copyright (c) 2017 Tairan Liu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import os
from os import walk
import sys
from sys import stdout

import wx
import wx.lib.embeddedimage
import wx.dataview

import logging
import threading
from threading import Thread
from wx.lib.pubsub import pub

import serial
import serial.tools.list_ports
from pyzbMultiwii import MultiWii
from QuadStates import QuadStates

import math
import time
import struct

import signal
from contextlib import contextmanager

__author__ = "Tairan Liu"
__copyright__ = "Copyright 2017, Tairan Liu"
__credits__ = ["Tairan Liu", "Other Supporters"]
__license__ = "MIT"
__version__ = "0.4-dev"
__maintainer__ = "Tairan Liu"
__email__ = "liutairan2012@gmail.com"
__status__ = "Development"

class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException, "Timed out!"
    signal.signal(signal.SIGALRM, signal_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class SerialCommunication(object):
    def __init__(self, port, addrlist):
        self.addressList = addrlist
        self.serialPort = port
        self.board = MultiWii(self.serialPort)
        self._rawData = None
        self.quadObjs = []

        path = '/Users/liutairan/Documents/PythonLab/pyGCS_dev/dev9/'
        logname = path + time.asctime() + '.log'
        self.logger = logging.getLogger('Serial Data')
        self.logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.FileHandler(logname)
        fh.setLevel(logging.DEBUG)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        # add the handlers to logger
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

        self.CreateObjs()
        self.PreLoadInfo()

    def stopSerial(self):
        self.board.stopDevice()

    def CreateObjs(self):
        for i in range(len(self.addressList)):
            if len(self.addressList[i]) > 0:
                self.quadObjs.append(QuadStates('\x01', self.addressList[i][0], self.addressList[i][1]))

    def PreLoadInfo(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            #print('pre check')
            while True:
                try:
                    with time_limit(0.5):
                        self.PreCheck(tempObj)
                        print('Warmed up')
                        break
                except:
                    self.stopSerial()
                    print('Time out warm up')
                    pass

    def PreCheck(self, obj):
        try:
            self.board.getData(0,MultiWii.BOXIDS,[],obj)
            self.logger.info(obj.activeBoxes)
        except Exception, error:
            print('Failed')
            print(Exception)
            print(error)

    def RegularLoadInfo(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            try:
                self.RegularCheck(tempObj)
            except:
                pass

    def RegularCheck(self, obj):
        try:
            self.board.getData(0,MultiWii.MSP_STATUS_EX,[],obj)
            self.board.parseSensorStatus(obj)
            self.board.parseFlightModeFlags(obj)
            self.board.getData(0,MultiWii.ATTITUDE,[],obj)
            self.board.getData(0,MultiWii.ANALOG,[],obj)
            time.sleep(0.05)
            self.board.getData(0,MultiWii.RAW_GPS,[],obj)
            time.sleep(0.05)
            #self.board.getData(0,MultiWii.GPSSTATISTICS,[],obj)
            #time.sleep(0.05)
        except Exception, error:
            print('Failed')
            print(Exception)
            print(error)

    def RegularLoadOverview(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            try:
                self.board.getDataLoose(0, MultiWii.MSP_STATUS_EX, [], tempObj, self.quadObjs)
                self.board.getDataLoose(0, MultiWii.ANALOG, [], tempObj, self.quadObjs)
            except:
                pass

    def RegularLoadAllGPS(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            try:
                self.board.getData(0,MultiWii.RAW_GPS,[],tempObj)
                self.logger.info(tempObj.msp_raw_gps)
                #self.logger.info('raw gps')
            except:
                pass

    def RegularLoadQuad1(self):
        quadObjId = 0
        tempObj = self.quadObjs[quadObjId]
        try:
            #self.board.arm(tempObj)
            self.board.getData(0,MultiWii.MSP_STATUS_EX,[],tempObj)
            self.board.parseSensorStatus(tempObj)
            self.board.parseFlightModeFlags(tempObj)
            self.board.parseArmingFlags(tempObj)
            #print('BLOCK_NAV_SAFETY:')
            #print(tempObj.armStatus['BLOCK_NAV_SAFETY'])
            self.board.getData(0,MultiWii.ANALOG,[],tempObj)
        except:
            pass

    def RegularLoadQuad2(self):
        quadObjId = 1
        for i in range(1):
            if len(self.addressList[i]) == 0:
                quadObjId = quadObjId - 1
            else:
                pass
        tempObj = self.quadObjs[quadObjId]
        try:
            self.board.getData(0,MultiWii.MSP_STATUS_EX,[],tempObj)
            self.board.parseSensorStatus(tempObj)
            self.board.parseFlightModeFlags(tempObj)
            self.board.getData(0,MultiWii.ANALOG,[],tempObj)
        except:
            pass

    def RegularLoadQuad3(self):
        quadObjId = 2
        for i in range(1):
            if len(self.addressList[i]) == 0:
                quadObjId = quadObjId - 1
            else:
                pass
        tempObj = self.quadObjs[quadObjId]
        try:
            self.board.getData(0,MultiWii.MSP_STATUS_EX,[],tempObj)
            self.board.parseSensorStatus(tempObj)
            self.board.parseFlightModeFlags(tempObj)
            self.board.getData(0,MultiWii.ANALOG,[],tempObj)
        except:
            pass

    def RegularLoadInfoLoose(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            try:
                self.board.getDataLoose(0, MultiWii.MSP_STATUS_EX, [], tempObj, self.quadObjs)
                self.board.getDataLoose(0, MultiWii.ANALOG, [], tempObj, self.quadObjs)
                self.board.getDataLoose(0, MultiWii.ATTITUDE,[],tempObj, self.quadObjs)
            except:
                print('Regular load error')
                pass

    def UploadWPs(self, mission_task):
        quadId = mission_task[0] - 10
        mission = mission_task[1]
        quadObjId = quadId - 1

        for i in range(quadId):
            if len(self.addressList[i]) == 0:
                quadObjId = quadObjId - 1
            else:
                pass
        self.quadObjs[quadObjId].missionList = mission
        print("Start upload missions. Quad: " + str(quadId))
        self.board.uploadMissions(self.quadObjs[quadObjId])
        print("All missions uploaded successfully. Quad: " + str(quadId))

    def DownloadWPs(self, mission_task):
        quadId = mission_task[0] - 20
        quadObjId = quadId - 1

        for i in range(quadId):
            if len(self.addressList[i]) == 0:
                quadObjId = quadObjId - 1
            else:
                pass
        print("Start download missions. Quad: " + str(quadId))
        self.board.downloadMissions(self.quadObjs[quadObjId])
        print("All missions downloaded successfully. Quad: " + str(quadId))

    def RegularArmAll(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            try:
                self.board.arm(tempObj)
                #self.logger.info(tempObj.msp_raw_gps)
                #self.logger.info('raw gps')
            except:
                pass
    def RegularDisarmAll(self):
        for i in range(len(self.quadObjs)):
            tempObj = self.quadObjs[i]
            try:
                self.board.disarm(tempObj)
            except:
                pass

    def StartMission(self, mission_task):
        quadId = mission_task[0] - 30
        quadObjId = quadId - 1

        for i in range(quadId):
            if len(self.addressList[i]) == 0:
                quadObjId = quadObjId - 1
            else:
                pass
        tempObj = self.quadObjs[quadObjId]
        #print("Start arm. Quad: " + str(quadId))
        self.board.arm(tempObj)
        #self.board.getData(0,MultiWii.MSP_STATUS_EX,[],tempObj)
        #self.board.parseSensorStatus(tempObj)
        #self.board.parseFlightModeFlags(tempObj)
        #self.board.parseArmingFlags(tempObj)
        #print('BLOCK_NAV_SAFETY:')
        #print(tempObj.armStatus['BLOCK_NAV_SAFETY'])
        #print('ARM:')
        #print(tempObj.flightModes['ARM'])
        #print("Armed successfully. Quad: " + str(quadId))

    def AbortMission(self, mission_task):
        quadId = mission_task[0] - 35
        quadObjId = quadId - 1

        for i in range(quadId):
            if len(self.addressList[i]) == 0:
                quadObjId = quadObjId - 1
            else:
                pass
        print("Start disarm. Quad: " + str(quadId))
        self.board.disarm(self.quadObjs[quadObjId])
        print("Disarmed successfully. Quad: " + str(quadId))


    def get_rawData(self):
        return self._rawData

    def set_rawData(self, value):
        self._rawData = value

    rawData = property(get_rawData, set_rawData)
