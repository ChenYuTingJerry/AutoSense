# -*- coding: utf-8 -*-
'''
Created on 2015年10月7日

@author: jerrychen
'''
import threading
import os
import re
import time
import uiautomator
import json
import socket
import binascii
from minicap import MiniServer, MiniReader
from Adb import AdbDevice
from subprocess import CalledProcessError
from PySide import QtCore, QtGui
from autoSense import AutoSenseItem
from constants import Setting, Global, JudgeState as State


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


class RunTest(QtCore.QThread):
    """
    Handle the reproduced actions and send back to device
    """
    actionResult = State.FAIL
    isStopRun = False
    finish = QtCore.Signal()
    currentAction = QtCore.Signal(AutoSenseItem)
    actionDone = QtCore.Signal(AutoSenseItem, bool, int)

    def __init__(self, times=1, device=None):
        super(RunTest, self).__init__()
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
                self.actionResult = State.PASS

    def actionRelativeCheck(self, param, refer=None):
        pass

    def actionCheckPoint(self, param, refer=None):
        self.actionResult = State.SEMI

    def actionType(self, param, refer=None):
        """
        Action of typing text.
        :param param: a string
        :param refer: None
        """
        self._device.type(param[0])
        self.actionResult = State.PASS

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
        self.actionResult = State.PASS

    def actionUnlock(self, param, refer=None):
        """
        Unlock screen. If screen is not locked, it will do nothing.
        :param param: None
        :param refer: None
        """
        self._device.unlock()
        self.actionResult = State.PASS

    def actionMenu(self, param, refer=None):
        """
        Simulate menu button is pressed.
        :param param: None
        :param refer: None
        """
        self._device.cmd.inputKeyevnt('MENU')
        self.actionResult = State.PASS

    def actionPower(self, param, refer=None):
        """
        Simulate power button is pressed.
        :param param: None
        :param refer: None
        """
        self._device.cmd.inputKeyevnt('POWER')
        self.actionResult = State.PASS

    def actionHome(self, param, refer=None):
        """
        Simulate home button is pressed.
        :param param: None
        :param refer: None
        """
        self._device.cmd.inputKeyevnt('HOME')
        self.actionResult = State.PASS

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
        self.actionResult = State.PASS

    def actionDrag(self, param, refer=None):
        """
        Simulate drag action. It can drag a view object if it can be dragged.
        :param param: [x1, y1, x2, y2, duration]
        :param refer: None
        """
        start = (param[0], param[1])
        end = (param[2], param[3])
        self._device.drag(start, end, int(param[4]))
        self.actionResult = State.PASS

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
        self.actionResult = State.PASS

    def actionBack(self, param, refer=None):
        """
        Simulate back button.
        :param param: None
        :param refer: None
        """
        self._device.backBtn()
        self.actionResult = State.PASS

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
                    self.actionResult = State.PASS
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
                    self.actionResult = State.PASS
            else:
                self.actionResult = State.PASS

        elif attribute == 'description':
            selector = self._device.retrieveSelector(point, self._device.d(description=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = State.PASS
            else:
                self.actionResult = State.PASS

        elif attribute == 'resourceId':
            selector = self._device.retrieveSelector(point, self._device.d(resourceId=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = State.PASS
            else:
                self.actionResult = State.PASS

        elif attribute == 'className':
            selector = self._device.retrieveSelector(point, self._device.d(className=value))
            if selector:
                if selector.childCount == 0:
                    self.actionResult = State.PASS
            else:
                self.actionResult = State.PASS

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
            self._device.takeSnapshot(Global.IMAGE_FOLDER + '/%s_%d.png' % (self.playName, 0))
            while self.limit < self.times and not self.isStopRun:
                self.limit += 1
                for index in range(len(self.actions)):
                    if not self.isStopRun and self.startIndex <= index:
                        self.index = index + 1
                        item = self.actions[index]
                        if self._device.isConnected():
                            self.actionResult = State.FAIL
                            self.currentAction.emit(item)
                            self.actionSwitcher.get(item.action())(item.parameter(), item.information())
                            self._device.takeSnapshot(Global.IMAGE_FOLDER + '/%s_%d.png' % (self.playName, self.index))
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
        self.miniServer = MiniServer(self._device)
        self.miniReader = MiniReader(self._device)

    def stop(self):
        """ Stop capturing """
        self.isStop = True
        self.miniServer.stop()

    def pause(self):
        """ Pause capturing """
        self.isPause = True
        self.miniServer.stop()

    def resume(self):
        """ resume capturing """
        self.isPause = False
        self.start()

    def setDelay(self, delay=0):
        """ Set a delay time to start capturing """
        self.delay = delay

    def run(self):
        time.sleep(self.delay)
        # try:
        self.miniServer.start()
        self.isStop = False
        while not self.isStop:
            if not self.isPause and self.miniServer.isActive():
                if not self.miniServer.needRestart():
                    self.startLoad.emit()
                    self.screenshot(path=self.picPath + '/' + self._device.serialno + '_screen.jpg')
                else:
                    self.miniServer.reStart()
                # self.isPause = True
        # except:
        #     print 'device not found'
        #     self.lastFrameTime = 0
        #     self.deviceOffline.emit()

    # def run(self):
    #     self.screenSync()
    #     print 'done'

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
                if self.miniServer.isActive():
                    byteData = self.miniReader.getDisplay()
                    im = QtGui.QImage.fromData(QtCore.QByteArray.fromRawData(byteData))
                    im.loadFromData(byteData)
                    im.save(path, 'JPEG')
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


    def __byteToHex(self, bs):
        return ''.join(['%02X ' % ord(byte) for byte in bs])

    def __parsePicSize(self, data):
        return int(binascii.hexlify(data[::-1]), 16)

    def __parseBanner(self, data):
        if len(data) == 24:
            banner = dict()
            banner['version'] = int(binascii.hexlify(data[0]), 16)
            banner['length'] = int(binascii.hexlify(data[1]), 16)
            banner['pid'] = int(binascii.hexlify(data[2:5][::-1]), 16)
            banner['real.width'] = int(binascii.hexlify(data[6:9][::-1]), 16)
            banner['real.height'] = int(binascii.hexlify(data[10:13][::-1]), 16)
            banner['virtual.width'] = int(binascii.hexlify(data[14:17][::-1]), 16)
            banner['virtual.height'] = int(binascii.hexlify(data[18:21][::-1]), 16)
            banner['orient'] = int(binascii.hexlify(data[22]), 16)
            banner['policy'] = int(binascii.hexlify(data[23]), 16)
            return banner


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
            xx[Setting.NFC] = self.device.isNfcOn()
            xx[Setting.WIFI] = self.device.isWifiOn()
            xx[Setting.AIRPLANE] = self.device.isAirPlaneModeOn()
            xx[Setting.GPS] = self.device.isGpsOn()
            xx[Setting.AUTO_ROTATE] = self.device.isAutoRotateOn()
            xx[Setting.BLUETOOTH] = self.device.isBtOn()
            xx[Setting.DATA_ROAMING] = self.device.isDataRoamingOn()
            xx[Setting.ALLOW_APP] = self.device.isInstallUnknownSources()
            xx[Setting.NO_KEEP_ACTIVITY] = self.device.isNoKeepActivityOn()
            xx[Setting.AUTO_BRIGHTNESS] = self.device.isAutoBrightnessOn()
            xx[Setting.BRIGHTNESS_SET] = self.device.screenTimeout()
            xx[Setting.VIBRATE] = self.device.isVibrateWhenRingOn()
            xx[Setting.WINDOW_ANIMATOR] = self.device.isWindowAniOn()
            xx[Setting.TRANSITION_ANIMATOR] = self.device.isTransitionAnuOn()
            xx[Setting.DURATION_ANIMATION] = self.device.isDurationAniOn()
            self.currentSettings.emit(xx, True)
        except CalledProcessError:
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
            if key == Setting.AIRPLANE:
                self.device.enableAirplaneMode(value)
            elif key == Setting.NFC:
                self.device.enableNfc(value)
            elif key == Setting.ALLOW_APP:
                self.device.enableInstallUnknownSources(value)
            elif key == Setting.WIFI:
                self.device.enableWifi(value)
            elif key == Setting.BLUETOOTH:
                self.device.enableBluetooth(value)
            elif key == Setting.NO_KEEP_ACTIVITY:
                self.device.enableNoKeepActivity(value)
            elif key == Setting.DATA_ROAMING:
                self.device.enableDataRoaming(value)
            elif key == Setting.AUTO_ROTATE:
                self.device.enableAutoRotate(value)
            elif key == Setting.GPS:
                self.device.enableGps(value)
            elif key == Setting.AUTO_BRIGHTNESS:
                self.device.enableAutoBrightness(value)
            elif key == Setting.VIBRATE:
                self.device.enableVibrateWhenRing(value)
            elif key == Setting.BRIGHTNESS_SET:
                self.device.setScreenTimeout(str(long(value) * 1000))
            elif key == Setting.WINDOW_ANIMATOR:
                if self.device.isWindowAniOn() != value:
                    self.device.enableWindowAnimator(not value)
                    needReboot = True
            elif key == Setting.TRANSITION_ANIMATOR:
                if self.device.isTransitionAnuOn() != value:
                    self.device.enableTransitionAnimator(not value)
                    needReboot = True
            elif key == Setting.DURATION_ANIMATION:
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




