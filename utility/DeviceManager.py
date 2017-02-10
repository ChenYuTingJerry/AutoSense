# -*- coding: utf-8 -*-
'''
Created on 2015/10/27

@author: jerrychen
'''
import re
import os
import csv
from PySide import QtCore
from subprocess import check_output
from Adb import AdbCmd

SERIAL_NO = 'serial no.'
PID = 'PID'
FIELD_NAME = [SERIAL_NO, PID]
FILE_NAME = 'connect.cfg'


class Manager(object):
    """
    Manage connected information
    """

    connectedInfo = QtCore.Signal()

    def __init__(self, path):
        self.path = path
        self.filePath = self.path + '/' + FILE_NAME
        if not os.path.exists(self.filePath):
            open(self.filePath, 'a').close()

    def connectableDevices(self):
        RE = re.compile('(?P<device>[\w-]+)\s+device')
        output = AdbCmd.devices()
        devices = []
        for line in output.split('\n'):
            find = RE.match(line)
            if find:
                devices.append(find.group('device'))
                
        if len(devices) == 0:
            return devices
        
        markedDevices = self._connectingInfo()
        if len(markedDevices) == 0:
            return devices
        
        processingDevices = self._processingInfo()

        for device in markedDevices:
            if device[PID] in processingDevices:
                print 'remove  = ' + str(device)
                devices.remove(device[SERIAL_NO])
        return devices
    
    def _processingInfo(self):
        searchName = 'AutoSense'
            
        pids = []
        if os.name == 'posix':
            output = check_output(['ps', 'ax'])
            for line in output.split('\n'):
                if searchName in line or ('SenseMain.py') in line:
                    pids.append(line.split()[0])

        elif os.name == 'nt':
            output = check_output(['tasklist'])
            for line in output.split('\n'):
                if searchName in line or ('python.exe') in line:
                    pids.append(line.split()[1])

        return pids

    def _connectingInfo(self):
        devices = []
        with open(self.filePath, 'rb') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                devices.append(row)
        return devices

    def markConnected(self, serialno):
        devices = []
        hasModify = False
        with open(self.filePath, 'rb') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row[SERIAL_NO] == serialno:
                    print 'set = ' + str(os.getpid())
                    row[PID] = os.getpid()
                    hasModify = True
                
                devices.append(row)
                
        with open(self.filePath, 'wb') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELD_NAME)
            writer.writeheader()
            writer.writerows(devices)
            if not hasModify:
                writer.writerow({SERIAL_NO: serialno, PID: os.getpid()})
