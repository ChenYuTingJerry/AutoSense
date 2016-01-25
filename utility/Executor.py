# -*- coding: utf-8 -*-
'''
Created on 2015年10月7日

@author: jerrychen
'''
import threading
import os
from PySide import QtCore


def workExecutor(cmd, arg1=None):
        if arg1:
            if type(arg1) is tuple:
                threading.Thread(target=cmd, args=arg1).start()
            else:
                threading.Thread(target=cmd, args=(arg1,)).start()  
        else:
            threading.Thread(target=cmd).start()


class Runner(QtCore.QRunnable):
    
    def __init__(self, runner, arg=None, replyId=None):
        super(Runner, self).__init__()
        self.arg = arg
        self.replyId = replyId
        self.runner = runner
    
    def run(self):
        if self.arg:
            self.runner(self.arg)
        else:
            self.runner()


class ApkInstaller(QtCore.QThread):
    onStatus = QtCore.Signal(str, str)
    done = QtCore.Signal()
    INSTALL = 'install'
    INSTALLED = 'installed'
    UNINSTALL = 'uninstall'
    UNINSTALLED = 'uninstalled'
    FINISHED = 'finished'
    FORCESTOP = 'force stop'
    
    def __init__(self, device, installList): 
        super(ApkInstaller, self).__init__()
        self.installList = installList
        self.device = device
        
    def stop(self):
        self.isStop = True
        
    def run(self):
        self.isStop = False
        for apk in self.installList:
            if not self.isStop:
                if os.path.exists(apk):
                    self.onStatus.emit(self.INSTALL, apk)
                    self.device.install(apk)
                    self.onStatus.emit(self.INSTALLED,os.path.basename(apk))
            else:
                self.done.emit()
                return
        self.done.emit()
