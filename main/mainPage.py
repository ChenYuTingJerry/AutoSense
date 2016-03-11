# -*- coding: utf-8 -*-
"""
Created on 2016/1/13

@author: Jerry Chen
"""
from __future__ import division
from Adb import AdbDevice
from autoSense import AutoSenseItem, PlayItem, TestPlanItem, TestResultItem, \
    INDEX, ACTION, PARAMETER, DESCRIPTION, INFORMATION
from Executor import workExecutor
from DeviceManager import Manager
from PySide import QtCore, QtGui
from GuiTemplate import MainTitleButton, IconButton, IconWithWordsButton, PushButton, TestPlanListView, MyLabel, \
    BottomLineWidget, HContainer, VContainer, TestPlanListItem, MyPlainTextEdit, MyProcessingBar, IntroWindow, \
    PictureLabel, ActionListView, DelayDialog, MediaCheckDialog, MyCheckBox, MyLineEdit, ListWidgetWithLine, \
    InfoListWidget, TitleButton, SearchBox, SettingIconButton, PlayQueueListView, PlayQueueListItem, ActionListItem, \
    MyProgressBar, MenuButton, MyButton, DonutPie
from constants import NFC, WIFI, AIRPLANE, GPS, AUTO_ROTATE, BLUETOOTH, DATA_ROAMING, ALLOW_APP, NO_KEEP_ACTIVITY, \
    AUTO_BRIGHTNESS, BRIGHTNESS_SET, VIBRATE, WINDOW_ANIMATOR, TRANSITION_ANIMATOR, DURATION_ANIMATION, \
    KEEP_WIFI, ICON_FOLDER, ROOT_FOLDER, FONT_FOLDER, LOG_FOLDER, SCRIPT_FOLDER, PRIVATE_FOLDER, \
    IMAGE_FOLDER, IS_RELATIVE_EXIST, IS_BLANK, IS_EXIST, NO_EXIST
import re
import os
import csv
import sys
import copy
import time
import glob
import json
import socket
import directory as folder
import subprocess
import autoSense
import uiautomator
import threading
from subprocess import CalledProcessError


PLAY_LIST_PAGE = 0
PROCESS_PAGE = 1
SEMI_CHECK_PAGE = 2
REPORT_PAGE = 3


def set_background_color(widget, color):
    """
    Paint the background of a widget
    :param widget: Pyside object
    :param color: Input color in Hex string. Like '#FFFFFF'
    """
    c = QtGui.QColor()
    c.setNamedColor(color)
    widget.setAutoFillBackground(True)
    p = widget.palette()
    p.setColor(QtGui.QPalette.Background, c)
    widget.setPalette(p)


class RunScript(QtCore.QThread):
    """
    Handle the reproduced actions and send back to device
    """
    actionResult = autoSense.FAIL
    isStopRun = False
    finish = QtCore.Signal()
    currentAction = QtCore.Signal(AutoSenseItem)
    actionDone = QtCore.Signal(AutoSenseItem, bool, int)

    def __init__(self, times=1, device=None):
        super(RunScript, self).__init__()
        self.setTimes(times)
        self.setDevice(device)
        self.actionSwitcher = {
            'Power': self.actionPower,
            'Unlock': self.actionUnlock,
            'Back': self.actionBack,
            'Click': self.actionClick,
            'Home': self.actionHome,
            'Swipe': self.actionSwipe,
            'Drag': self.actionDrag,
            'LongClick': self.actionLongClick,
            'Delay': self.actionDelay,
            'Menu': self.actionMenu,
            'Exist': self.actionCheckExist,
            'NoExist': self.actionCheckNoExist,
            'IsBlank': self.actionCheckBlank,
            'RelativeCheck': self.actionRelativeCheck,
            'Type': self.actionType,
            'MediaCheck': self.actionMediaCheck,
            'HideKeyboard': self.actionHideKeyboard,
            'CheckPoint': self.actionCheckPoint}

    def setTimes(self, times):
        """
        Set repeat times of running a script. It should set before running.
        :param times: Set by user.
        """
        self.times = times

    def setActions(self, actions):
        """
        Assign actions that want to play.
        :param actions: List of AutoSense item.
        """
        self.actions = actions

    def setDevice(self, device):
        """
        Assign a instance of device.
        :param device: AdbDevice
        """
        self._device = device

    def setPlayName(self, name):
        self.playName = name

    def checkMedia(self, passTime, timeout, isHold):
        decryptRE = re.compile('[lL]ast\s+write\s+occurred\s+\(msecs\):\s+(?P<last_write>\d+)')
        current_sec_time = lambda: time.time()
        isAlreadyPass = False
        idle = current_sec_time()
        work = idle
        hold = True if isHold == 'True' else False

        while not self.isStopRun:
            output = self._device.cmd.dumpsys(['media.audio_flinger'])
            decryptMatch = decryptRE.search(output)
            if decryptMatch is not None:
                lastWriteTime = int(decryptMatch.group('last_write'))
                if lastWriteTime < 1000:
                    idle = current_sec_time()
                    playTime = current_sec_time() - work
                    print 'play time = ' + str(playTime) + '   passTime: ' + str(passTime)
                    if playTime > passTime:
                        if hold:
                            isAlreadyPass = True
                            timeout = 2
                        else:
                            return {'result': True, 'reason': ''}
                else:
                    work = current_sec_time()
                    idleTime = current_sec_time() - idle
                    print 'idleTime = ' + str(idleTime) + ', idleTime > timeout: ' + str(idleTime > timeout)
                    if idleTime > timeout:
                        if isAlreadyPass:
                            return {'result': True, 'reason': ''}
                        else:
                            return {'result': False, 'reason': 'timeout'}
            else:
                print 'It can\'t figure out last write time.'
                return {'result': False, 'reason': 'Program can\'t define whether media is playing.'}
            time.sleep(0.1)

    def actionMediaCheck(self, param, refer=None):
        t, timeout, isHold = param
        result = self.checkMedia(int(t), int(timeout), isHold)
        if result is not None:
            if result['result']:
                self.actionResult = autoSense.PASS

    def actionRelativeCheck(self, param, refer=None):
        pass

    def actionCheckPoint(self, param, refer=None):
        self.actionResult = autoSense.SEMI

    def actionType(self, param, refer=None):
        """
        Action of typing text.
        :param param: a string
        :param refer: None
        """
        self._device.type(param[0])
        self.actionResult = autoSense.PASS

    def actionDelay(self, param, refer=None):
        """

        :param param: (int). in second.
        :param refer: None
        """
        t = int(param[0])
        D_value = 0
        container = []
        startTime = float(self._device.cmd.shell(['echo', '$EPOCHREALTIME'], output=True))
        while not self.isStopRun and D_value < t:
            currentTime = float(self._device.cmd.shell(['echo', '$EPOCHREALTIME'], output=True))
            D_value = currentTime - startTime
            self.removeLastLog.emit()
            container.append(D_value)
            if len(container) > 1:
                if not self._device.isScreenOn():
                    self._device.powerBtn()
                    if self._device.isLocked():
                        self._device.unlock()
                del container[:]
            time.sleep(1)
        self.actionResult = autoSense.PASS

    def actionUnlock(self, param, refer=None):
        """
        Unlock screen. If screen is not locked, it will do nothing.
        :param param: None
        :param refer: None
        """
        self._device.unlock()
        self.actionResult = autoSense.PASS

    def actionMenu(self, param, refer=None):
        """
        Simulate menu button is pressed.
        :param param: None
        :param refer: None
        """
        self._device.cmd.inputKeyevnt('MENU')
        self.actionResult = autoSense.PASS

    def actionPower(self, param, refer=None):
        """
        Simulate power button is pressed.
        :param param: None
        :param refer: None
        """
        self._device.cmd.inputKeyevnt('POWER')
        self.actionResult = autoSense.PASS

    def actionHome(self, param, refer=None):
        """
        Simulate home button is pressed.
        :param param: None
        :param refer: None
        """
        self._device.cmd.inputKeyevnt('HOME')
        self.actionResult = autoSense.PASS

    def actionLongClick(self, param, refer=None):
        """
        Simulate long click.
        :param param: [x, y, duration]
        :param refer: A json object include view information.
        """
        info = json.loads(refer)
        x, y, duration = param
        point = (int(x), int(y))
        self._device.longClick(point[0], point[1], int(duration))
        self.actionResult = autoSense.PASS

    def actionDrag(self, param, refer=None):
        """
        Simulate drag action. It can drag a view object if it can be dragged.
        :param param: [x1, y1, x2, y2, duration]
        :param refer: None
        """
        start = (param[0], param[1])
        end = (param[2], param[3])
        self._device.drag(start, end, int(param[4]))
        self.actionResult = autoSense.PASS

    def actionSwipe(self, param, refer=None):
        """
        Simulate swipe action. View won't be dragged
        :param param: [x1, y1, x2, y2, duration]
        :param refer: None
        """
        start = (param[0], param[1])
        end = (param[2], param[3])
        # ensure page flow
        self._device.swipe(start, end, int(param[4]))
        self.actionResult = autoSense.PASS

    def actionBack(self, param, refer=None):
        """
        Simulate back button.
        :param param: None
        :param refer: None
        """
        self._device.backBtn()
        self.actionResult = autoSense.PASS

    def actionClick(self, param, refer=None):
        """
        Simulate click action.
        :param param: [x, y]
        :param refer: A json object include view information.
        """
        info = json.loads(refer)
        if len(param) == 2:
            x, y = param
        else:
            x, y, _ = param

        point = (int(x), int(y))
        noShow = False
        wait = 5
        while self._device.isConnected() and not self.isStopRun and wait > 0:
            try:
                if not self._device.isScreenOn():
                    self._device.powerBtn()
                    if self._device.isLocked():
                        self._device.unlock()
                result = self._device.checkSamePoint(point, info)
                if result['answer']:
                    self.actionResult = autoSense.PASS
                    break
                elif not noShow:
                    print 'wait view'
                time.sleep(1)
                wait -= 1
            except uiautomator.JsonRPCError:
                break

    def actionCheckBlank(self, param, refer=None):
        """
        Check the target view should not have any child view.
        :param param: [Identification, x, y]. There are 4 kinds of identification(resourceId, text, description, className).
        :param refer: None
        """
        benchmark, x, y = param
        attribute, value = benchmark.split('=')
        point = (int(x), int(y))
        if attribute == 'text':
            selector = self._device.retrieveSelector(point, self._device.d(text=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = autoSense.PASS
            else:
                self.actionResult = autoSense.PASS

        elif attribute == 'description':
            selector = self._device.retrieveSelector(point, self._device.d(description=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = autoSense.PASS
            else:
                self.actionResult = autoSense.PASS

        elif attribute == 'resourceId':
            selector = self._device.retrieveSelector(point, self._device.d(resourceId=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = autoSense.PASS
            else:
                self.actionResult = autoSense.PASS

        elif attribute == 'className':
            selector = self._device.retrieveSelector(point, self._device.d(className=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = autoSense.PASS
            else:
                self.actionResult = autoSense.PASS

    def actionCheckExist(self, param, refer=None):
        """
        Check the target view whether is existed on the screen.
        :param param: [Identification, x, y]. There are 4 kinds of identification(resourceId, text, description, className).
        :param refer: None
        """
        benchmark, x, y = param
        attribute, value = benchmark.split('=')
        point = (int(x), int(y))
        if attribute == 'text':
            if self._device.retrieveSelector(point, self._device.d(text=value)):
                self.actionResult = self.PASS
                # self.report.emit(INFO, 'Pass: View exist', True)
            else:
                pass
                # self.report.emit(ERROR, 'Fail: View not exist', True)
                # self.isStopRun = True
        elif attribute == 'description':
            if self._device.retrieveSelector(point, self._device.d(description=value)):
                self.actionResult = self.PASS
                # self.report.emit(INFO, 'Pass: View exist', True)
            else:
                pass
                # self.report.emit(ERROR, 'Fail: View not exist', True)
                # self.isStopRun = True
        elif attribute == 'resourceId':
            if self._device.retrieveSelector(point, self._device.d(resourceId=value)):
                self.actionResult = self.PASS
                # self.report.emit(INFO, 'Pass: View exist', True)
            else:
                pass
                # self.report.emit(ERROR, 'Fail: View not exist', True)
                # self.isStopRun = True
        elif attribute == 'className':
            if self._device.retrieveSelector(point, self._device.d(className=value)):
                self.actionResult = self.PASS
                # self.report.emit(INFO, 'Pass: View exist', True)
            else:
                pass
                # self.report.emit(ERROR, 'Fail: View not exist', True)
                # self.isStopRun = True

    def actionCheckNoExist(self, param, refer=None):
        """
        Check the target view whether isn't existed on the screen.
        :param param: [Identification, x, y]. There are 4 kinds of identification(resourceId, text, description, className).
        :param refer: None
        """
        benchmark, x, y = param
        attribute, value = benchmark.split('=')
        point = (int(x), int(y))
        if attribute == 'text':
            if not self._device.retrieveSelector(point, self._device.d(text=value)):
                self.actionResult = self.PASS

        elif attribute == 'description':
            if not self._device.retrieveSelector(point, self._device.d(description=value)):
                self.actionResult = self.PASS

        elif attribute == 'resourceId':
            if not self._device.retrieveSelector(point, self._device.d(resourceId=value)):
                self.actionResult = self.PASS

        elif attribute == 'className':
            if not self._device.retrieveSelector(point, self._device.d(className=value)):
                self.actionResult = self.PASS

    def actionHideKeyboard(self, param, refer=None):
        """
        Hide soft keyboard. If keyboard isn't showed, it will do nothing.
        :param param: None
        :param refer: None
        """
        self._device.hideKeyboard()
        self.actionResult = self.PASS

    def stop(self):
        """
        Exit this process.
        """
        self.isStopRun = True

    def setStartIndex(self, index):
        """
        chose a start index of actions.
        :param index: integer
        """
        self.startIndex = index

    def run(self):
        self.isStopRun = False
        self.limit = 0
        try:
            self._device.takeSnapshot(IMAGE_FOLDER + '/%s_%d.png' % (self.playName, 0))
            while self.limit < self.times and not self.isStopRun:
                self.limit += 1
                for index in range(len(self.actions)):
                    if not self.isStopRun and self.startIndex <= index:
                        self.index = index + 1
                        item = self.actions[index]
                        if self._device.isConnected():
                            self.actionResult = autoSense.FAIL
                            self.currentAction.emit(item)
                            self.actionSwitcher.get(item.action())(item.parameter(), item.information())
                            self._device.takeSnapshot(IMAGE_FOLDER + '/%s_%d.png' % (self.playName, self.index))
                            self.actionDone.emit(item, self.actionResult, index)
                        else:
                            self.isStopRun = True
                            break

        except socket.error:
            print 'socket.error: device offline'
            self.isStopRun = True
        except ValueError as e:
            print 'ValueError: ' + e.message
            self.isStopRun = True
        except CalledProcessError, exc:
            print 'CalledProcessError: ' + str(exc)
            self.isStopRun = True
        finally:
            self.finish.emit()


class UpdateScreen(QtCore.QThread):
    """
    Keep capturing screen in the background.
    """
    loadDone = QtCore.Signal()
    startLoad = QtCore.Signal()
    deviceOffline = QtCore.Signal()
    isStop = False
    isPause = False

    def __init__(self, device, picPath):
        super(UpdateScreen, self).__init__()
        self.isStop = False
        self._device = device
        self.delay = 0
        self.picPath = picPath
        self.lastFrameTime = 0
        self.isRefresh = False
        self.nconcurrent = threading.BoundedSemaphore(5)

    def stop(self):
        """ Stop capturing """
        self.isStop = True

    def pause(self):
        """ Pause capturing """
        self.isPause = True

    def resume(self):
        """ resume capturing """
        self.isPause = False

    def setDelay(self, delay=0):
        """ Set a delay time to start capturing """
        self.delay = delay

    def run(self):
        time.sleep(self.delay)
        try:
            self.isStop = False
            while not self.isStop:
                if not self.isPause and self.monitorFrame():
                    self.startLoad.emit()
                    self.screenshot(path=self.picPath + '/' + self._device.serialno + '_screen.png')
                else:
                    time.sleep(0.2)
        except:
            print 'device not found'
            self.lastFrameTime = 0
            self.deviceOffline.emit()

    def monitorFrame(self):
        """
        monitor the screen has changed, it helps to reduce capturing frequency.
        """
        decryptRE = re.compile('\s+events-delivered:\s+(?P<number>\d+)')
        output = self._device.cmd.dumpsys(['SurfaceFlinger'])
        if output:
            m = decryptRE.search(output)
            if m is not None:
                tmpTime = m.group('number')
                if tmpTime != self.lastFrameTime:
                    self.lastFrameTime = tmpTime
                    return True

    def screenshot(self, path, delay=0):
        """
        Do screen capture
        :param path: save pic path
        :param delay: delay to capture screen. In second.
        """
        try:
            self.nconcurrent.acquire()
            time.sleep(delay)
            pp = time.time()
            if self._device.isConnected():
                self._device.takeSnapshot(path)
            else:
                if not self.isStop:
                    self.deviceOffline.emit()
            print time.time() - pp
            if not self.isStop:
                self.loadDone.emit()
        except AttributeError as e:
            print e.message
        except IOError as e:
            print e.message
        finally:
            self.nconcurrent.release()


class WaitForDevice(QtCore.QThread):
    '''
    Monitor device to be connected to computer.
    '''
    online = QtCore.Signal()

    def __init__(self, device):
        super(WaitForDevice, self).__init__()
        self.device = device
        self.isStop = False

    def stop(self):
        """
        Stop to wait device
        """
        self.isStop = True

    def run(self):
        print 'start to monitor'
        self.isStop = False
        while not self.isStop:
            if self.device.isConnected():
                try:
                    print 'start to connect'
                    self.device.connect()
                    if not self.isStop:
                        self.online.emit()
                    break
                except:
                    print 'Keep searching'
            time.sleep(1)


class DeviceInfoThread(QtCore.QThread):
    """
    Get device information in background. Include brand,
    modle name, serial number, android version, region, resolution,
    manufacturer name, product name and kernel number.
    """
    onDeviceInfo = QtCore.Signal(dict)

    def __init__(self, serialno=None):
        super(DeviceInfoThread, self).__init__()
        self.serialNo = serialno

    def setDeviceId(self, ID):
        """
        Set a seria; number of target device.
        :param ID: device serial number
        """
        self.serialNo = ID

    def run(self):
        holdInfo = dict()
        device = AdbDevice(self.serialNo)
        for prop in device.getProp().split('\n'):
            proper = prop.replace('[', '').replace(']', '').split(':')
            if proper[0] == 'ro.product.brand':
                holdInfo['brand'] = proper[1].strip()
            elif proper[0] == 'ro.product.model':
                holdInfo['model'] = proper[1].strip()
            elif proper[0] == 'ro.serialno':
                holdInfo['serialNo'] = proper[1].strip()
            elif proper[0] == 'ro.build.version.release':
                holdInfo['android'] = proper[1].strip()
            elif proper[0] == 'ro.build.display.id':
                holdInfo['buildNo'] = proper[1].strip()
            elif proper[0] == 'ro.product.locale.region':
                holdInfo['region'] = proper[1].strip()
            elif proper[0] == 'ro.product.manufacturer':
                holdInfo['manufacturer'] = proper[1].strip()
            elif proper[0] == 'ro.product.name':
                holdInfo['name'] = proper[1].strip()

        holdInfo['kernelNo'] = device.cmd.shell(['cat', 'proc/version'], output=True).strip('\r\n')
        display = device.getRealDisplay()
        holdInfo['resolution'] = str(display['width']) + ' x ' + str(display['height'])

        self.onDeviceInfo.emit(holdInfo)


class DeviceSettingsThread(QtCore.QThread):
    """
    Get device environment states. Include NFC, WiFi, airplan mode,
    GPS, AutoRotate, Bluetooth, Brightness, install unknown app,
    Vibrate, Auto-Brightness, Window animator, transition animator,
    duration animation and no keep activity.
    """
    currentSettings = QtCore.Signal(dict, bool)
    device = None

    def __init__(self):
        super(DeviceSettingsThread, self).__init__()

    def setDevice(self, device):
        """
        Set target device.
        :param device: AdbDevice
        """
        self.device = device

    def run(self):
        try:
            xx = dict()
            xx[NFC] = self.device.isNfcOn()
            xx[WIFI] = self.device.isWifiOn()
            xx[AIRPLANE] = self.device.isAirPlaneModeOn()
            xx[GPS] = self.device.isGpsOn()
            xx[AUTO_ROTATE] = self.device.isAutoRotateOn()
            xx[BLUETOOTH] = self.device.isBtOn()
            xx[DATA_ROAMING] = self.device.isDataRoamingOn()
            xx[ALLOW_APP] = self.device.isInstallUnknownSources()
            xx[NO_KEEP_ACTIVITY] = self.device.isNoKeepActivityOn()
            xx[AUTO_BRIGHTNESS] = self.device.isAutoBrightnessOn()
            xx[BRIGHTNESS_SET] = self.device.screenTimeout()
            xx[VIBRATE] = self.device.isVibrateWhenRingOn()
            xx[WINDOW_ANIMATOR] = self.device.isWindowAniOn()
            xx[TRANSITION_ANIMATOR] = self.device.isTransitionAnuOn()
            xx[DURATION_ANIMATION] = self.device.isDurationAniOn()
            self.currentSettings.emit(xx, True)
        except subprocess.CalledProcessError:
            self.currentSettings.emit(dict(), False)


class PackagesThread(QtCore.QThread):
    """
    Get packages name in device. Include all, system, 3rd party and recent.
    """
    currentPackages = QtCore.Signal(list)
    device = None
    t = ''

    def __init__(self):
        super(PackagesThread, self).__init__()

    def setDevice(self, device):
        """
        Set target device.
        :param device: AdbDevice
        """
        self.device = device

    def setType(self, t):
        """
        Set package type
        :param t: request package type
        """
        self.t = t

    def run(self):
        self.currentPackages.emit(self.device.requestPackage(self.t))


class SendSettingThread(QtCore.QThread):
    """
    Set device environment states. Include NFC, WiFi, airplan mode,
    GPS, AutoRotate, Bluetooth, Brightness, install unknown app,
    Vibrate, Auto-Brightness, Window animator, transition animator,
    duration animation and no keep activity.
    """
    mDict = dict()
    done = QtCore.Signal()

    def __init__(self, settingDict, device):
        super(SendSettingThread, self).__init__()
        self.mDict = settingDict
        self.device = device

    def run(self):
        needReboot = False
        for key, value in self.mDict.iteritems():
            print 'key = ' + key
            if key == AIRPLANE:
                self.device.enableAirplaneMode(value)
            elif key == NFC:
                self.device.enableNfc(value)
            elif key == ALLOW_APP:
                self.device.enableInstallUnknownSources(value)
            elif key == WIFI:
                self.device.enableWifi(value)
            elif key == BLUETOOTH:
                self.device.enableBluetooth(value)
            elif key == NO_KEEP_ACTIVITY:
                self.device.enableNoKeepActivity(value)
            elif key == DATA_ROAMING:
                self.device.enableDataRoaming(value)
            elif key == AUTO_ROTATE:
                self.device.enableAutoRotate(value)
            elif key == GPS:
                self.device.enableGps(value)
            elif key == AUTO_BRIGHTNESS:
                self.device.enableAutoBrightness(value)
            elif key == VIBRATE:
                self.device.enableVibrateWhenRing(value)
            elif key == BRIGHTNESS_SET:
                self.device.setScreenTimeout(str(long(value) * 1000))
            elif key == WINDOW_ANIMATOR:
                if self.device.isWindowAniOn() != value:
                    self.device.enableWindowAnimator(not value)
                    needReboot = True
            elif key == TRANSITION_ANIMATOR:
                if self.device.isTransitionAnuOn() != value:
                    self.device.enableTransitionAnimator(not value)
                    needReboot = True
            elif key == DURATION_ANIMATION:
                print self.device.isDurationAniOn() != value
                if self.device.isDurationAniOn() != value:
                    self.device.enableDurationAnimation(not value)
                    needReboot = True

        self.sleep(5)
        if needReboot:
            print 'reboot'
            self.device.reboot()

        while needReboot:
            self.sleep(2)
            try:
                if self.device.isConnected():
                    self.device.screenTimeout()
                    needReboot = False
            except ValueError:
                pass
        self.done.emit()


class InstallThread(QtCore.QThread):
    """
    Install app
    """
    done = QtCore.Signal()

    def __init__(self, f, device):
        super(InstallThread, self).__init__()
        self.f = f
        self.device = device

    def run(self):
        self.device.install(self.f)
        self.done.emit()


class LandingPage(IntroWindow):
    """
    Program entry point.
    """
    w = None

    def __init__(self):
        super(LandingPage, self).__init__()
        logo = QtGui.QPixmap(ICON_FOLDER + '/' + 'ic_logo_with_shadow.png')
        self.lbl = QtGui.QLabel()
        self.lbl.setPixmap(logo)

        self.welcomeTitle = QtGui.QLabel('Welcome to Autosense')
        font = self.welcomeTitle.font()
        font.setBold(False)
        font.setPixelSize(30)
        self.welcomeTitle.setFont(font)

        self.welcomeSubTitle = QtGui.QLabel('What do you want to do first?')
        self.welcomeSubTitle.setStyleSheet('font: Light')
        font = self.welcomeSubTitle.font()
        font.setPixelSize(12)
        font.setWeight(QtGui.QFont.Light)
        self.welcomeSubTitle.setFont(font)

        self.createBtn = QtGui.QPushButton()
        self.createBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_create_testplan_normal.png'))
        self.createBtn.setStyleSheet('border: 0px')
        self.createBtn.setIconSize(QtCore.QSize(40, 40))
        self.createBtn.clicked.connect(self.button_clicked)
        self.createTitle = QtGui.QLabel('Create Testplan')
        self.createTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.createLayout = QtGui.QVBoxLayout()
        self.createLayout.addWidget(self.createBtn)
        self.createLayout.addWidget(self.createTitle)
        self.createLayout.setSpacing(0)
        self.createLayout.setContentsMargins(0, 0, 36, 0)

        self.loadBtn = QtGui.QPushButton()
        self.loadBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_load_testplan_normal.png'))
        self.loadBtn.setStyleSheet('border: 0px')
        self.loadBtn.setIconSize(QtCore.QSize(40, 40))
        self.loadTitle = QtGui.QLabel('Load Testplan')
        self.loadTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.loadLayout = QtGui.QVBoxLayout()
        self.loadLayout.addWidget(self.loadBtn)
        self.loadLayout.addWidget(self.loadTitle)
        self.loadLayout.setSpacing(0)
        self.loadLayout.setContentsMargins(0, 0, 0, 0)

        self.readBtn = QtGui.QPushButton()
        self.readBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_read_userguide.png'))
        self.readBtn.setStyleSheet('border: 0px')
        self.readBtn.setIconSize(QtCore.QSize(128, 128))
        self.readTitle = QtGui.QLabel('Read\nUser Guide')
        self.readTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.readLayout = QtGui.QVBoxLayout()
        self.readLayout.addWidget(self.readBtn)
        self.readLayout.addWidget(self.readTitle)
        self.readLayout.setSpacing(0)
        self.readLayout.setContentsMargins(36, 0, 0, 0)

        self.noShowCheck = QtGui.QCheckBox('Show this window when Autosense open')

        self.initUI()

    def initUI(self):
        titleLayout = QtGui.QVBoxLayout()
        titleLayout.setSpacing(5)
        titleLayout.setContentsMargins(0, 78, 0, 0)
        titleLayout.addWidget(self.lbl, alignment=QtCore.Qt.AlignHCenter)
        titleLayout.addWidget(self.welcomeTitle, alignment=QtCore.Qt.AlignHCenter)
        titleLayout.addWidget(self.welcomeSubTitle, alignment=QtCore.Qt.AlignHCenter)
        titleWidget = QtGui.QWidget()
        titleWidget.setLayout(titleLayout)
        titleWidget.setFixedSize(titleLayout.sizeHint())

        choseLayout = QtGui.QHBoxLayout()
        choseLayout.addLayout(self.createLayout)
        choseLayout.addLayout(self.loadLayout)
        choseWidget = QtGui.QWidget()
        choseWidget.setLayout(choseLayout)
        choseWidget.setFixedSize(choseLayout.sizeHint())

        bottomLayout = QtGui.QVBoxLayout()
        bottomLayout.addWidget(self.noShowCheck)
        bottomLayout.setContentsMargins(10, 0, 0, 0)
        bottomWidget = QtGui.QWidget()
        bottomWidget.setLayout(bottomLayout)

        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(40)
        mainLayout.addWidget(titleWidget, alignment=QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        mainLayout.addWidget(choseWidget, alignment=QtCore.Qt.AlignCenter)
        mainLayout.addWidget(bottomWidget, alignment=QtCore.Qt.AlignBottom)
        mainLayout.setContentsMargins(0, 0, 0, 0)

        self.setCentralLayout(mainLayout)
        self.setOkBtnText('Close')
        self.okBtn.clicked.connect(self.close)
        self.setWindowTitle('Autosense')
        self.setStyleSheet('color: #585858')
        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())
        self.setFixedSize(896, 494)
        self.show()
        self.raise_()

    def button_clicked(self):
        self.newPage = ChoseDevicePage()
        self.newPage.show()
        self.newPage.raise_()
        self.close()


class CreateNewPage(IntroWindow):
    """
    This is a creating testplan page, user can input name and description.
    """

    def __init__(self):
        super(CreateNewPage, self).__init__()
        self.nameLabel = QtGui.QLabel('Testplan name')
        font = self.nameLabel.font()
        font.setPixelSize(12)
        self.nameLabel.setFont(font)
        self.nameLabel.setContentsMargins(0, 15, 0, 0)
        self.nameInput = QtGui.QLineEdit('TEST_PLAN')
        self.nameInput.setFixedSize(300, 30)
        self.describeLabel = QtGui.QLabel('Testplan description')
        font = self.describeLabel.font()
        font.setPixelSize(12)
        self.describeLabel.setFont(font)
        self.describeLabel.setContentsMargins(0, 15, 0, 0)
        self.describeInput = QtGui.QPlainTextEdit('William Shakespeare was the '
                                                  'son of John Shakespeare, an alderman a'
                                                  'nd a successful glover originally from Snitterfield, '
                                                  'and Mary Arden, the daughter of an affluent landowning farmer.')
        self.describeInput.setFixedSize(300, 270)
        self.warningLabel = QtGui.QLabel('You must fill all textfield to finish this step')
        font = self.warningLabel.font()
        font.setPixelSize(12)
        self.warningLabel.setFont(font)
        self.icon = QtGui.QPixmap(ICON_FOLDER + '/ic_warning.png')
        self.iconLabel = QtGui.QLabel()
        self.iconLabel.setPixmap(self.icon)
        self.initUI()

    def initUI(self):
        gridLayout = QtGui.QVBoxLayout()
        gridLayout.addWidget(self.nameLabel)
        gridLayout.addWidget(self.nameInput)
        gridLayout.addWidget(self.describeLabel)
        gridLayout.addWidget(self.describeInput)
        gridLayout.setContentsMargins(0, 0, 0, 0)
        gridWidget = QtGui.QWidget()
        gridWidget.setLayout(gridLayout)
        gridWidget.setFixedSize(gridLayout.sizeHint())

        waringLayout = QtGui.QHBoxLayout()
        waringLayout.addWidget(self.iconLabel)
        waringLayout.addWidget(self.warningLabel)
        waringLayout.setContentsMargins(0, 0, 0, 0)
        self.warningWidget = QtGui.QWidget()
        self.warningWidget.setLayout(waringLayout)
        self.warningWidget.setFixedSize(waringLayout.sizeHint())

        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(gridWidget, alignment=QtCore.Qt.AlignHCenter)
        mainLayout.addWidget(self.warningWidget, alignment=QtCore.Qt.AlignHCenter)
        self.setCentralLayout(mainLayout)
        self.setOkBtnText('Next')
        self.setWindowTitle('Create New Testplan')
        self.setStyleSheet('color: #585858')
        self.okBtn.clicked.connect(self.button_clicked)
        self.setFixedSize(gridLayout.sizeHint().width() + 400, self.sizeHint().height())

        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())
        self.warningWidget.setHidden(True)

    def button_clicked(self):
        if len(self.nameInput.text()) == 0 or len(self.describeInput.toPlainText()) == 0:
            self.warningWidget.setHidden(False)
        else:
            self.accept()

    def getName(self):
        return self.nameInput.text()

    def getDescription(self):
        return self.describeInput.toPlainText()

    @staticmethod
    def getTestPlan():
        """
        It can get name and description.
        :return: (testplan name, testplan description, result)
        """
        window = CreateNewPage()
        result = window.exec_()
        return window.getName(), window.getDescription(), result


class ChoseDevicePage(IntroWindow):
    """
    It will list all connected devices and let user to chose.
    """
    deviceInfoT = DeviceInfoThread()
    currentSelectChange = False

    def __init__(self):
        super(ChoseDevicePage, self).__init__()
        self.listTitle = QtGui.QLabel('Device List')
        self.listTitle.setStyleSheet('color: white; font: 14px')
        self.listTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.refreshBtn = IconButton()
        self.refreshBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_refresh_normal.png'))
        self.refreshBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_refresh_press.png'))
        self.refreshBtn.clicked.connect(self.refreshDeviceList)
        self.refreshBtn.setIconSize(QtCore.QSize(16, 16))
        self.refreshBtn.setFixedSize(self.refreshBtn.sizeHint())

        self.infoTitle = QtGui.QLabel('Device Information')
        self.infoTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.infoTitle.setStyleSheet('font-size: 14px')
        self.infoTitle.setFixedHeight(40)
        self.infoTitle.setAutoFillBackground(True)
        p = self.infoTitle.palette()
        p.setColor(self.infoTitle.backgroundRole(), QtGui.QColor(202, 202, 202))
        self.infoTitle.setPalette(p)

        self.infoDeviceName = QtGui.QLabel()
        self.infoDeviceName.setAlignment(QtCore.Qt.AlignCenter)

        self.deviceList = ListWidgetWithLine()
        self.deviceList.itemClicked.connect(self.itemChose)
        self.deviceList.itemSelectionChanged.connect(self.itemChanged)
        self.infoList = InfoListWidget()
        self.deviceName = QtGui.QLabel()
        self.deviceName.setFixedHeight(30)
        self.deviceName.setStyleSheet('border: 1px solid #CACACA; background-color: white; padding-left: 11px')
        font = self.deviceName.font()
        font.setPixelSize(14)
        self.deviceName.setFont(font)
        self.setAutoFillBackground(True)
        self.deviceInfoT.onDeviceInfo.connect(self.refreshInfoList)

        self.initUi()

    def initUi(self):
        deviceTitleLayout = QtGui.QHBoxLayout()
        deviceTitleLayout.addWidget(self.listTitle)
        deviceTitleLayout.addWidget(self.refreshBtn)
        deviceTitleLayout.setContentsMargins(0, 0, 0, 0)
        deviceTitleLayout.setSpacing(0)
        deviceTitleWidget = QtGui.QWidget()
        deviceTitleWidget.setLayout(deviceTitleLayout)
        deviceTitleWidget.setFixedHeight(40)
        deviceTitleWidget.setAutoFillBackground(True)
        p = deviceTitleWidget.palette()
        p.setColor(deviceTitleWidget.backgroundRole(), QtGui.QColor(74, 74, 74))
        deviceTitleWidget.setPalette(p)

        deviceLayout = QtGui.QVBoxLayout()
        deviceLayout.addWidget(deviceTitleWidget)
        deviceLayout.addWidget(self.deviceList)
        deviceLayout.setSpacing(0)
        deviceLayout.setContentsMargins(0, 0, 0, 0)
        deviceWidget = QtGui.QWidget()
        deviceWidget.setLayout(deviceLayout)
        deviceWidget.setFixedSize(396, 402)

        infoLayout = QtGui.QVBoxLayout()
        infoLayout.addWidget(self.infoTitle)
        infoLayout.addWidget(self.deviceName)
        infoLayout.addWidget(self.infoList)
        infoLayout.setContentsMargins(0, 0, 0, 0)
        infoLayout.setSpacing(0)
        infoWidget = QtGui.QWidget()
        infoWidget.setLayout(infoLayout)
        infoWidget.setFixedSize(396, 402)

        mainLayout = QtGui.QHBoxLayout()
        mainLayout.addWidget(deviceWidget)
        mainLayout.addWidget(infoWidget)
        mainLayout.setSpacing(20)
        mainLayout.setContentsMargins(42, 30, 42, 50)

        self.setCentralLayout(mainLayout)
        self.setOkBtnText('Create')
        self.okBtn.clicked.connect(self.create_click)
        self.setLeaveBtnText('Setting')
        self.leaveBtn.clicked.connect(self.setting_click)
        self.setWindowTitle('Select Device')
        self.setStyleSheet('color: #585858')
        self.setFixedSize(mainLayout.sizeHint().width(), self.sizeHint().height())

        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())

        if self.refreshDeviceList():
            self.show()
            self.raise_()

    def create_click(self):
        """
        Jump to Main page
        """
        items = self.deviceList.selectedItems()
        if len(items) == 1:
            print items[0].text()
            self.w = MainPage(items[0].text())
            self.w.show()
            self.w.raise_()
            self.close()
        else:
            print 'No selected item'

    def setting_click(self):
        """
        Jump to Setting page
        """
        if self.deviceList.currentItem():
            self.w = SettingPage(self.deviceList.currentItem().text())
            self.w.show()
            self.w.raise_()
            self.close()

    def refreshDeviceList(self):
        """
        Refresh connected device list
        """
        self.deviceList.clear()
        self.infoList.clear()
        self.deviceName.setText('')
        devices = self.askForDevices()
        if len(devices) == 0:
            self.w = NoConnectDevicePage()
            self.w.show()
            self.w.raise_()
            self.close()
            return False
        else:
            self.loadDeviceList(devices)
            return True

    def loadDeviceList(self, devices):
        """
        load connected to to list view
        :param devices: connected devices
        """
        self.deviceList.addCustomItems(devices)

    def askForDevices(self):
        manager = Manager(ROOT_FOLDER)
        devices = manager.connectableDevices()
        return devices

    def invokeDeviceInfo(self, text):
        self.deviceInfoT.setDeviceId(text)
        self.deviceInfoT.start()

    @QtCore.Slot(QtGui.QListWidgetItem)
    def itemChose(self, item):
        if not self.deviceInfoT.isRunning() and self.currentSelectChange:
            self.invokeDeviceInfo(item.text())
            self.currentSelectChange = False

    @QtCore.Slot(list)
    def refreshInfoList(self, infos):
        print infos
        self.infoList.clear()
        items = self.deviceList.selectedItems()
        if len(items) != 0:
            if infos.get('serialNo') == items[0].text():
                self.deviceName.setText(infos.get('brand') + '-' + infos.get('name'))
                self.infoList.addInfos(infos)
            else:
                self.invokeDeviceInfo(self.deviceList.currentItem().text())
        else:
            pass

    def itemChanged(self):
        self.currentSelectChange = True


class QueueAddPage(IntroWindow):
    deviceInfoT = DeviceInfoThread()
    currentSelectChange = False

    def __init__(self, planDict):
        super(QueueAddPage, self).__init__()
        self.planDict = planDict
        fromLabel = MyLabel('From', font_size=14)
        self.fromEdit = MyLineEdit(color='#585858')
        self.fromEdit.setInputMask('0000')
        self.fromEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.fromEdit.setFixedWidth(70)
        fromContainer = HContainer()
        fromContainer.setSpacing(5)
        fromContainer.addWidget(fromLabel)
        fromContainer.addWidget(self.fromEdit)

        toLabel = MyLabel('To', font_size=14)
        self.toEdit = MyLineEdit(color='#585858')
        self.toEdit.setAlignment(QtCore.Qt.AlignCenter)
        self.toEdit.setInputMask('0000')
        self.toEdit.setFixedWidth(70)
        toContainer = HContainer()
        toContainer.setSpacing(5)
        toContainer.addWidget(toLabel)
        toContainer.addWidget(self.toEdit)

        repeatLabel = MyLabel('Repeat', font_size=14)
        self.repeatEdit = MyLineEdit(color='#585858')
        self.repeatEdit.setInputMask('0000')
        self.repeatEdit.setFixedWidth(70)
        self.repeatEdit.setAlignment(QtCore.Qt.AlignCenter)
        repeatContainer = HContainer()
        repeatContainer.setSpacing(5)
        repeatContainer.addWidget(repeatLabel)
        repeatContainer.addWidget(self.repeatEdit)

        self.rangeContainer = HContainer()
        self.rangeContainer.setSpacing(30)
        self.rangeContainer.addWidget(fromContainer)
        self.rangeContainer.addWidget(toContainer)
        self.rangeContainer.addWidget(repeatContainer)
        self.rangeContainer.setAutoFitSize()

        self.combo = QtGui.QComboBox()
        self.combo.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.combo.addItems(self.planDict.keys())
        self.combo.activated[str].connect(self.onActivated)
        self.initialEdit(self.combo.currentText())

        self.comboContainer = HContainer()
        self.comboContainer.addWidget(self.combo)
        self.comboContainer.setFixedWidth(self.rangeContainer.sizeHint().width())

        self.label = MyLabel('Tips:', font_size=14, font_weight=QtGui.QFont.Light)
        self.label.setAlignment(QtCore.Qt.AlignTop)
        self.content = MyLabel('If you don\'t input any data, it will add <b>default</b> testplan to<br>queue. '
                               '(<b>From beginning to end and repeat one time.</b>)', font_size=14,
                               font_weight=QtGui.QFont.Light)

        self.tipsContainer = HContainer()
        self.tipsContainer.setSpacing(5)
        self.tipsContainer.addWidget(self.label)
        self.tipsContainer.addWidget(self.content)
        self.initUi()

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)
        mainLayout.addWidget(self.rangeContainer)
        mainLayout.addWidget(self.comboContainer)
        mainLayout.addWidget(self.tipsContainer)

        self.setCentralLayout(mainLayout)
        self.setOkBtnText('Add')
        self.okBtn.clicked.connect(self.accept)
        self.setLeaveBtnText('Cancel')
        self.leaveBtn.clicked.connect(self.reject)
        self.setWindowTitle('Add to play queue')
        self.setStyleSheet('color: #585858')
        self.setFixedSize(mainLayout.sizeHint().width() + 50, self.sizeHint().height() + 100)

        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())

    def getPlan(self):
        return self.combo.currentText()

    def getFrom(self):
        return self.fromEdit.text()

    def getTo(self):
        return self.toEdit.text()

    def getRepeat(self):
        return self.repeatEdit.text()

    def onActivated(self, text):
        self.initialEdit(text)

    def initialEdit(self, text):
        actions = self.planDict.get(text).actions()
        self.fromEdit.setText('1')
        self.toEdit.setText(str(len(actions)))
        self.repeatEdit.setText('1')

    @staticmethod
    def getInformation(planDict):
        w = QueueAddPage(planDict)
        result = w.exec_()
        return w.getPlan(), w.getFrom(), w.getTo(), w.getRepeat(), result


class NoConnectDevicePage(IntroWindow):
    def __init__(self):
        super(NoConnectDevicePage, self).__init__()
        self.noConnectPix = QtGui.QPixmap(ICON_FOLDER + '/ic_no_connect.png')
        self.noConnectPixLbl = QtGui.QLabel()
        self.noConnectPixLbl.setPixmap(self.noConnectPix)

        self.noConnectTitle = MyLabel('No device connected', font_size=20, font_weight=QtGui.QFont.Light)
        self.noConnectTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.noConnectSubTitle = MyLabel('Woops,\n'
                                         'We found you doesn\'t connect any device.\n'
                                         'Please connect a device for creating a new Testplan'
                                         , font_size=12, font_weight=QtGui.QFont.Light)
        self.noConnectSubTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.noConnectSubTitle.setContentsMargins(0, 0, 0, 40)
        self.initUi()

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.noConnectPixLbl)
        mainLayout.addWidget(self.noConnectTitle)
        mainLayout.addWidget(self.noConnectSubTitle)
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)

        self.setCentralLayout(mainLayout)
        self.setWindowTitle('No Device')
        self.setOkBtnText('OK')
        self.setStyleSheet('color: #585858')
        self.okBtn.clicked.connect(self.button_click)
        self.setFixedSize(self.sizeHint())

        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())
        self.show()
        self.raise_()

    def button_click(self):
        self.f = ChoseDevicePage()
        self.close()


class SettingPage(IntroWindow):
    deviceSettingThread = DeviceSettingsThread()
    packageThread = PackagesThread()

    def __init__(self, serialNo):
        super(SettingPage, self).__init__()
        self.changeDict = dict()
        self.checkBoxDict = dict()
        self.filterText = ''
        self.isGetting = False
        self.device = AdbDevice(serialNo)
        self.deviceSettingThread.setDevice(self.device)
        self.deviceSettingThread.currentSettings.connect(self.onCurrentSettings)
        self.packageThread.setDevice(self.device)
        self.packageThread.currentPackages.connect(self.onReceivePackageList)

        self.upsideBar()
        self.initialGeneralPage()
        self.initialManagerPage()
        self.dowsideContent()
        self.initUi()

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(self.upsideWidget)
        mainLayout.addWidget(self.downsideWidget)
        self.setCentralLayout(mainLayout)
        self.setWindowTitle('Setting')
        self.setOkBtnText('Save')
        self.okBtn.clicked.connect(self.saveClick)
        self.setLeaveBtnText('Cancel')
        self.leaveBtn.clicked.connect(self.cancelClick)
        self.setStyleSheet('color: #585858')

        x = self.getScreenGeometry().width() / 2 - self.sizeHint().width() / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x, y, self.sizeHint().width(), self.sizeHint().height())
        self.show()
        self.raise_()
        self.generalBtn.click()

    def initialGeneralPage(self):
        self.networkGroup = MyLabel('Network', font_size=14)
        self.deviceGroup = MyLabel('Device', font_size=14)
        self.animationGroup = MyLabel('Animation (Require Reboot)', font_size=14)

        self.airplaneBox = MyCheckBox('Airplane mode', font_weight=QtGui.QFont.Light, font_size=12, identity='airplane')
        self.airplaneBox.onStateChanged.connect(self.checkBoxChanged)
        self.btBox = MyCheckBox('Bluetooth', font_weight=QtGui.QFont.Light, font_size=12, identity='bt')
        self.btBox.onStateChanged.connect(self.checkBoxChanged)
        self.roamingBox = MyCheckBox('Data roaming', font_weight=QtGui.QFont.Light, font_size=12, identity='roaming')
        self.roamingBox.onStateChanged.connect(self.checkBoxChanged)
        self.gpsBox = MyCheckBox('GPS', font_weight=QtGui.QFont.Light, font_size=12, identity='gps')
        self.gpsBox.onStateChanged.connect(self.checkBoxChanged)
        self.nfcBox = MyCheckBox('NFC', font_weight=QtGui.QFont.Light, font_size=12, identity='nfc')
        self.nfcBox.onStateChanged.connect(self.checkBoxChanged)
        self.wifiBox = MyCheckBox('WIFI', font_weight=QtGui.QFont.Light, font_size=12, identity='wifi')
        self.wifiBox.onStateChanged.connect(self.checkBoxChanged)

        self.checkBoxDict[AIRPLANE] = self.airplaneBox
        self.checkBoxDict[BLUETOOTH] = self.btBox
        self.checkBoxDict[DATA_ROAMING] = self.roamingBox
        self.checkBoxDict[GPS] = self.gpsBox
        self.checkBoxDict[NFC] = self.nfcBox
        self.checkBoxDict[WIFI] = self.wifiBox

        oneVbox = QtGui.QVBoxLayout()
        oneVbox.setContentsMargins(0, 0, 0, 0)
        oneVbox.addWidget(self.networkGroup)
        oneVbox.addWidget(self.airplaneBox)
        oneVbox.addWidget(self.btBox)
        oneVbox.addWidget(self.roamingBox)
        oneVbox.addWidget(self.gpsBox)
        oneVbox.addWidget(self.nfcBox)
        oneVbox.addWidget(self.wifiBox)
        oneVbox.addStretch(1)
        oneVbox.setSpacing(12)

        self.leftWidget = QtGui.QWidget()
        self.leftWidget.setLayout(oneVbox)
        self.leftWidget.setFixedSize(oneVbox.sizeHint().width(), 398)

        self.autoRotateBox = MyCheckBox('Auto rotate', font_weight=QtGui.QFont.Light, font_size=12,
                                        identity='auto_rotate')
        self.autoRotateBox.onStateChanged.connect(self.checkBoxChanged)
        self.autoBrightnessBox = MyCheckBox('Adaptie brightness', font_weight=QtGui.QFont.Light, font_size=12,
                                            identity='auto_brightness')
        self.autoBrightnessBox.onStateChanged.connect(self.checkBoxChanged)
        self.allowAppBox = MyCheckBox('Allowing app installing "unknown sources"', font_weight=QtGui.QFont.Light,
                                      font_size=12, identity='allow_app')
        self.allowAppBox.onStateChanged.connect(self.checkBoxChanged)
        self.noKeepActivityBox = MyCheckBox('Don\'t keep app activities', font_weight=QtGui.QFont.Light, font_size=12,
                                            identity='no_keep_activity')
        self.noKeepActivityBox.onStateChanged.connect(self.checkBoxChanged)
        self.vibrateBox = MyCheckBox('Vibrate when ringing', font_weight=QtGui.QFont.Light, font_size=12,
                                     identity='vibrate')
        self.vibrateBox.onStateChanged.connect(self.checkBoxChanged)
        self.keepWifiBox = MyCheckBox('keep WIFI on during sleep', font_weight=QtGui.QFont.Light, font_size=12,
                                      identity='keep_wifi')
        self.keepWifiBox.onStateChanged.connect(self.checkBoxChanged)

        brightTimeout = MyLabel('Brightness timeout', font_weight=QtGui.QFont.Light, font_size=12)
        sec = MyLabel('sec.', font_weight=QtGui.QFont.Light, font_size=12)
        self.timeoutEdit = MyLineEdit()
        self.timeoutEdit.setFixedSize(48, 16)
        self.timeoutEdit.setInputMask("000000")
        self.timeoutEdit.textChanged.connect(self.timeoutChanged)
        self.timeoutEdit.setEnabled(False)

        subHBox = QtGui.QHBoxLayout()
        subHBox.setContentsMargins(18, 0, 0, 0)
        subHBox.addWidget(brightTimeout)
        subHBox.addWidget(self.timeoutEdit)
        subHBox.addWidget(sec)
        self.subHWidget = QtGui.QWidget()
        self.subHWidget.setLayout(subHBox)
        self.subHWidget.setFixedSize(subHBox.sizeHint())

        self.checkBoxDict[AUTO_ROTATE] = self.autoRotateBox
        self.checkBoxDict[AUTO_BRIGHTNESS] = self.autoBrightnessBox
        self.checkBoxDict[BRIGHTNESS_SET] = self.timeoutEdit
        self.checkBoxDict[ALLOW_APP] = self.allowAppBox
        self.checkBoxDict[NO_KEEP_ACTIVITY] = self.noKeepActivityBox
        self.checkBoxDict[VIBRATE] = self.vibrateBox
        self.checkBoxDict[KEEP_WIFI] = self.keepWifiBox

        twoVbox = QtGui.QVBoxLayout()
        twoVbox.setContentsMargins(0, 0, 0, 0)
        twoVbox.addWidget(self.deviceGroup)
        twoVbox.addWidget(self.autoRotateBox)
        twoVbox.addWidget(self.autoBrightnessBox)
        twoVbox.addWidget(self.subHWidget)
        twoVbox.addWidget(self.allowAppBox)
        twoVbox.addWidget(self.noKeepActivityBox)
        twoVbox.addWidget(self.vibrateBox)
        twoVbox.addWidget(self.keepWifiBox)
        twoVbox.addStretch(1)
        twoVbox.setSpacing(12)
        self.middleWidget = QtGui.QWidget()
        self.middleWidget.setLayout(twoVbox)
        self.middleWidget.setFixedSize(twoVbox.sizeHint().width(), 398)

        self.windowAniBox = MyCheckBox('Window animation scale off', font_weight=QtGui.QFont.Light, font_size=12,
                                       identity='window_animator')
        self.windowAniBox.onStateChanged.connect(self.checkBoxChanged)
        self.transitionAniBox = MyCheckBox('Transition animation scale off', font_weight=QtGui.QFont.Light,
                                           font_size=12, identity='transition_animator')
        self.transitionAniBox.onStateChanged.connect(self.checkBoxChanged)
        self.durationAniBox = MyCheckBox('Animator duration off', font_weight=QtGui.QFont.Light, font_size=12,
                                         identity='duration_animation')
        self.durationAniBox.onStateChanged.connect(self.checkBoxChanged)

        self.checkBoxDict[WINDOW_ANIMATOR] = self.windowAniBox
        self.checkBoxDict[TRANSITION_ANIMATOR] = self.transitionAniBox
        self.checkBoxDict[DURATION_ANIMATION] = self.durationAniBox

        threeVbox = QtGui.QVBoxLayout()
        threeVbox.setContentsMargins(0, 0, 0, 0)
        threeVbox.addWidget(self.animationGroup)
        threeVbox.addWidget(self.windowAniBox)
        threeVbox.addWidget(self.transitionAniBox)
        threeVbox.addWidget(self.durationAniBox)
        threeVbox.addStretch(1)
        threeVbox.setSpacing(12)
        self.rightWidget = QtGui.QWidget()
        self.rightWidget.setLayout(threeVbox)
        self.rightWidget.setFixedSize(threeVbox.sizeHint().width(), 398)

        self.generalLayout = QtGui.QHBoxLayout()
        self.generalLayout.setContentsMargins(0, 0, 0, 0)
        self.generalLayout.addWidget(self.leftWidget, alignment=QtCore.Qt.AlignLeft)
        self.generalLayout.addWidget(self.middleWidget, alignment=QtCore.Qt.AlignHCenter)
        self.generalLayout.addWidget(self.rightWidget, alignment=QtCore.Qt.AlignRight)
        self.generalWidget = QtGui.QWidget()
        self.generalWidget.setLayout(self.generalLayout)
        self.generalWidget.setContentsMargins(40, 40, 24, 0)

        for checkBox in self.checkBoxDict.values():
            checkBox.setEnabled(False)

    def initialManagerPage(self):
        installBtn = IconButton()
        installBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_add app_normal.png'))
        installBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_add app_press.png'))
        installBtn.setIconSize(QtCore.QSize(20, 20))
        installBtn.clicked.connect(self.install)
        uninstallBtn = IconButton()
        uninstallBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_delete app_normal.png'))
        uninstallBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_delete app_press.png'))
        uninstallBtn.clicked.connect(self.uninstall)
        uninstallBtn.setIconSize(QtCore.QSize(20, 20))
        clearBtn = IconButton()
        clearBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_clear data _normal.png'))
        clearBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_clear data _normal.png'))
        clearBtn.clicked.connect(self.clear)
        clearBtn.setIconSize(QtCore.QSize(20, 20))

        apkWidget = HContainer()
        apkWidget.addWidget(uninstallBtn)
        apkWidget.addWidget(installBtn)
        apkWidget.addWidget(clearBtn)
        apkWidget.setAutoFitSize()

        self.allBtn = TitleButton('All', font_size=12, text_color='#464646')
        self.allBtn.clicked.connect(lambda result=AdbDevice.LIST_ALL: self.refreshPackageList(result))
        self.allBtn.setFixedHeight(40)
        self.systemBtn = TitleButton('System', font_size=12, text_color='#464646')
        self.systemBtn.clicked.connect(lambda result=AdbDevice.LIST_SYSTEM: self.refreshPackageList(result))
        self.systemBtn.setFixedHeight(40)
        self.trdPartyBtn = TitleButton('3rd Party', font_size=12, text_color='#464646')
        self.trdPartyBtn.clicked.connect(lambda result=AdbDevice.LIST_3RD_PARTY: self.refreshPackageList(result))
        self.trdPartyBtn.setFixedHeight(40)
        self.recentBtn = TitleButton('Recent', font_size=12, text_color='#464646')
        # recentBtn.clicked.connect(lambda t=AdbDevice.LIST_RECENT: self.device.requestInstallPackage(t))
        self.recentBtn.setFixedHeight(40)

        categoryLayout = QtGui.QHBoxLayout()
        categoryLayout.setContentsMargins(0, 0, 0, 0)
        categoryLayout.addWidget(self.allBtn)
        categoryLayout.addWidget(self.systemBtn)
        categoryLayout.addWidget(self.trdPartyBtn)
        categoryLayout.addWidget(self.recentBtn)
        categoryWidget = QtGui.QWidget()
        categoryWidget.setLayout(categoryLayout)
        categoryWidget.setFixedSize(categoryLayout.sizeHint())

        searchEdit = SearchBox()
        searchEdit.setFixedSize(157, 24)
        searchEdit.textChanged.connect(self.textChange)

        self.barLayout = QtGui.QHBoxLayout()
        self.barLayout.setContentsMargins(12, 0, 10, 0)
        self.barLayout.addWidget(apkWidget, alignment=QtCore.Qt.AlignLeft)
        self.barLayout.addWidget(categoryWidget, alignment=QtCore.Qt.AlignHCenter)
        self.barLayout.addWidget(searchEdit, alignment=QtCore.Qt.AlignRight)

        self.barWidget = QtGui.QWidget()
        self.barWidget.setLayout(self.barLayout)
        self.barWidget.setAutoFillBackground(True)
        self.barWidget.setFixedSize(896, 40)
        p = self.barWidget.palette()
        p.setColor(self.barWidget.backgroundRole(), QtGui.QColor(216, 216, 216))
        self.barWidget.setPalette(p)

        self.packageList = ListWidgetWithLine()
        self.packageList.setFixedSize(396, 330)

        self.packageLayout = QtGui.QHBoxLayout()
        self.packageLayout.addWidget(self.packageList, alignment=QtCore.Qt.AlignCenter)
        self.packageWidget = QtGui.QWidget()
        self.packageWidget.setLayout(self.packageLayout)
        self.packageWidget.setFixedSize(896, 359)

        self.managerLayout = QtGui.QVBoxLayout()
        self.managerLayout.setContentsMargins(0, 0, 0, 0)
        self.managerLayout.setSpacing(0)
        self.managerLayout.addWidget(self.barWidget)
        self.managerLayout.addWidget(self.packageWidget)

        self.managerWidget = QtGui.QWidget()
        self.managerWidget.setLayout(self.managerLayout)

    def upsideBar(self):
        self.generalBtn = SettingIconButton('General', font_size=14, color='#F8F8F8')
        self.generalBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.generalBtn.clicked.connect(lambda page=0: self.switchPage(page))
        self.generalBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_general_setting_normal.png'))
        self.generalBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_general_setting_press.png'))
        # self.generalBtn.
        self.generalBtn.setFixedHeight(96)
        self.apkManagerBtn = SettingIconButton('APK manager', font_size=14, color='#F8F8F8')
        self.apkManagerBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.apkManagerBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_apk_manager_normal.png'))
        self.apkManagerBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_apk_manager_press.png'))
        self.apkManagerBtn.clicked.connect(lambda page=1: self.switchPage(page))
        self.apkManagerBtn.setFixedHeight(96)

        upsideLayout = QtGui.QHBoxLayout()
        upsideLayout.setContentsMargins(0, 0, 0, 0)
        upsideLayout.addWidget(self.generalBtn)
        upsideLayout.addWidget(self.apkManagerBtn)
        upsideLayout.setSpacing(10)
        upsideLayout.addStretch(1)
        self.upsideWidget = QtGui.QWidget()
        self.upsideWidget.setLayout(upsideLayout)
        self.upsideWidget.setAutoFillBackground(True)
        self.upsideWidget.setFixedSize(896, 96)
        p = self.upsideWidget.palette()
        p.setColor(self.upsideWidget.backgroundRole(), QtGui.QColor(64, 64, 64))
        self.upsideWidget.setPalette(p)

    def dowsideContent(self):
        self.downsideWidget = QtGui.QStackedWidget()
        self.downsideWidget.setFixedSize(896, 398)
        self.downsideWidget.addWidget(self.generalWidget)
        self.downsideWidget.addWidget(self.managerWidget)

    def switchPage(self, page):
        if page == 0:
            self.downsideWidget.setCurrentIndex(0)
            self.isGetting = True
            self.deviceSettingThread.start()
            self.generalBtn.setEnabled(False)
            self.apkManagerBtn.setEnabled(True)
        else:
            self.downsideWidget.setCurrentIndex(1)
            self.packageThread.setType(AdbDevice.LIST_ALL)
            self.packageType = AdbDevice.LIST_ALL
            self.enablePackageButton()
            self.packageThread.start()
            self.generalBtn.setEnabled(True)
            self.apkManagerBtn.setEnabled(False)

    def checkBoxChanged(self, identity, state):
        if not self.isGetting:
            self.changeDict[identity] = state

    def timeoutChanged(self, text):
        if not self.isGetting:
            self.changeDict[BRIGHTNESS_SET] = text

    def onCurrentSettings(self, current, success):
        if success:
            for key, value in current.iteritems():
                if key != BRIGHTNESS_SET:
                    self.checkBoxDict.get(key).setEnabled(True)

                    if value:
                        self.checkBoxDict.get(key).setCheckState(QtCore.Qt.Checked)
                else:
                    self.timeoutEdit.setEnabled(True)
                    self.timeoutEdit.setText(str(value))
            self.isGetting = False
        else:
            self.w = NoConnectDevicePage()
            self.close()

    def saveClick(self):
        self.w = WaitDeviceSetting(self.changeDict, self.device)
        self.w.show()
        self.raise_()
        self.close()

    def noConnection(self):
        self.w = NoConnectDevicePage()
        self.close()

    def cancelClick(self):
        self.w = ChoseDevicePage()
        self.close()

    def refreshPackageList(self, t):
        self.packageType = t
        self.enablePackageButton()
        self.onReceivePackageList(self.device.requestPackage(t))

    def onReceivePackageList(self, packages):
        self.listPackage = packages
        self.fillList()

    def fillList(self):
        self.packageList.clear()
        for package in self.listPackage:
            name = package.replace('package:', '')
            if name.lower().find(self.filterText) != -1:
                self.packageList.addItem(name)

    def textChange(self, text):
        self.filterText = text.encode('utf-8')
        self.fillList()

    def install(self):
        fname, ok = QtGui.QFileDialog.getOpenFileName(self, 'install apk', folder.get_current_dir(__file__))
        if ok:
            _, extension = os.path.splitext(fname)
            if extension == '.apk':
                self.installPop = WaitDeviceInstalled(fname, self.device)
                self.installPop.installFinish.connect(self.installDone)

    def uninstall(self):
        item = self.packageList.currentItem()
        if item:
            self.device.uninstall(str(item.text()))
            self.refreshPackageList(self.packageType)

    def clear(self):
        item = self.packageList.currentItem()
        if item:
            self.device.resetPackage(str(item.text()))

    def installDone(self):
        self.refreshPackageList(self.packageType)

    def enablePackageButton(self):
        print self.packageType
        self.allBtn.setEnabled(True)
        self.systemBtn.setEnabled(True)
        self.trdPartyBtn.setEnabled(True)

        if self.packageType == AdbDevice.LIST_ALL:
            self.allBtn.setEnabled(False)
        elif self.packageType == AdbDevice.LIST_SYSTEM:
            self.systemBtn.setEnabled(False)
        elif self.packageType == AdbDevice.LIST_3RD_PARTY:
            self.trdPartyBtn.setEnabled(False)


class WaitDeviceSetting(IntroWindow):
    def __init__(self, settingDict, device):
        super(WaitDeviceSetting, self).__init__()
        self.device = device
        self.mThread = SendSettingThread(settingDict, self.device)
        self.mThread.done.connect(self.onDone)
        self.mThread.start()
        self.dontTouchPix = QtGui.QPixmap(ICON_FOLDER + '/ic_dont_youch_device.png')
        self.dontTouchPixLbl = QtGui.QLabel()
        self.dontTouchPixLbl.setPixmap(self.dontTouchPix)
        self.dontTouchPixLbl.setAlignment(QtCore.Qt.AlignCenter)

        self.dontTouchTitle = MyLabel('Don\'t touch your device,\n'
                                      'till setup complete.', font_size=20)
        self.dontTouchTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.dontTouchSubTitle = MyLabel('Please wait for a moment', font_size=12, font_weight=QtGui.QFont.Light)
        self.dontTouchSubTitle.setAlignment(QtCore.Qt.AlignCenter)

        self.loadingBar = MyProcessingBar()
        self.loadingBar.setFixedSize(640, 8)
        self.initUi()

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(self.dontTouchPixLbl)
        mainLayout.addWidget(self.dontTouchTitle)
        mainLayout.addWidget(self.dontTouchSubTitle)
        mainLayout.addSpacing(29)
        mainLayout.addWidget(self.loadingBar)
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)

        self.setCentralLayout(mainLayout)
        self.setCentralFixedSize(640, 334)
        self.setWindowTitle('Please Wait')
        self.setStyleSheet('color: #585858;')
        self.setFixedSize(self.sizeHint())

        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())
        self.loadingBar.setMovingColor('#1E90FF', '#82B1FF')
        self.loadingBar.start()

    def onDone(self):
        self.loadingBar.stop()
        self.close()
        self.w = ChoseDevicePage()
        self.w.show()
        self.w.raise_()


class WaitDeviceInstalled(IntroWindow):
    installFinish = QtCore.Signal()

    def __init__(self, f, device):
        super(WaitDeviceInstalled, self).__init__()
        self.device = device
        self.mThread = InstallThread(f, self.device)
        self.mThread.done.connect(self.onDone)
        self.mThread.start()
        self.installPix = QtGui.QPixmap(ICON_FOLDER + '/ic_installing_app.png')
        self.installPixLbl = QtGui.QLabel()
        self.installPixLbl.setPixmap(self.installPix)
        self.installPixLbl.setAlignment(QtCore.Qt.AlignCenter)

        self.installTitle = MyLabel('Installing App...', font_size=20)
        self.installTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.installSubTitle = MyLabel('Please wait for a moment', font_size=12, font_weight=QtGui.QFont.Light)
        self.installSubTitle.setAlignment(QtCore.Qt.AlignCenter)

        self.loadingBar = MyProcessingBar()
        self.loadingBar.setFixedSize(640, 8)
        self.initUi()

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(self.installPixLbl)
        mainLayout.addWidget(self.installTitle)
        mainLayout.addWidget(self.installSubTitle)
        mainLayout.addSpacing(29)
        mainLayout.addWidget(self.loadingBar)
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)

        self.setCentralLayout(mainLayout)
        self.setCentralFixedSize(640, 334)
        self.setWindowTitle('Please Wait')
        self.setStyleSheet('color: #585858;')
        self.setFixedSize(self.sizeHint())

        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())
        self.show()
        self.raise_()
        self.loadingBar.setMovingColor('#1E90FF', '#82B1FF')
        self.loadingBar.start()

    def onDone(self):
        self.loadingBar.stop()
        self.installFinish.emit()
        self.close()


class MainPage(QtGui.QWidget):
    pageList = list()
    _device = None
    updateScreen = None

    def __init__(self, serialNo):
        super(MainPage, self).__init__()
        set_background_color(self, '#181818')
        self._device = AdbDevice(serialNo)
        self.monitor = WaitForDevice(self._device)
        self.monitor.online.connect(self.deviceConnected)
        self.monitor.start()

        self.upsideBar()
        self.playPage = PlayListPage(self._device)
        self.playPage.notifyPages.connect(self.switchPages)
        self.downsideContent()
        self.createMenus()
        self.initUi()
        self.switchPages(PLAY_LIST_PAGE)

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(1)
        mainLayout.addWidget(self.categoryWidget)
        mainLayout.addWidget(self.downsideWidget)
        self.setWindowTitle('Autosense')
        self.setLayout(mainLayout)
        self.showMaximized()

    def deviceConnected(self):
        if self.currentPage() == 0:
            self.playPage.connected()
            self.updateScreen = UpdateScreen(self._device, PRIVATE_FOLDER)
            self.updateScreen.loadDone.connect(self.loadDone)
            self.updateScreen.deviceOffline.connect(self.deviceOffline)
            self.updateScreen.start()

    def upsideBar(self):
        # self.playListBtn = QtGui.QPushButton('PLAYLIST')
        self.playListBtn = MainTitleButton('PLAYLIST', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        self.processBtn = MainTitleButton('PROCESS', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        self.semiCheckBtn = MainTitleButton('SEMI-CHECK', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        self.reportBtn = MainTitleButton('REPORT', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        self.playListBtn.setFixedSize(self.processBtn.sizeHint().width(), 28)
        self.processBtn.setFixedSize(self.processBtn.sizeHint().width(), 28)
        self.semiCheckBtn.setFixedSize(self.semiCheckBtn.sizeHint().width(), 28)
        self.reportBtn.setFixedSize(self.reportBtn.sizeHint().width(), 28)
        self.playListBtn.pressed.connect(self.switchPlayListPage)
        self.processBtn.pressed.connect(self.switchProcessPage)
        self.semiCheckBtn.pressed.connect(self.switchSemiCheckPage)
        self.reportBtn.pressed.connect(self.switchReportPage)
        self.pageList.append(self.playListBtn)
        self.pageList.append(self.processBtn)
        self.pageList.append(self.semiCheckBtn)
        self.pageList.append(self.reportBtn)

        categoryLayout = QtGui.QHBoxLayout()
        categoryLayout.setContentsMargins(0, 0, 0, 0)
        categoryLayout.setSpacing(0)
        categoryLayout.addWidget(self.playListBtn)
        categoryLayout.addWidget(self.processBtn)
        categoryLayout.addWidget(self.semiCheckBtn)
        categoryLayout.addWidget(self.reportBtn)
        categoryLayout.addStretch(1)
        self.categoryWidget = QtGui.QWidget()
        self.categoryWidget.setLayout(categoryLayout)
        self.categoryWidget.setFixedHeight(categoryLayout.sizeHint().height())
        self.categoryWidget.setAutoFillBackground(True)
        p = self.categoryWidget.palette()
        p.setColor(self.categoryWidget.backgroundRole(), QtGui.QColor(40, 40, 40))
        self.categoryWidget.setPalette(p)

    def downsideContent(self):
        self.downsideWidget = QtGui.QStackedWidget()
        self.downsideWidget.addWidget(self.playPage)

    def createMenus(self):
        '''
        Add menu bar
        1. Script
        2. Run
        3. Device
        4. Tool
        '''
        # Script, Run,  Device
        self.menuBar = QtGui.QMenuBar(self)
        fileMenu = self.menuBar.addMenu('Script')
        deviceMenu = self.menuBar.addMenu('Device')
        toolMenu = self.menuBar.addMenu('Tool')

        self.openAction = fileMenu.addAction('Import\tCtrl+o')
        self.saveAction = fileMenu.addAction('Export\tCtrl+s')
        self.deleteAction = fileMenu.addAction('Delete\tCtrl+d')
        self.selectAction = fileMenu.addAction('Select all\tCtrl+a')
        self.deselectAction = fileMenu.addAction('Deselect all\tCtrl+Shift+a')
        self.clearAction = fileMenu.addAction('Clear')

        self.deviceInfoAtion = deviceMenu.addAction('Device info\tCtrl+i')
        self.turnOffAnimation = deviceMenu.addAction('Disable animations')
        self.installAction = deviceMenu.addAction('Install apk')
        self.uninstallAction = deviceMenu.addAction('uninstall apk')

        self.scriptConvertAction = toolMenu.addAction('Script conversion')


    def switchPlayListPage(self):
        self.enablePage(PLAY_LIST_PAGE)
        if self.updateScreen:
            self.updateScreen.start()
        self.playPage.switch_mode(PLAY_LIST_PAGE)

    def switchProcessPage(self):
        self.updateScreen.stop()
        self.enablePage(PROCESS_PAGE)
        self.playPage.switch_mode(PROCESS_PAGE)

    def switchSemiCheckPage(self):
        self.updateScreen.stop()
        self.enablePage(SEMI_CHECK_PAGE)
        self.playPage.switch_mode(SEMI_CHECK_PAGE)

    def switchReportPage(self):
        self.updateScreen.stop()
        self.enablePage(REPORT_PAGE)
        self.playPage.switch_mode(REPORT_PAGE)

    def switchPages(self, num):
        if num == PLAY_LIST_PAGE:
            self.switchPlayListPage()
        elif num == PROCESS_PAGE:
            self.switchProcessPage()
        elif num == SEMI_CHECK_PAGE:
            self.switchSemiCheckPage()
        elif num == REPORT_PAGE:
            self.switchReportPage()

    def currentPage(self):
        return self.downsideWidget.currentIndex()

    def enablePage(self, number):
        for btn in self.pageList:
            btn.setEnabled(True)
        self.pageList[number].setEnabled(False)

    def calculateTextLength(self, text, size):
        font = QtGui.QFont('Open Sans', size)
        fm = QtGui.QFontMetrics(font)
        return fm.width(text)

    @QtCore.Slot()
    def loadDone(self):
        if self.updateScreen.isRunning():
            self.playPage.notifySetScreenContent()

    @QtCore.Slot()
    def deviceOffline(self):
        self.monitor.start()
        if self.currentPage() == 0:
            self.playPage.disconnected()

    def stopThread(self, t):
        if t and t.isRunning():
            t.stop()
            while not t.isFinished():
                time.sleep(0.05)
            print str(t) + ' is finished.'

    def closeEvent(self, event):
        print 'Window is closed.....'
        self.stopThread(self.updateScreen)
        self.stopThread(self.monitor)
        if self._device and self._device.isConnected():
            self._device.close()


class PlayListPage(VContainer):
    ratio = 1
    mode = 0
    _device = None
    timestamp = None
    selectedPlanItem = None
    selectedActionItem = None
    currentPlanName = None
    currentPlayName = None
    buttonList = list()
    planDict = dict()
    playQueueDict = dict()
    runQueueList = list()
    resultPool = list()
    notifyPages = QtCore.Signal(int)
    isRunning = False
    RIGHT_VIRTUAL_PAGE = 0
    RIGHT_PROCESSING_PAGE = 2
    RIGHT_DISCONNECT_PAGE = 1
    RIGHT_SEMICHECK_PAGE = 3
    RIGHT_REPORT_PAGE = 4

    currentPage = 0

    def __init__(self, device):
        super(PlayListPage, self).__init__()
        self._device = device
        self.picPath = PRIVATE_FOLDER + '/' + str(self._device.serialno) + '_screen.png'
        self.init_action_bar()
        self.init_left_frame()
        self.init_right_frame()
        self.combine_frames()
        self.enable_buttons(False)
        self.setSpacing(1)
        self.addWidget(self.actionBar)
        self.addWidget(self.combineWidget)

        self.rsThread = RunScript(device=self._device)
        self.rsThread.currentAction.connect(self.onCurrentAction)
        self.rsThread.actionDone.connect(self.onActionDone)
        self.rsThread.finish.connect(self.run_done)

    def init_action_bar(self):
        backBtn = IconButton()
        homeBtn = IconButton()
        menuBtn = IconButton()
        powerBtn = IconButton()
        volumeUp = IconButton()
        volumeDown = IconButton()
        rotateLeftBtn = IconButton()
        rotateRightBtn = IconButton()
        unlockBtn = IconButton()
        typeTextBtn = IconButton()
        hideKeyboardBtn = IconButton()

        backBtn.setFixedSize(40, 40)
        homeBtn.setFixedSize(40, 40)
        menuBtn.setFixedSize(40, 40)
        powerBtn.setFixedSize(40, 40)
        volumeUp.setFixedSize(40, 40)
        volumeDown.setFixedSize(40, 40)
        rotateLeftBtn.setFixedSize(40, 40)
        rotateRightBtn.setFixedSize(40, 40)
        unlockBtn.setFixedSize(40, 40)
        typeTextBtn.setFixedSize(40, 40)
        hideKeyboardBtn.setFixedSize(40, 40)

        backBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_back_normal.png'))
        homeBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_home_normal.png'))
        menuBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_menu_normal.png'))
        powerBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_power_normal.png'))
        volumeUp.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_zoomin_normal.png'))
        volumeDown.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_zoonout_normal.png'))
        rotateLeftBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_rotate_left_normal.png'))
        rotateRightBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_rotate_right_normal.png'))
        unlockBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_unlock_normal.png'))
        typeTextBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_typetext_normal.png'))
        hideKeyboardBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_hide_keyboard_normal.png'))

        backBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_back_press.png'))
        homeBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_home_press.png'))
        menuBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_menu_press.png'))
        powerBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_power_press.png'))
        volumeUp.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_zoomin_press.png'))
        volumeDown.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_zoonout_press.png'))
        rotateLeftBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_rotate_left_press.png'))
        rotateRightBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_rotate_right_press.png'))
        unlockBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_unlock_press.png'))
        typeTextBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_typetext_press.png'))
        hideKeyboardBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_hide_keyboard_press.png'))

        backBtn.clicked.connect(self.pressBack)
        homeBtn.clicked.connect(self.pressHome)
        menuBtn.clicked.connect(self.pressMenu)
        powerBtn.clicked.connect(self.pressPower)
        volumeUp.clicked.connect(self.volumeUp)
        volumeDown.clicked.connect(self.volumeDown)
        rotateLeftBtn.clicked.connect(self.rotateLeft)
        rotateRightBtn.clicked.connect(self.rotateRight)
        unlockBtn.clicked.connect(self.unlockScreen)
        typeTextBtn.clicked.connect(self.addTypeText)
        hideKeyboardBtn.clicked.connect(self.hideKeyboard)

        self.buttonList.append(backBtn)
        self.buttonList.append(homeBtn)
        self.buttonList.append(menuBtn)
        self.buttonList.append(powerBtn)
        self.buttonList.append(volumeUp)
        self.buttonList.append(volumeDown)
        self.buttonList.append(rotateLeftBtn)
        self.buttonList.append(rotateRightBtn)
        self.buttonList.append(unlockBtn)
        self.buttonList.append(typeTextBtn)
        self.buttonList.append(hideKeyboardBtn)

        actionsWidget = HContainer()
        actionsWidget.setSpacing(1)
        for btn in self.buttonList:
            actionsWidget.addWidget(btn)
        actionsWidget.setAutoFixedFitWidth()
        set_background_color(actionsWidget, '#282828')

        checkUiBtn = MenuButton('Check', font_size=12, font_weight=QtGui.QFont.Light, text_color='#D1D1D1')
        checkUiBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        checkUiBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_check_normal.png'))
        checkUiBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_check_press.png'))
        checkUiBtn.setMenuIndicator(ICON_FOLDER + '/ic_drop_normal.png',
                                    ICON_FOLDER + '/ic_drop_press.png')
        checkUiBtn.setFixedSize(120, 40)
        checkMenu = QtGui.QMenu()
        checkMenu.setStyleSheet('QMenu{background-color: #282828; color: #A0A0A0}'
                                'QMenu::item:selected {background-color: #383838;}')
        checkMenu.addAction('UI exist', lambda check_type=IS_EXIST: self.notify_Check_UI(check_type))
        checkMenu.addAction('UI not exist', lambda check_type=NO_EXIST: self.notify_Check_UI(check_type))
        checkMenu.addAction('UI is blank', lambda check_type=IS_BLANK: self.notify_Check_UI(check_type))
        checkMenu.addAction('UI relative is exist', lambda check_type=IS_RELATIVE_EXIST: self.notify_Check_UI(check_type))
        checkMenu.addAction('Check point', self.addCheckPoint)
        checkUiBtn.setMenu(checkMenu)

        checkUiWidget = HContainer()
        checkUiWidget.addWidget(checkUiBtn)
        checkUiWidget.setAutoFitSize()
        set_background_color(checkUiWidget, '#282828')

        mediaCheckBtn = IconWithWordsButton('Media Check', font_size=12, font_weight=QtGui.QFont.Light,
                                            text_color='#D1D1D1')
        mediaCheckBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        mediaCheckBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_mediacheck_normal.png'))
        mediaCheckBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_mediacheck_press.png'))
        mediaCheckBtn.clicked.connect(self.pressMediaCheck)
        mediaCheckBtn.setFixedHeight(40)

        mediaCheckWidget = HContainer()
        mediaCheckWidget.addWidget(mediaCheckBtn)
        mediaCheckWidget.setAutoFitSize()
        set_background_color(mediaCheckWidget, '#282828')

        delayBtn = IconWithWordsButton('Delay', font_size=12, font_weight=QtGui.QFont.Light, text_color='#D1D1D1')
        delayBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        delayBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_delay_normal.png'))
        delayBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_delay_press.png'))
        delayBtn.clicked.connect(self.pressDelay)
        delayBtn.setFixedSize(120, 40)

        self.buttonList.append(checkUiBtn)
        self.buttonList.append(mediaCheckBtn)
        self.buttonList.append(delayBtn)

        delayWidget = HContainer()
        delayWidget.addWidget(delayBtn)
        delayWidget.setAutoFitSize()
        set_background_color(delayWidget, '#282828')

        blankWidget = QtGui.QWidget()
        set_background_color(blankWidget, '#282828')

        self.actionMenuBar = HContainer()
        self.actionMenuBar.setSpacing(1)
        self.actionMenuBar.addWidget(actionsWidget)
        self.actionMenuBar.addWidget(checkUiWidget)
        self.actionMenuBar.addWidget(mediaCheckWidget)
        self.actionMenuBar.addWidget(delayWidget)
        self.actionMenuBar.addWidget(blankWidget)
        self.actionMenuBar.setAutoFitHeight()

        # back button and next button
        previousBtn = MenuButton('Back', font_size=12, text_color='#A0A0A0')
        previousBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        previousBtn.setIgnoreMouse(True)
        previousBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_previous normal.png'))
        previousBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_previous not active.png'))
        previousBtn.setFixedSize(120, 40)
        previousBtn.clicked.connect(self.abort_process)

        cancelBtn = MyButton('CANCEL', font_size=10, font_color='#A0A0A0')
        cancelBtn.setFixedSize(80, 24)
        saveBtn = MyButton('SAVE', font_size=10, font_color='#A0A0A0')
        saveBtn.setFixedSize(80, 24)

        self.saveSemiField = HContainer()
        self.saveSemiField.setSpacing(10)
        self.saveSemiField.addWidget(cancelBtn)
        self.saveSemiField.addWidget(saveBtn)

        jumpBar = HContainer()
        jumpBar.addWidget(previousBtn)
        jumpBar.addStretch(1)
        jumpBar.addWidget(self.saveSemiField)
        set_background_color(jumpBar, '#282828')

        self.actionBar = QtGui.QStackedWidget()
        self.actionBar.addWidget(self.actionMenuBar)
        self.actionBar.addWidget(jumpBar)
        self.actionBar.setFixedHeight(40)

    def init_left_frame(self):
        # Test plan title filed
        testPlanBtn = MainTitleButton('Test plan', text_color='#FFFFFF', rect_color='#282828')
        playQueueBtn = MainTitleButton('Play queue', text_color='#FFFFFF', rect_color='#282828')

        testPlanBtn.pressed.connect(lambda page=0: self.switch_left_frame(page))
        playQueueBtn.pressed.connect(lambda page=1: self.switch_left_frame(page))
        self.titleList = [testPlanBtn, playQueueBtn]

        testPlanTitleWidget = HContainer()
        testPlanTitleWidget.addWidget(testPlanBtn)
        testPlanTitleWidget.addWidget(playQueueBtn)
        testPlanTitleWidget.setFixedHeight(30)

        # test plan page
        self.addPlanBtn = PushButton('Add new testplan', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        self.addPlanBtn.setFixedHeight(30)
        self.addPlanBtn.clicked.connect(self.add_test_plan_btn)
        appPlanWidget = HContainer()
        appPlanWidget.addWidget(self.addPlanBtn)
        appPlanWidget.setAutoFitHeight()

        self.testPlanListView = TestPlanListView('#6C9EFF')
        self.testPlanListView.currentItemChanged.connect(self.testPlanSelected)
        self.testPlanListView.itemDelete.connect(self.testPlanItemDeleted)

        testPlanWidget = VContainer()
        testPlanWidget.addWidget(appPlanWidget)
        testPlanWidget.addWidget(self.testPlanListView)
        testPlanWidget.setFixedWidth(200)

        #  play queue page
        self.addQueueBtn = PushButton('Add play queue', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        self.addQueueBtn.setFixedHeight(30)
        self.addQueueBtn.clicked.connect(self.addPlanQueueBtn)
        appQueueWidget = HContainer()
        appQueueWidget.addWidget(self.addQueueBtn)
        appQueueWidget.setAutoFitHeight()

        self.startBtn = PushButton(text='PLAY', font_size=14, text_color='#A0A0A0', rect_color='#282828')
        self.startBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_play normal.png'))
        self.startBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_play press.png'))
        self.startBtn.clicked.connect(self.ready_script)
        self.startBtn.setFixedHeight(40)

        self.stopBtn = PushButton(text='STOP', font_size=14, text_color='#A0A0A0', rect_color='#282828')
        self.stopBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_stop normal.png'))
        self.stopBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_stop press.png'))
        self.stopBtn.clicked.connect(self.stopRun)
        self.stopBtn.setFixedHeight(40)

        self.switchBtns = QtGui.QStackedWidget()
        self.switchBtns.addWidget(self.startBtn)
        self.switchBtns.addWidget(self.stopBtn)

        self.playQueueListView = PlayQueueListView('#6C9EFF')
        self.playQueueListView.currentItemChanged.connect(self.playQueueSelected)
        self.playQueueListView.itemDelete.connect(self.playQueueItemDeleted)

        queueWidget = VContainer()
        queueWidget.addWidget(testPlanTitleWidget)
        queueWidget.addWidget(appQueueWidget)
        queueWidget.addWidget(self.playQueueListView)
        queueWidget.addStretch(1)
        queueWidget.addWidget(self.switchBtns)
        queueWidget.setFixedWidth(200)

        self.sideStack = QtGui.QStackedWidget()
        self.sideStack.addWidget(testPlanWidget)
        self.sideStack.addWidget(queueWidget)

        self.sideView = VContainer()
        self.sideView.setSpacing(1)
        self.sideView.addWidget(testPlanTitleWidget)
        self.sideView.addWidget(self.sideStack)
        self.sideView.setFixedWidth(200)

        set_background_color(self.sideView, '#282828')

        # Test plan detail filed
        self.planNameLabel = MyLabel('', font_size=12, color='#ffffff')
        self.planNameLabel.setFixedHeight(30)
        self.createTime = MyLabel('', font_size=12, color='#A0A0A0')
        self.createTime.setFixedHeight(30)

        testPlanDetailWidget = BottomLineWidget()
        testPlanDetailWidget.addWidget(self.planNameLabel)
        testPlanDetailWidget.addStretch(1)
        testPlanDetailWidget.addWidget(self.createTime)
        testPlanDetailWidget.setContentsMargins(8, 0, 8, 0)
        testPlanDetailWidget.setAutoFitHeight()

        numMark = MyLabel('#', font_size=12, color='#A0A0A0')
        actionMark = MyLabel('Action', font_size=12, color='#A0A0A0')
        numMark.setFixedHeight(30)
        actionMark.setFixedHeight(30)

        actionTitle = HContainer()
        actionTitle.addWidget(numMark)
        actionTitle.addWidget(actionMark)
        actionTitle.addStretch(1)
        actionTitle.setSpacing(23)
        actionTitle.setMargins(30, 0, 0, 0)
        actionTitle.setBottomLine('#333333')
        actionTitle.setAutoFitHeight()

        self.actionListView = ActionListView(active_color='#282828')
        self.actionListView.currentItemChanged.connect(self.actionSelected)
        self.actionListView.takeItemsDone.connect(self.actionItemDeleted)

        self.descriptionEdit = MyPlainTextEdit(font_size=12, font_color='#FFFFFF')
        self.descriptionEdit.setFixedHeight(160)
        self.descriptionEdit.setEnabled(False)
        self.descriptionEdit.focusOut.connect(self.editDone)

        self.testActionWidget = VContainer()
        self.testActionWidget.setContentsMargins(8, 0, 8, 0)
        self.testActionWidget.addWidget(testPlanDetailWidget)
        self.testActionWidget.addWidget(actionTitle)
        self.testActionWidget.addWidget(self.actionListView)
        self.testActionWidget.addWidget(self.descriptionEdit)
        self.testActionWidget.setFixedWidth(396)

        self.findTestPlan()

    def init_right_frame(self):

        # Virtual screen page
        self.virtualScreen = PictureLabel(self, currentPath=self.picPath)
        self.virtualScreen.setAlignment(QtCore.Qt.AlignCenter)
        self.virtualScreen.mouseClick.connect(self.getClick)
        self.virtualScreen.mouseLongClick.connect(self.getLongClick)
        self.virtualScreen.mouseSwipe.connect(self.getSwipe)
        self.virtualScreen.mouseDrag.connect(self.getDrag)
        self.virtualScreen.checkClick.connect(self.addCheck)
        self.virtualScreen.checkRelativeClick.connect(self.checkRelativeClick)
        self.virtualScreen.checkRelativeDone.connect(self.checkRelativeDone)

        self.virtualFrame = HContainer()
        self.virtualFrame.addWidget(self.virtualScreen, alignment=QtCore.Qt.AlignCenter)

        self.virtualWidget = HContainer()
        self.virtualWidget.addWidget(self.virtualFrame)
        self.virtualWidget.resizeHappened.connect(self.virtualScreenResize)

        # disconnect page
        self.noConnectPix = QtGui.QPixmap(ICON_FOLDER + '/ic_no_connect_blue.png')
        self.noConnectPixLbl = QtGui.QLabel()
        self.noConnectPixLbl.setPixmap(self.noConnectPix)

        self.noConnectTitle = MyLabel('No device connected', font_size=20, color='#FFFFFF')
        self.noConnectTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.noConnectSubTitle = MyLabel('Woops,\n'
                                         'We found you doesn\'t connect any device.\n'
                                         'Please connect a device'
                                         , font_size=12, font_weight=QtGui.QFont.Light, color='#A0A0A0')
        self.noConnectSubTitle.setAlignment(QtCore.Qt.AlignCenter)

        disconnectView = VContainer()
        disconnectView.addWidget(self.noConnectPixLbl)
        disconnectView.addWidget(self.noConnectTitle)
        disconnectView.addWidget(self.noConnectSubTitle)
        disconnectView.setAlignment(QtCore.Qt.AlignCenter)

        # process page
        processLabel = QtGui.QLabel()
        self.processGif = QtGui.QMovie(ICON_FOLDER + '/gif_processing.gif')
        processLabel.setFixedHeight(128)

        processLabel.setMovie(self.processGif)
        processLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.processPlan = MyLabel('', color='#A0A0A0', font_size=12)
        self.processPlan.setFixedWidth(360)
        self.progressBar = MyProgressBar()
        self.progressBar.setFixedSize(360, 8)

        self.percentage = MyLabel('', color='#FFFFFF', font_size=12)

        processContainer = VContainer()
        processContainer.addWidget(processLabel, alignment=QtCore.Qt.AlignHCenter)
        processContainer.addWidget(self.processPlan)
        processContainer.addWidget(self.progressBar)
        processContainer.addWidget(self.percentage)
        processContainer.setAutoFitSize()
        processContainer.setSpacing(8)

        processView = HContainer()
        processView.addWidget(processContainer)

        # semi-check page
        checkPointTitle = MyLabel('Checkpoint : ', font_size=14, color='#FFFFFF')
        self.checkPointDescription = MyLabel('Checkpoint:', font_size=14, color='#FFFFFF')
        checkCombo = HContainer()
        checkCombo.addWidget(checkPointTitle)
        checkCombo.addWidget(self.checkPointDescription)

        passBtn = IconButton()
        passBtn.setIconSize(QtCore.QSize(64, 24))
        passBtn.setIgnoreMouse(True)
        passBtn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        passBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/btn_pass_normal.png'))
        passBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/btn_pass_press.png'))
        passBtn.clicked.connect(lambda: self.semi_result_clicked(autoSense.PASS))
        failBtn = IconButton()
        failBtn.setIconSize(QtCore.QSize(64, 24))
        failBtn.setIgnoreMouse(True)
        failBtn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        failBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/btn_fail_normal.png'))
        failBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/btn_fail_press.png'))
        failBtn.clicked.connect(lambda: self.semi_result_clicked(autoSense.FAIL))
        judgeField = HContainer()
        judgeField.addWidget(passBtn)
        judgeField.addWidget(failBtn)
        judgeField.setAutoFitSize()

        topField = HContainer()
        topField.setFixedHeight(40)
        topField.addWidget(checkCombo)
        topField.addStretch(1)
        topField.addWidget(judgeField)

        logView = MyPlainTextEdit(font_size=12, font_color='#FFFFFF')
        logView.setPlainText('This function is similar to registerListener(SensorEventListener, '
                             'Sensor, int) but it allows events to stay temporarily in the hardware FIFO (queue) '
                             'before being delivered. The events can be stored in the hardware FIFO up to'
                             ' maxReportLatencyUs microseconds. Once one of the events in the FIFO needs to be '
                             'reported, all of the events in the FIFO are reported sequentially. This means that '
                             'some events will be reported before the maximum reporting latency has elapsed.')
        logView.setFixedSize(662, 262)

        beforeActionLabel = MyLabel('BEFORE action screenshot', font_size=12, color='#A4A4A4')
        beforeActionLabel.setFixedHeight(40)
        beforeActionLabel.setContentsMargins(10, 0, 0, 0)
        set_background_color(beforeActionLabel, '#282828')
        afterActionLabel = MyLabel('AFTER action screenshot', font_size=12, color='#A4A4A4')
        afterActionLabel.setFixedHeight(40)
        afterActionLabel.setContentsMargins(10, 0, 0, 0)
        set_background_color(afterActionLabel, '#282828')

        self.beforePixLabel = QtGui.QLabel()
        self.beforePixLabel.setAlignment(QtCore.Qt.AlignCenter)
        set_background_color(self.beforePixLabel, '#282828')
        self.afterPixLabel = QtGui.QLabel()
        self.afterPixLabel.setAlignment(QtCore.Qt.AlignCenter)
        set_background_color(self.afterPixLabel, '#282828')

        self.leftScreenShotField = VContainer()
        self.leftScreenShotField.setSpacing(1)
        self.leftScreenShotField.addWidget(beforeActionLabel)
        self.leftScreenShotField.addWidget(self.beforePixLabel)

        self.rightScreenShotField = VContainer()
        self.rightScreenShotField.setSpacing(1)
        self.rightScreenShotField.addWidget(afterActionLabel)
        self.rightScreenShotField.addWidget(self.afterPixLabel)

        screenShotField = HContainer()
        screenShotField.setSpacing(8)
        screenShotField.setContentsMargins(0, 10, 0, 0)
        screenShotField.addWidget(self.leftScreenShotField)
        screenShotField.addWidget(self.rightScreenShotField)

        semiCheckView = VContainer()
        semiCheckView.setContentsMargins(10, 10, 10, 10)
        semiCheckView.addWidget(topField)
        semiCheckView.addWidget(logView)
        semiCheckView.addWidget(screenShotField)

        # report page
        totalField = VContainer()
        totalLabel = MyLabel('Total Action', font_size=12, color='#A0A0A0')
        totalLabel.setAlignment(QtCore.Qt.AlignCenter)
        totalLabel.setBoader('#404040')
        self.totalCountLabel = MyLabel('50%', font_size=12, color='#A0A0A0')
        self.totalCountLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.totalCountLabel.setBoader('#404040')
        totalField.addWidget(totalLabel)
        totalField.addWidget(self.totalCountLabel)

        passField = VContainer()
        passLabel = MyLabel('Passed', font_size=12, color='#A0A0A0')
        passLabel.setAlignment(QtCore.Qt.AlignCenter)
        passLabel.setBoader('#404040')
        self.passCountLabel = MyLabel('50%', font_size=12, color='#A0A0A0')
        self.passCountLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.passCountLabel.setBoader('#404040')
        passField.addWidget(passLabel)
        passField.addWidget(self.passCountLabel)

        failField = VContainer()
        failLabel = MyLabel('Failed', font_size=12, color='#A0A0A0')
        failLabel.setAlignment(QtCore.Qt.AlignCenter)
        failLabel.setBoader('#404040')
        self.failCountLabel = MyLabel('50%', font_size=12, color='#A0A0A0')
        self.failCountLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.failCountLabel.setBoader('#404040')
        failField.addWidget(failLabel)
        failField.addWidget(self.failCountLabel)

        passRatioField = VContainer()
        passRatioLabel = MyLabel('Pass Ratio', font_size=12, color='#A0A0A0')
        passRatioLabel.setAlignment(QtCore.Qt.AlignCenter)
        passRatioLabel.setBoader('#404040')
        self.passRatioValueLabel = MyLabel('50%', font_size=12, color='#A0A0A0')
        self.passRatioValueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.passRatioValueLabel.setBoader('#404040')
        passRatioField.addWidget(passRatioLabel)
        passRatioField.addWidget(self.passRatioValueLabel)

        failRatioField = VContainer()
        failRatioLabel = MyLabel('Fail Ratio', font_size=12, color='#A0A0A0')
        failRatioLabel.setAlignment(QtCore.Qt.AlignCenter)
        failRatioLabel.setBoader('#404040')
        self.failRatioValueLabel = MyLabel('50%', font_size=12, color='#A0A0A0')
        self.failRatioValueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.failRatioValueLabel.setBoader('#404040')
        failRatioField.addWidget(failRatioLabel)
        failRatioField.addWidget(self.failRatioValueLabel)

        semiRatioField = VContainer()
        semiRatioLabel = MyLabel('Semi Ratio', font_size=12, color='#A0A0A0')
        semiRatioLabel.setAlignment(QtCore.Qt.AlignCenter)
        semiRatioLabel.setBoader('#404040')
        self.semiRatioValueLabel = MyLabel('50%', font_size=12, color='#A0A0A0')
        self.semiRatioValueLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.semiRatioValueLabel.setBoader('#404040')
        semiRatioField.addWidget(semiRatioLabel)
        semiRatioField.addWidget(self.semiRatioValueLabel)

        emptyField = VContainer()
        emptyLabel = MyLabel('')
        emptyLabel.setBoader('#404040')
        emptyValueLabel = MyLabel('')
        emptyValueLabel.setBoader('#404040')
        emptyField.addWidget(emptyLabel)
        emptyField.addWidget(emptyValueLabel)

        formView = HContainer()
        formView.addWidget(totalField)
        formView.addWidget(passField)
        formView.addWidget(failField)
        formView.addWidget(passRatioField)
        formView.addWidget(failRatioField)
        formView.addWidget(semiRatioField)
        formView.addWidget(emptyField)
        formView.setFixedHeight(60)

        drawerView = VContainer()
        self.pass_fail_pie = DonutPie(radius=100, thickness=20, color='#7ED321', second_color='#DA4456')
        self.pass_fail_pie.setMinimumHeight(290)
        self.semi_total_pie = DonutPie(radius=100, thickness=20, color='#F5A623', second_color='#4A4A4A')
        self.semi_total_pie.setMinimumHeight(290)

        drawerView.addWidget(self.pass_fail_pie)
        drawerView.addWidget(self.semi_total_pie)

        reportView = VContainer()
        reportView.setContentsMargins(10, 10, 10, 10)
        reportView.addWidget(formView)
        reportView.addWidget(drawerView)
        reportView.addStretch(1)

        self.aboutDeviceWidget = QtGui.QStackedWidget()
        self.aboutDeviceWidget.addWidget(self.virtualWidget)
        self.aboutDeviceWidget.addWidget(disconnectView)
        self.aboutDeviceWidget.addWidget(processView)
        self.aboutDeviceWidget.addWidget(semiCheckView)
        self.aboutDeviceWidget.addWidget(reportView)

    def combine_frames(self):
        line = QtGui.QFrame()
        line.setFrameShape(QtGui.QFrame.VLine)
        line.setStyleSheet('color: #404040;')

        self.combineWidget = HContainer()
        self.combineWidget.addWidget(self.sideView)
        self.combineWidget.addWidget(self.testActionWidget)
        self.combineWidget.addWidget(line)
        self.combineWidget.addWidget(self.aboutDeviceWidget)

    def switch_mode(self, mode):
        """
        This switches pages include: PLAY_LIST_PAGE, PROCESS_PAGE, SEMI_CHECK_PAGE, REPORT_PAGE
        :param mode: page number
        :return: None
        """
        if mode == PLAY_LIST_PAGE:
            self.currentPage = PLAY_LIST_PAGE
            self.switch_left_frame(0)
            self.switch_right_frame(self.RIGHT_VIRTUAL_PAGE)
            self.switch_action_bar(0)
            self.off_list_right_click(False)

        elif mode == PROCESS_PAGE:
            self.currentPage = PROCESS_PAGE
            self.switch_right_frame(self.RIGHT_PROCESSING_PAGE)
            self.switch_action_bar(1)
            self.off_list_right_click(True)

        elif mode == SEMI_CHECK_PAGE:
            self.currentPage = SEMI_CHECK_PAGE
            self.switch_left_frame(1)
            self.switch_right_frame(self.RIGHT_SEMICHECK_PAGE)
            self.switch_action_bar(1)
            self.off_list_right_click(True)
            self.select_check_point_action()

        elif mode == REPORT_PAGE:
            self.currentPage = REPORT_PAGE
            self.switch_left_frame(1)
            self.switch_action_bar(1)
            self.off_list_right_click(True)
            self.switch_right_frame(self.RIGHT_REPORT_PAGE)

    def switch_left_frame(self, number):
        """
        This switches Testplan and Playqueue
        :param number: page number
        :return: None
        """
        self.actionListView.clear()
        self.planNameLabel.setText('')
        self.createTime.setText('')
        if number == 0:
            self.titleList[0].setEnabled(False)
            self.titleList[1].setEnabled(True)
            self.sideStack.setCurrentIndex(0)
            self.testPlanListView.setCurrentRow(-1)
            if self.testPlanListView.count() != 0:
                self.testPlanListView.setCurrentRow(0)
        else:
            self.titleList[0].setEnabled(True)
            self.titleList[1].setEnabled(False)
            self.sideStack.setCurrentIndex(1)
            self.playQueueListView.setCurrentRow(-1)
            if self.playQueueListView.count() != 0:
                self.playQueueListView.setCurrentRow(0)

    def switch_right_frame(self, number):
        self.aboutDeviceWidget.setCurrentIndex(number)
        if number == self.RIGHT_VIRTUAL_PAGE:
            self.enable_buttons(True)
        elif number == self.RIGHT_DISCONNECT_PAGE:
            self.enable_buttons(False)

    def switch_action_bar(self, number):
        self.actionBar.setCurrentIndex(number)
        if number == 1:
            self.saveSemiField.setVisible(False)
        else:
            self.saveSemiField.setVisible(True)

    def switch_buttons(self, number):
        self.switchBtns.setCurrentIndex(number)

    def off_list_right_click(self, needOff):
        if needOff:
            self.testPlanListView.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
            self.playQueueListView.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
            self.actionListView.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        else:
            self.testPlanListView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.playQueueListView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.actionListView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def semi_result_clicked(self, result):
        item = self.actionListView.itemWidgetByRow(self.actionListView.currentRow())
        print item.action()
        if item and item.action() == "CheckPoint":
            item.setTested(result)
            self.refreshPlayActionView()
            if not self.select_check_point_action():
                self.notifyPages.emit(REPORT_PAGE)

    def abort_process(self):
        result = QtGui.QMessageBox.warning(self, 'Warning', 'Do you want to abort? \n(It will lose testing result.)'
                                           , QtGui.QMessageBox.Abort, QtGui.QMessageBox.Cancel)
        if result == QtGui.QMessageBox.Abort:
            self.notifyPages.emit(PLAY_LIST_PAGE)

    def testPlanItemDeleted(self, row, item, widget):
        del self.planDict[widget.planName()]
        path = SCRIPT_FOLDER + '/' + widget.text() + '.csv'
        if os.path.exists(path):
            os.remove(path)

    def playQueueItemDeleted(self, row, item, widget):
        pass

    def actionItemDeleted(self, deleteItems):
        for deletedItem in deleteItems:
            actionList = self.planDict.get(self.getCurrentPlanName()).actions()
            actionList.pop(deletedItem.get('row'))
        self.refreshActionList()
        self.refreshPlanActionView(refreshRow=deleteItems[0].get('row'))

    def enable_buttons(self, state):
        self.virtualScreen.setEnabled(state)
        for btn in self.buttonList:
            btn.setEnabled(state)

    def add_test_plan_btn(self):
        name, description, ok = CreateNewPage.getTestPlan()
        if ok:
            if not self.testPlanListView.haveItem(name):
                self.insert_plan_item(name, time.strftime("%Y/%m/%d %T", time.localtime()))

    def insert_plan_item(self, text, create_time=None):
        fullName = SCRIPT_FOLDER + '/' + text + '.csv'
        if not os.path.exists(fullName):
            self.saveScript(text, create_time)

        actions, timestamp = self.loadScript(text)
        planItem = TestPlanItem()
        planItem.setPlanName(text)
        planItem.setActions(actions)
        if timestamp:
            planItem.setCreateTime(timestamp)
        else:
            planItem.setCreateTime(create_time)

        planItem.setIndex(self.testPlanListView.count())
        self.planDict[text] = planItem
        self.testPlanListView.addCustomItem(self.testPlanListView.count(), TestPlanListItem(planItem))

    def findTestPlan(self):
        for f in glob.glob(SCRIPT_FOLDER + "/*.csv"):
            baseName = os.path.basename(f)
            self.insert_plan_item(baseName[0:baseName.find('.csv')])

    def addPlanQueueBtn(self):
        name, start, end, repeat, ok = QueueAddPage.getInformation(self.planDict)
        if ok:
            playActions = copy.deepcopy(self.planDict.get(name).actions()[int(start) - 1:int(end)])
            playItem = PlayItem()
            playItem.setPlayName(name)
            playItem.setRange((int(start), int(end)))
            playItem.setRepeat(int(repeat))
            playItem.setActions(playActions)
            queueListItem = PlayQueueListItem(playItem)
            self.playQueueDict[queueListItem.text()] = playItem
            self.playQueueListView.addCustomItem(self.playQueueListView.count(), queueListItem)

    def editDone(self):
        if self.getSelectedActionItem():
            actionItem = self.planDict.get(self.getCurrentPlanName()).actions()[
                self.actionListView.row(self.getSelectedActionItem())]
            actionItem.setAnnotation(self.descriptionEdit.toPlainText())
            self.saveScript(self.getCurrentPlanName())

    def setSelectedActionItem(self, item):
        self.selectedActionItem = item

    def getSelectedActionItem(self):
        return self.selectedActionItem

    def disconnected(self):
        self.switch_right_frame(self.RIGHT_DISCONNECT_PAGE)

    def connected(self):
        self.switch_right_frame(self.RIGHT_VIRTUAL_PAGE)

    def testPlanSelected(self, item):
        if item:
            self.enable_buttons(True)
            self.selectedPlanItem = item
            self.selectedActionItem = None
            self.createTime.setText(self.testPlanListView.itemWidget(item).createTime())
            self.setCurrentPlanName(self.testPlanListView.itemWidget(item).planName())
            self.refreshPlanActionView()
            self.planNameLabel.setText(self.getCurrentPlanName())
            self.descriptionEdit.clear()

    def playQueueSelected(self, item):
        print "playQueueSelected"
        if item:
            self.selectedPlanItem = item
            self.selectedActionItem = None
            self.enable_buttons(True)
            itemWidget = self.playQueueListView.itemWidget(item)
            self.setCurrentPlayName(itemWidget.text())
            self.planNameLabel.setText('%s' % (itemWidget.text()))
            self.refreshPlayActionView()

            if self.currentPage == REPORT_PAGE:
                item = TestResultItem(self.playQueueListView.itemWidgetByRow(self.playQueueListView.currentRow()).actions())
                self.setReportAnalysis(item)

    def setReportAnalysis(self, resultItem):
        self.totalCountLabel.setText(str(resultItem.total_count()))
        self.passCountLabel.setText(str(resultItem.pass_count()))
        self.failCountLabel.setText(str(resultItem.fail_count()))
        self.passRatioValueLabel.setText(str(resultItem.pass_ratio())+'%')
        self.failRatioValueLabel.setText(str(resultItem.fail_ratio())+'%')
        self.semiRatioValueLabel.setText(str(resultItem.semi_ratio())+'%')

        self.pass_fail_pie.setStartAngle(0)
        self.pass_fail_pie.setSpanAngle(360 * resultItem.pass_ratio() / 100)
        self.semi_total_pie.setStartAngle(0)
        self.semi_total_pie.setSpanAngle(360 * resultItem.semi_ratio() / 100)

        self.pass_fail_pie.update()
        self.semi_total_pie.update()



    def actionSelected(self, item):
        if item:
            if self.sideStack.currentIndex() == 0:
                widgetItem = self.planDict.get(self.getCurrentPlanName()).actions()[self.actionListView.row(item)]
            else:
                widgetItem = self.playQueueDict.get(self.getCurrentPlayName()).actions()[self.actionListView.row(item)]
            self.selectedActionItem = item
            self.descriptionEdit.setEnabled(True)
            self.descriptionEdit.setPlainText(widgetItem.annotation())

            if self.currentPage == 2:  # show screenshot if it is in semi-check page
                postPixmap = QtGui.QPixmap(
                    IMAGE_FOLDER + '/%s_%d.png' % (self.currentPlayName, int(widgetItem.index()) - 1))
                if not postPixmap.isNull():
                    postPixmap = postPixmap.scaled(postPixmap.size().width() * 328 / postPixmap.size().width(),
                                                   postPixmap.size().height() * 328 / postPixmap.size().height(),
                                                   aspectMode=QtCore.Qt.KeepAspectRatio)

                afterPixmap = QtGui.QPixmap(
                    IMAGE_FOLDER + '/%s_%d.png' % (self.currentPlayName, int(widgetItem.index())))
                if not afterPixmap.isNull():
                    afterPixmap = afterPixmap.scaled(afterPixmap.size().width() * 328 / afterPixmap.size().width(),
                                                     afterPixmap.size().height() * 328 / afterPixmap.size().height(),
                                                     aspectMode=QtCore.Qt.KeepAspectRatio)

                self.beforePixLabel.setPixmap(postPixmap)
                self.afterPixLabel.setPixmap(afterPixmap)

                if widgetItem.action() == 'CheckPoint':
                    self.checkPointDescription.setText(widgetItem.parameter()[0])
                    self.rightScreenShotField.setVisible(False)
                else:
                    self.rightScreenShotField.setVisible(True)

    def select_check_point_action(self):
        for ranWidget in self.resultPool:
            for action in ranWidget.actions():
                if action.tested() == autoSense.SEMI:
                    self.playQueueListView.setCurrentItem(self.playQueueListView.itemByItemWidget(ranWidget))
                    self.actionListView.setCurrentRow(ranWidget.actions().index(action))
                    return True

    def notify_Check_UI(self, check_type):
        """
        It draw gird on virtual screen for user to check UI component.
        :param check_type:
        :return: None
        """
        self.virtualScreen.drawGrid(self._device.dump(), check_type)
        self.virtualScreen.setMouseIgnore(True)

    def ready_script(self):
        del self.runQueueList[:]
        del self.resultPool[:]
        for num in range(self.playQueueListView.count()):
            item = self.playQueueListView.item(num)
            queueWidget = self.playQueueListView.itemWidget(item)
            if queueWidget.isChecked():
                self.runQueueList.append(queueWidget)

        if len(self.runQueueList) > 0:
            self.processGif.start()
            self.isRunning = True
            self.switch_buttons(1)
            self.playQueueListView.setEnabled(False)
            self.notifyPages.emit(1)
            self.runQueueList.reverse()
            self.run_script(self.runQueueList[-1])

    def run_script(self, queueWidget):
        # self.setCurrentPlanName(queueWidget.playName())

        self.playQueueListView.setCurrentItem(self.playQueueListView.itemByItemWidget(queueWidget))
        viewRange = queueWidget.range()
        self.refreshPlayActionView()
        self.progressBar.setMaximum(queueWidget.actionsCount())
        self.progressBar.setValue(0)
        self.processPlan.setText('%s (%d to %d)' % (queueWidget.playName(),
                                                    viewRange[0],
                                                    viewRange[1]))
        self.rsThread.setActions(queueWidget.actions())
        self.rsThread.setPlayName(self.getCurrentPlayName())
        self.rsThread.setTimes(queueWidget.repeat())
        self.rsThread.setStartIndex(0)
        self.rsThread.start()

    def stopRun(self):
        if self.rsThread.isRunning():
            self.rsThread.stop()
        self.switch_buttons(0)

    def notifySetScreenContent(self):
        """
        Show device screen
        :return:
        """
        try:
            pic = QtGui.QPixmap(self.picPath)
            if not pic.isNull():
                self.ratio = self.calculate_scale(self._device.getCurrDisplay(), self.virtualWidget.size())
                pic = pic.scaled(pic.size().width() * self.ratio,
                                 pic.size().height() * self.ratio,
                                 aspectMode=QtCore.Qt.KeepAspectRatio)
                if not self.virtualScreen.pixmap():
                    self.virtualScreen.setPixmap(pic)
                # self.scrollArea.setFixedSize(pic.size().width() + 2, pic.size().height() + 2)
                long_side = max([pic.size().width(), pic.size().height()])
                self.virtualFrame.setMaximumSize(long_side, long_side)
                self.virtualScreen.setMaximumSize(pic.size().width(), pic.size().height())
                self.virtualScreen.setPicScale(self.ratio)
                self.virtualScreen.update()
        except IndexError as e:
            print 'IndexError: ' + e.message
        except OSError as e:
            print 'OSError: ' + e.message

    def calculate_scale(self, displayInfo, size):
        width = displayInfo['width']
        height = displayInfo['height']
        short_side = min(size.width(), size.height())
        if width > height:
            ratio = short_side * 0.9 / width  # virtual screen margins 1/8 width of screen container
        elif width < height:
            ratio = short_side * 0.9 / height
        return ratio

    def add_list_item(self, action, param='', info=''):
        insertRow = self.actionListView.getInsertRow()
        item = AutoSenseItem()
        item.setIndex(self.actionListView.count() + 1)
        item.setAction(action)
        item.setParameter(param)
        item.setInformation(info)
        self.planDict.get(self.getCurrentPlanName()).actions().insert(insertRow, item)
        self.refreshActionList()
        self.refreshPlanActionView()

    def refreshActionList(self):
        actionList = self.planDict.get(self.getCurrentPlanName()).actions()
        for i in range(len(actionList)):
            actionList[i].setIndex(i + 1)
        self.saveScript(self.getCurrentPlanName())

    def refreshPlanActionView(self, refreshRow=-1, scrollToIndex=None):
        '''
        Refresh the action list view and save the changes.
        It also control the signal light changes to represent the states of running
        script.
        :param refreshRow:
        '''
        self.descriptionEdit.clear()
        if refreshRow == -1:
            self.actionListView.clear()
            self.descriptionEdit.setEnabled(False)
            actionList = self.planDict.get(self.getCurrentPlanName()).actions()

            for i in range(len(actionList)):
                actionListItem = ActionListItem(actionList[i], i + 1)
                self.actionListView.addCustomItem(i, actionListItem)

            if scrollToIndex:
                self.scrollListViewTo(scrollToIndex, isSelect=False)
        else:
            actionList = self.planDict.get(self.getCurrentPlanName()).actions()
            for num in range(refreshRow, len(actionList)):
                self.actionListView.itemWidgetByRow(num).setIndex(num + 1)

    def refreshPlayActionView(self, scrollToIndex=None):
        self.descriptionEdit.clear()
        self.actionListView.clear()
        self.descriptionEdit.setEnabled(False)
        actionList = self.playQueueDict.get(self.getCurrentPlayName()).actions()
        for i in range(len(actionList)):
            actionListItem = ActionListItem(actionList[i], i + 1)
            self.actionListView.addCustomItem(i, actionListItem)
            if self.currentPage == 0 or self.sideStack.currentIndex() == 0:
                actionListItem.setSignal(QtGui.QIcon(''))
            elif self.isRunning:
                actionListItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_normal.png'))
            else:
                if actionListItem.tested() == autoSense.NORMAL:
                    actionListItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_normal.png'))
                elif actionListItem.tested() == autoSense.PASS:
                    actionListItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_passed.png'))
                elif actionListItem.tested() == autoSense.FAIL:
                    actionListItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_failed.png'))
                elif actionListItem.tested() == autoSense.SEMI:
                    actionListItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_semichecked.png'))

        if scrollToIndex:
            self.scrollListViewTo(scrollToIndex, isSelect=False)

    def scrollListViewTo(self, index, selected=True, hint=QtGui.QAbstractItemView.PositionAtCenter):
        self.actionListView.scrollToItem(self.actionListView.item(index), hint=hint)
        if selected:
            self.actionListView.setCurrentRow(index, QtGui.QItemSelectionModel.ClearAndSelect)

    @QtCore.Slot()
    def virtualScreenResize(self, event):
        # self.ratio = self.calculateScale(self._device.getCurrDisplay(), event.size())
        self.notifySetScreenContent()

    @QtCore.Slot()
    def getClick(self, point):
        print 'get Click'
        x = int(point.x() / self.ratio)
        y = int(point.y() / self.ratio)
        pressPoint = (x, y)
        info = self._device.getTouchViewInfo(pressPoint)

        s = json.dumps(info)
        param = list(pressPoint)
        self.add_list_item('Click', param=param, info=s)

        workExecutor(self._device.click, pressPoint)

    @QtCore.Slot()
    def getLongClick(self, point, duration):
        print 'getLongClick'
        x = int(point.x() / self.ratio)
        y = int(point.y() / self.ratio)
        pressPoint = (x, y)
        info = self._device.getTouchViewInfo(pressPoint)
        s = json.dumps(info)
        param = [x, y, duration]
        self.add_list_item('LongClick', param=param, info=s)
        workExecutor(self._device.longClick, (x, y, duration))

    @QtCore.Slot()
    def getDrag(self, start, end, speed):
        print 'getDrag'
        startPoint = start.toTuple()
        endPoint = end.toTuple()
        self.dragFrom = [int(startPoint[0] / self.ratio), int(startPoint[1] / self.ratio)]
        self.dragTo = [int(endPoint[0] / self.ratio), int(endPoint[1] / self.ratio)]
        self.speed = speed
        info = self._device.getTouchViewInfo(self.dragFrom)
        s = json.dumps(info)
        param = self.dragFrom + self.dragTo
        param.append(speed)
        self.add_list_item('Drag', param, s)
        workExecutor(self._device.drag, (self.dragFrom, self.dragTo, speed))

    @QtCore.Slot()
    def getSwipe(self, start, end, speed):
        print 'getSwipe'
        startPoint = start.toTuple()
        endPoint = end.toTuple()
        self.dragFrom = [int(startPoint[0] / self.ratio), int(startPoint[1] / self.ratio)]
        self.dragTo = [int(endPoint[0] / self.ratio), int(endPoint[1] / self.ratio)]
        self.speed = speed
        info = self._device.getTouchViewInfo(self.dragFrom)
        s = json.dumps(info)
        param = self.dragFrom + self.dragTo
        param.append(speed)
        self.add_list_item('Swipe', param, s)
        workExecutor(self._device.swipe, (self.dragFrom, self.dragTo, speed))

    @QtCore.Slot()
    def addCheck(self, point, check_type):
        print 'addCheck'
        x = int(point.x() / self.ratio)
        y = int(point.y() / self.ratio)
        press_point = (x, y)
        info = self._device.getTouchViewInfo(press_point)

        param = list()
        param.append(self.getCheckReference(info))
        center_point = self._device.getBoundsCenter(info['bounds'])
        param.append(center_point[0])
        param.append(center_point[1])
        self.add_list_item(check_type, param)

        self.virtualScreen.doneDrawGrid()
        self.virtualScreen.setMouseIgnore(False)

    def getCheckReference(self, info):
        if info['text'] != '':
            return 'text=%s' % info['text']
        elif info['content-desc'] != '':
            return 'description=%s' % info['content-desc']
        elif info['resource-id'] != '':
            return 'resourceId=%s' % info['resource-id']
        else:
            return 'className=%s' % info['class']

    def addCheckPoint(self):
        inputText, ok = QtGui.QInputDialog.getText(self, 'Input Dialog',
                                                   'Input text:', QtGui.QLineEdit.Normal)
        if ok:
            self.add_list_item('CheckPoint', inputText)

    @QtCore.Slot()
    def checkRelativeClick(self, point):
        info = self._device.getTouchViewInfo((point.x() / self.ratio, point.y() / self.ratio))
        self.virtualScreen.drawRelativeGrid(info.get('bounds'))

    @QtCore.Slot()
    def checkRelativeDone(self, pivot, point):
        print 'checkRelativeDone'
        x1 = int(pivot.x() / self.ratio)
        y1 = int(pivot.y() / self.ratio)
        x2 = int(point.x() / self.ratio)
        y2 = int(point.y() / self.ratio)
        firstPoint = (x1, y1)
        secondPoint = (x2, y2)
        info1 = self._device.getTouchViewInfo(firstPoint)
        info2 = self._device.getTouchViewInfo(secondPoint)

        param = list()
        param.append(self.getCheckReference(info1))
        param.append(self.getCheckReference(info2))
        param.append(x1)
        param.append(y1)
        param.append(x2)
        param.append(y2)
        self.add_list_item('RelativeCheck', param)
        self.virtualScreen.doneDrawGrid()
        self.virtualScreen.setMouseIgnore(False)

    @QtCore.Slot()
    def addTypeText(self):
        print 'addType'
        inputText, ok = QtGui.QInputDialog.getText(self, 'Input Dialog',
                                                   'Input text:', QtGui.QLineEdit.Normal)
        text = inputText.encode('utf-8').decode('ascii', 'ignore').encode('utf-8')

        if ok and text != '':
            self.add_list_item('Type', text)
            workExecutor(self._device.type, text)

    @QtCore.Slot(AutoSenseItem)
    def onCurrentAction(self, item):
        index = int(item.index()) - 1
        self.actionListView.setCurrentRow(index)

    @QtCore.Slot(AutoSenseItem, int, int)
    def onActionDone(self, item, result, index):
        currentItem = self.actionListView.item(index)
        currentWidgetItem = self.actionListView.itemWidget(currentItem)

        if result == autoSense.PASS:
            currentWidgetItem.setTested(autoSense.PASS)
            currentWidgetItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_passed.png'))
        elif result == autoSense.FAIL:
            currentWidgetItem.setTested(autoSense.FAIL)
            currentWidgetItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_failed.png'))
        elif result == autoSense.SEMI:
            currentWidgetItem.setTested(autoSense.SEMI)
            currentWidgetItem.setSignal(QtGui.QIcon(ICON_FOLDER + '/ic_semichecked.png'))

        self.progressBar.setValue(self.progressBar.value() + 1)
        calculate = self.progressBar.value() / self.progressBar.maximum()
        self.percentage.setText(str((int(calculate * 100))) + '%')
        self.rsThread.setPlayName(self.getCurrentPlayName())

    @QtCore.Slot()
    def run_done(self):
        if len(self.runQueueList) > 1:
            self.resultPool.append(self.runQueueList.pop())
            self.playQueueListView.setCurrentItem(self.playQueueListView.itemByItemWidget(self.runQueueList[-1]))
            self.run_script(self.runQueueList[-1])
        else:
            self.resultPool.append(self.runQueueList.pop())
            self.switch_buttons(0)
            self.actionListView.setCurrentRow(-1)
            self.isRunning = False
            self.processGif.stop()
            self.playQueueListView.setEnabled(True)
            self.notifyPages.emit(SEMI_CHECK_PAGE)

    def pressMediaCheck(self):
        testTime, timeout, isChecked, ok = MediaCheckDialog.getCheckTime()
        if ok and len(testTime) != 0 and len(timeout) != 0:
            if isChecked:
                self.add_list_item('MediaCheck', param=[testTime, timeout, 'True'])
            else:
                self.add_list_item('MediaCheck', param=[testTime, timeout, 'False'])

    def pressDelay(self):
        inputDelay, ok = DelayDialog.getDelay()
        if ok and len(inputDelay) != 0:
            self.add_list_item('Delay', param=inputDelay)

    def pressBack(self):
        workExecutor(self._device.backBtn)
        self.add_list_item('Back')

    def pressPower(self):
        workExecutor(self._device.powerBtn)
        self.add_list_item('Power')

    def pressHome(self):
        workExecutor(self._device.homeBtn)
        self.add_list_item('Home')

    def pressMenu(self):
        workExecutor(self._device.menuBtn)
        self.add_list_item('Menu')

    def unlockScreen(self):
        workExecutor(self._device.unlock)
        self.add_list_item('Unlock')

    def volumeUp(self):
        self._device.volumeUp()

    def volumeDown(self):
        self._device.volumeDown()

    def rotateLeft(self):
        workExecutor(self._device.rotate, ('left',))
        self.add_list_item('Rotate', param='left')

    def rotateRight(self):
        workExecutor(self._device.rotate, ('right',))
        self.add_list_item('Rotate', param='right')

    def hideKeyboard(self):
        workExecutor(self._device.hideKeyboard)
        self.add_list_item('HideKeyboard')

    def saveScript(self, fileName, timeStamp=None):
        fullName = SCRIPT_FOLDER + '/' + fileName + '.csv'
        if os.path.exists(fullName):
            currentPlan = self.planDict.get(fileName)
            with open(fullName, 'wb') as csvfile:
                fieldnames = [INDEX, ACTION, PARAMETER, INFORMATION, DESCRIPTION]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in currentPlan.actions():
                    writer.writerow(item.inDict())
                real = self._device.getRealDisplay()
                resolution = [real['width'], real['height']]
                writer.writerow({INDEX: '-1', ACTION: 'resolution', PARAMETER: str(resolution)})
                writer.writerow({INDEX: '-2', ACTION: 'create', PARAMETER: currentPlan.createTime()})
        else:
            with open(fullName, 'wb') as csvfile:
                fieldnames = [INDEX, ACTION, PARAMETER, INFORMATION, DESCRIPTION]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                real = self._device.getRealDisplay()
                resolution = [real['width'], real['height']]
                writer.writerow({INDEX: '-1', ACTION: 'resolution', PARAMETER: str(resolution)})
                writer.writerow({INDEX: '-2', ACTION: 'create', PARAMETER: timeStamp})

    def setCurrentPlanName(self, name):
        self.currentPlanName = name

    def getCurrentPlanName(self):
        return self.currentPlanName

    def setCurrentPlayName(self, name):
        self.currentPlayName = name

    def getCurrentPlayName(self):
        return self.currentPlayName

    def loadScript(self, fileName):
        screenMode = self._device.getCurrDisplay()['mode']
        actions = list()
        timestamp = None
        with open(SCRIPT_FOLDER + '/' + fileName + '.csv', 'rt') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if int(row[INDEX]) > 0:
                    if row[ACTION] == 'click':
                        param = row[PARAMETER].strip('[\[\]]').split(',')
                        if len(param) < 3:
                            param.append(screenMode[0].upper())
                            row[PARAMETER] = param
                    elif row[ACTION] == 'drag':
                        param = row[PARAMETER].strip('[\[\]]').split(',')
                        if len(param) < 6:
                            param.append(screenMode[0].upper())
                            row[PARAMETER] = param
                    item = AutoSenseItem(row)
                    actions.append(item)
                elif row[ACTION] == 'create':
                    timestamp = row[PARAMETER]

        return actions, timestamp


def add_font_family(app):
    for f in os.listdir(FONT_FOLDER):
        if f[-4:len(f)] == '.ttf':
            mid = QtGui.QFontDatabase.addApplicationFont(FONT_FOLDER + '/' + f)

    print QtGui.QFontDatabase.applicationFontFamilies(mid)[0]
    app.setFont(QtGui.QFont('Open Sans'))


def main():
    if not os.path.exists(ROOT_FOLDER):
        os.mkdir(ROOT_FOLDER)
    if not os.path.exists(LOG_FOLDER):
        os.mkdir(LOG_FOLDER)
    if not os.path.exists(SCRIPT_FOLDER):
        os.mkdir(SCRIPT_FOLDER)
    if not os.path.exists(PRIVATE_FOLDER):
        os.mkdir(PRIVATE_FOLDER)
    if not os.path.exists(IMAGE_FOLDER):
        os.mkdir(IMAGE_FOLDER)

    app = QtGui.QApplication(sys.argv)
    add_font_family(app)
    # wid = MainPage('emulator-5554')
    wid = MainPage('DT08A00003871140504')
    # wid = LandingPage()
    wid.raise_()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
