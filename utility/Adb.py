# -*- coding: utf-8 -*-
'''
Created on 2015年6月18日

@author: jerrychen
'''
from subprocess import check_output, call
import time
import re
import os
import sys
import xml.etree.ElementTree as ET
import threading
from uiautomator import Device


class AdbCmd(object):
    '''
    classdocs
    '''
    __gencmd = ['adb', 'shell']
    __pullcmd = ['adb', 'pull']
    __pushcmd = ['adb', 'push']
    __rebootcmd = ['adb', 'reboot']
    __installcmd = ['adb', 'install', '-r']
    __uninstallcmd = ['adb', 'uninstall']
    __devicecmd = ['adb', 'devices']
    __inputcmd = __gencmd + ['input', 'keyevent']
    __dumpsyscmd = __gencmd + ['dumpsys']
    __getsettingscmd = __gencmd + ['settings', 'get']
    __putsettingscmd = __gencmd + ['settings', 'put']

    def __init__(self, serialno=None):
        self.serialno = serialno

    def __addSerial__(self, tmp, serialno=None):
        tmp.insert(1, '-s')
        if serialno is not None:
            tmp.insert(2, serialno)
        else:
            tmp.insert(2, self.serialno)

    def __startServer(self):
        pass

    #         call(['adb','shell','echo'], stdout=PIPE)

    def shell(self, cmd, output=False, serialno=None):
        tmp = []
        tmp.extend(self.__gencmd)
        tmp.extend(cmd)
        self.__addSerial__(tmp, serialno)
        if output:
            return self.check_output_sync(tmp)
        else:
            call(tmp)

    def pull(self, src, dist='', serialno=None):
        tmp = []
        tmp.extend(self.__pullcmd)
        tmp.extend([src, dist])
        self.__addSerial__(tmp, serialno)
        call(tmp)

    def reboot(self, serialno=None):
        tmp = []
        tmp.extend(self.__rebootcmd)
        self.__addSerial__(tmp, serialno)
        call(tmp)

    def push(self, src, dist, serialno=None):
        tmp = []
        tmp.extend(self.__pushcmd)
        tmp.extend([src, dist])
        self.__addSerial__(tmp, serialno)
        call(tmp)

    def inputKeyevnt(self, code, serialno=None):
        tmp = []
        tmp.extend(self.__inputcmd)
        tmp.append(code)
        self.__addSerial__(tmp, serialno)
        call(tmp)

    def dumpsys(self, cmd, serialno=None):
        tmp = []
        tmp.extend(self.__dumpsyscmd)
        tmp.extend(cmd)
        self.__addSerial__(tmp, serialno)
        return self.check_output_sync(tmp)

    def dumpsys(self, cmd, serialno=None):
        tmp = []
        tmp.extend(self.__dumpsyscmd)
        tmp.extend(cmd)
        self.__addSerial__(tmp, serialno)
        return self.check_output_sync(tmp)

    def getSettings(self, cmd, serialno=None):
        tmp = []
        tmp.extend(self.__getsettingscmd)
        tmp.extend(cmd)
        self.__addSerial__(tmp, serialno)
        return self.check_output_sync(tmp)

    def putSettings(self, cmd, serialno=None):
        tmp = []
        tmp.extend(self.__putsettingscmd)
        tmp.extend(cmd)
        self.__addSerial__(tmp, serialno)
        return self.check_output_sync(tmp)

    def install(self, path, serialno=None):
        tmp = []
        tmp.extend(self.__installcmd)
        tmp.append(path)
        self.__addSerial__(tmp, serialno)
        call(tmp)

    def uninstall(self, package, serialno=None):
        tmp = []
        tmp.extend(self.__uninstallcmd)
        tmp.append(package)
        self.__addSerial__(tmp, serialno)
        return self.check_output_sync(tmp)

    @staticmethod
    def devices():
        return AdbCmd.check_output_sync(AdbCmd.__devicecmd)

    @staticmethod
    def check_output_sync(cmd, err=None):
        # set period for each
        # time.sleep(0.001)
        output = check_output(cmd, stderr=err)
        return output


class AdbDevice(object):
    hiddenService = 'com.fuhu.settingshelper/.SettingsHelperService'
    LIST_SYSTEM = 'system'
    LIST_ALL = 'all'
    LIST_3RD_PARTY = '3rd'
    LIST_RECENT = 'recent'
    orientation = ['natural', 'left', 'upsidedown', 'right']

    def __init__(self, serialno=None):
        self.lock = threading.Semaphore()
        self.cmd = AdbCmd(serialno)
        self.serialno = serialno

    def connect(self):
        self.d = Device(self.serialno)

    #         self.d, self.serialno = ViewClient.connectToDeviceOrExit(serialno=self.serialno)
    #         self.vc = ViewClient(self.d, self.serialno, compresseddump=False, ignoreuiautomatorkilled=True, autodump=False)

    def startActivity(self, component):
        component = component.replace('$', '\$')
        self.cmd.shell(['am', 'start', '-n', component, '--activity-clear-task'])

    def isConnected(self):
        if self.__getDevices(self.serialno):
            return True
        else:
            return False

    def listPackages(self):
        return self.cmd.shell(['pm', 'list', 'package'], output=True)

    def reboot(self):
        self.cmd.reboot()

    def dump(self, compressed=False):
        return self.d.dump(compressed=compressed).encode('utf-8')

    @staticmethod
    def retrieveSelector(point, selectors):
        shortestDistance = 500000
        result = None
        for selector in selectors:
            print selector.className
            bounds = selector.info['bounds']
            if point[0] <= bounds['right'] and point[0] >= bounds['left'] and point[1] <= bounds['top'] and point[1] >= \
                    bounds['bottom']:
                return selector

        for selector in selectors:

            bounds = selector.info['bounds']
            distance = (((bounds['left'] + bounds['top']) / 2 - point[0]) ** 2 + (
                (bounds['left'] + bounds['bottom']) / 2 - point[1]) ** 2) ** 0.5
            if shortestDistance > distance:
                shortestDistance = distance
                result = selector
        return result

    def checkSamePoint(self, point, info, isLongClick=False):
        print info
        if not self.isScreenOn():
            self.powerBtn()
            if self.isLocked():
                self.unlock()

        if len(info) == 2:
            if self.d.info['currentPackageName'] == info['packageName']:
                self.cmd.shell(['input', 'tap', str(point[0]), str(point[1])])
                return {'answer': True, 'reason': 'it is the navigation bar'}

        if info['content-desc'] != '':
            self.d(contentDescription=info['content-desc'])
            return {'answer': True, 'reason': 'find by description'}
        if info['text'] != '':
            self.d(text=info['text']).click()
            return {'answer': True, 'reason': 'find by text'}

        currentViewMap = self.getTouchViewInfo(point)
        if currentViewMap:
            if currentViewMap['package'] == info['package']:
                if currentViewMap['class'] == info['class']:
                    self.d.click(point[0], point[1])
                    return {'answer': True, 'reason': 'Find the similar view'}
                else:
                    return {'answer': False, 'reason': 'the view doesn\'t be found.'}
            else:
                return {'answer': False, 'reason': 'In the wrong page'}
        else:
            return {'answer': False, 'reason': 'the view can\'t be found.'}

    @staticmethod
    def removeKey(d, keys):
        r = dict(d)
        for k in keys:
            if r.has_key(k):
                del r[k]
        return r

    def __getDevices(self, serial):
        outputRE = re.compile(serial)
        devices = outputRE.findall(AdbCmd.devices())
        if len(devices) > 0:
            return devices[0]

    def getTouchViewInfo(self, point, compressed=False):
        smallestArea = sys.maxint
        result = None
        root = ET.fromstring(self.dump(compressed=compressed))
        for node in root.iter('node'):
            bounds = re.match('\[(?P<x1>[\d]+),(?P<y1>[\d]+)\]\[(?P<x2>[\d]+),(?P<y2>[\d]+)\]', node.get('bounds'))
            isInclude, area = self._parseRange(point,
                                               (int(bounds.group('x1')), int(bounds.group('y1'))),
                                               (int(bounds.group('x2')), int(bounds.group('y2'))))
            if isInclude:
                if area <= smallestArea:
                    smallestArea = area
                    result = node

        if result is not None:
            return result.attrib
        elif point[1] > self.d.info['displayHeight']:
            p = {'packageName': self.d.info['currentPackageName'], 'type': 'Navigation Bar'}
            return p

    @staticmethod
    def getBoundsCenter(bounds):
        bounds = re.match('\[(?P<x1>[\d]+),(?P<y1>[\d]+)\]\[(?P<x2>[\d]+),(?P<y2>[\d]+)\]', bounds)
        x = (int(bounds.group('x2')) + int(bounds.group('x1'))) / 2
        y = (int(bounds.group('y2')) + int(bounds.group('y1'))) / 2
        return x, y

    @staticmethod
    def _parseRange(point, point1, point2):
        if point[0] >= point1[0] and point[0] <= point2[0]:
            if point[1] >= point1[1] and point[1] <= point2[1]:
                area = (point2[0] - point1[0]) * (point2[1] - point1[1])
                return (True, area)
            else:
                return (False, None)
        else:
            return (False, None)

    def viewFilter(self, view):
        if view.getClass() == self.viewClass:
            return True
        else:
            return False

    def screenOn(self, status):
        if status == True:
            self.d.screen.on()
        else:
            self.d.screen.off()

    def clearLog(self):
        self.cmd.shell(['logcat', '-c'])

    def longClick(self, x, y, duration):
        if y <= self.d.info['displayHeight']:
            self.d.swipe(x, y, x, y, steps=duration / 10)
        else:
            self.cmd.shell(['input', 'tap', str(x), str(y)])

    def click(self, x, y):
        if y <= self.d.info['displayHeight']:
            self.d.click(x, y)
        else:
            self.cmd.shell(['input', 'tap', str(x), str(y)])

    def drag(self, x, y, duration):
        self.d.drag(x[0], x[1], y[0], y[1], steps=duration / 10)

    def swipe(self, x, y, duration):
        self.cmd.shell(['input', 'swipe', str(x[0]), str(x[1]), str(y[0]), str(y[1]), str(duration)])

    def type(self, text):
        translate = re.sub(r'([#\(\)\&\*\'\\\"\~\`\|\<\>?\;])', r'\\\1', text)
        self.cmd.shell(['input', 'text', translate])
        # self.d(className="android.widget.EditText").set_text(text)

    def hideKeyboard(self):
        if self.isKeyboardShown():
            self.backBtn()

    def unlock(self):
        if self.isLocked():
            self.menuBtn()

    def isLocked(self):
        lockScreenRE = re.compile('mShowingLockscreen=(true|false)')
        m = lockScreenRE.search(self.cmd.dumpsys(['window', 'policy']))
        if m is not None:
            return m.group(1) == 'true'

    def isScreenOn(self):
        screenOnRE = re.compile('mScreenOnFully=(true|false)')
        m = screenOnRE.search(self.cmd.dumpsys(['window', 'policy']))
        if m is not None:
            return m.group(1) == 'true'

    def powerBtn(self):
        self.cmd.inputKeyevnt('POWER')

    def backBtn(self):
        self.cmd.inputKeyevnt('BACK')

    def homeBtn(self):
        self.cmd.inputKeyevnt('HOME')

    def menuBtn(self):
        self.cmd.inputKeyevnt('MENU')

    # def rotate(self, orient):
    #     if orient == 'auto':
    #         self.d.freeze_rotation(False)
    #     elif orient == '0':
    #         self.d.orientation = 'n'
    #     elif orient == '90':
    #         self.d.orientation = 'l'
    #     elif orient == '180':
    #         self.d.freeze_rotation(True)
    #         self._setScreenOrient(2)
    #     elif orient == '270':
    #         self.d.orientation = 'r'

    def rotate(self, orient):
        self.d.freeze_rotation(True)
        index = self.orientation.index(self.d.orientation)
        if orient == 'left':
            index -= 1
            if index < 0:
                self._setScreenOrient(len(self.orientation) - 1)
            else:
                self._setScreenOrient(index)
        elif orient == 'right':
            index += 1
            if index >= len(self.orientation):
                self._setScreenOrient(0)
            else:
                self._setScreenOrient(index)

    def volumeUp(self):
        self.cmd.inputKeyevnt('VOLUME_UP')

    def volumeDown(self):
        self.cmd.inputKeyevnt('VOLUME_DOWN')

    #     def _setAutoRotate(self, status):
    #         if status:
    #             self.cmd.shell(['content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:accelerometer_rotation',
    #                             '--bind', 'value:i:1'])
    #             time.sleep(1)
    #             self.cmd.shell(['content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:accelerometer_rotation',
    #                             '--bind', 'value:i:1'])
    #
    #         else:
    #             self.cmd.shell(['content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:accelerometer_rotation',
    #                             '--bind', 'value:i:0'])
    #             time.sleep(1)
    #             self.cmd.shell(['content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:accelerometer_rotation',
    #                             '--bind', 'value:i:0'])


    def _setScreenOrient(self, orient):
        self.cmd.shell(['content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:user_rotation',
                        '--bind', 'value:i:' + str(orient)])

    def resetPackage(self, package):
        self.cmd.shell(['pm', 'clear', package])

    def takeSnapshot(self, path):
        return self.d.screenshot(path)

    def getCurrDisplay(self):
        output = self.cmd.dumpsys(['display'])
        match = re.search('mCurrentOrientation=(?P<orientation>[\d])[\w\d\s\(\),-=]+'
                          + 'mCurrentDisplayRect=Rect\(0, 0 - (?P<width>[\d]+),\s+(?P<height>[\d]+)', output)
        width = int(match.group('width'))
        height = int(match.group('height'))
        orientation = int(match.group('orientation'))
        mode = 'landscape' if width > height else 'portrait'
        return {'width': width, 'height': height, 'orientation': orientation, 'mode': mode}

    def getRealDisplay(self):
        output = self.cmd.dumpsys(['display'])
        match = re.search('real\s(?P<width>[\d]+)\sx\s(?P<height>[\d]+)', output)
        return {'width': int(match.group('width')), 'height': int(match.group('height'))}

    def getProp(self, propType=None):
        if propType:
            return self.cmd.shell(['getprop', propType], output=True).strip('\n')
        else:
            return self.cmd.shell(['getprop'], output=True).strip('\n')

    def uninstall(self, package):
        self.cmd.uninstall(package)

    def install(self, name):
        self.cmd.install(name)

    def close(self):
        pass

    def checkConnected(self):
        return self.d.checkConnected()

    def extractComponentName(self, packageName):
        if packageName == 'com.google.android.youtube':
            return 'com.google.android.youtube/.app.honeycomb.Shell$HomeActivity'
        output = self.cmd.dumpsys(['package', packageName])
        try:
            if os.name == 'nt':
                splitOutput = output.split('\r\r\n')
            else:
                splitOutput = output.split('\r\n')
            num = splitOutput.index(next(x for x in splitOutput if x.find('android.intent.action.MAIN:') != -1))
            if num != -1:
                print splitOutput[num + 1]
                return splitOutput[num + 1].split()[1]
            else:
                return None
        except:
            return None

    def screenTimeout(self):
        timeout = self.cmd.getSettings(['system', 'screen_off_timeout'])
        return long(timeout) / 1000

    def setScreenTimeout(self, value):
        self.cmd.putSettings(['system', 'screen_off_timeout', value])

    def isNfcOn(self):
        match = re.search('mState=(on|off)', self.cmd.dumpsys(['nfc']))
        if match:
            if match.group(1) == 'on':
                return True
            else:
                return False
        else:
            return False

    def isAirPlaneModeOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['global', 'airplane_mode_on']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isInstallUnknownSources(self):
        match = re.search('(0|1)', self.cmd.getSettings(['global', 'install_non_market_apps']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isKeyboardShown(self):
        output = self.cmd.dumpsys(['input_method'])
        result = re.search('mInputShown=(true|false)', output)
        if result.group(1) == 'true':
            return True
        else:
            return False

    def isWifiOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['global', 'wifi_on']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isBtOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['global', 'bluetooth_on']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isNoKeepActivityOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['global', 'always_finish_activities']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isDataRoamingOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['global', 'data_roaming']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isAutoRotateOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['system', 'accelerometer_rotation']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isGpsOn(self):
        state = self.cmd.getSettings(['secure', 'location_providers_allowed'])
        if state == 'none':
            return False
        else:
            return True

    def isAutoBrightnessOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['system', 'screen_brightness_mode']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False

    def isVibrateWhenRingOn(self):
        match = re.search('(0|1)', self.cmd.getSettings(['system', 'vibrate_when_ringing']))
        if match:
            if match.group(1) == '1':
                return True
            else:
                return False
        else:
            return False

    def isWindowAniOn(self):
        match = re.search('(0.0|1.0)', self.cmd.getSettings(['global', 'window_animation_scale']))
        if match:
            if match.group(1) == '0.0':
                return True
            else:
                return False
        else:
            return False

    def isTransitionAnuOn(self):
        match = re.search('(0.0|1.0)', self.cmd.getSettings(['global', 'transition_animation_scale']))
        if match:
            if match.group(1) == '0.0':
                return True
            else:
                return False
        else:
            return False

    def isDurationAniOn(self):
        match = re.search('(0.0|1.0)', self.cmd.getSettings(['global', 'animator_duration_scale']))
        if match:
            if match.group(1) == '0.0':
                return True
            else:
                return False
        else:
            return False

    def enableWifi(self, state):
        if state:
            self.cmd.shell(['am', 'startservice', '--ez', 'wifi', 'true', '-n',
                            self.hiddenService])
        else:
            self.cmd.shell(['am', 'startservice', '--ez', 'wifi', 'false', '-n',
                            self.hiddenService])

    def enableBluetooth(self, state):
        if state:
            self.cmd.shell(['am', 'startservice', '--ez', 'bt', 'true', '-n',
                            self.hiddenService])
        else:
            self.cmd.shell(['am', 'startservice', '--ez', 'bt', 'false', '-n',
                            self.hiddenService])

    def enableInstallUnknownSources(self, state):
        if state:
            self.cmd.putSettings(['global', 'install_non_market_apps', '1'])
        else:
            self.cmd.putSettings(['global', 'install_non_market_apps', '0'])

    def enableNfc(self, state):
        if state:
            self.cmd.shell(['service', 'call', 'nfc', '6'])
        else:
            self.cmd.shell(['service', 'call', 'nfc', '5'])

    def enableNoKeepActivity(self, state):
        if state:
            self.cmd.putSettings(['global', 'always_finish_activities', '1'])
        else:
            self.cmd.putSettings(['global', 'always_finish_activities', '0'])

    def enableDataRoaming(self, state):
        if state:
            self.cmd.putSettings(['global', 'data_roaming', '1'])
        else:
            self.cmd.putSettings(['global', 'data_roaming', '0'])

    def enableAutoRotate(self, state):
        if state:
            self.cmd.putSettings(['system', 'accelerometer_rotation', '1'])
        else:
            self.cmd.putSettings(['system', 'accelerometer_rotation', '0'])

    def enableGps(self, state):
        if state:
            self.cmd.putSettings(['secure', 'location_providers_allowed', 'gps,network'])
        else:
            self.cmd.putSettings(['secure', 'location_providers_allowed', 'none'])

    def enableAutoBrightness(self, state):
        if state:
            self.cmd.putSettings(['system', 'screen_brightness_mode', '1'])
        else:
            self.cmd.putSettings(['system', 'screen_brightness_mode', '0'])

    def enableVibrateRinging(self, state):
        if state:
            self.cmd.putSettings(['system', 'vibrate_when_ringing', '1'])
        else:
            self.cmd.putSettings(['system', 'vibrate_when_ringing', '0'])

    def enableVibrateWhenRing(self, state):
        if state:
            self.cmd.putSettings(['system', 'vibrate_when_ringing', '1'])
        else:
            self.cmd.putSettings(['system', 'vibrate_when_ringing', '0'])

    def enableWindowAnimator(self, state):
        if state:
            self.cmd.putSettings(['global', 'window_animation_scale', '1.0'])
        else:
            self.cmd.putSettings(['global', 'window_animation_scale', '0.0'])

    def enableTransitionAnimator(self, state):
        if state:
            self.cmd.putSettings(['global', 'transition_animation_scale', '1.0'])
        else:
            self.cmd.putSettings(['global', 'transition_animation_scale', '0.0'])

    def enableDurationAnimation(self, state):
        if state:
            self.cmd.putSettings(['global', 'animator_duration_scale', '1.0'])
        else:
            self.cmd.putSettings(['global', 'animator_duration_scale', '0.0'])

    def enableAirplaneMode(self, state):
        if state:
            self.cmd.putSettings(['global', 'airplane_mode_on', '1'])
            self.cmd.shell(['am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'true'])
        else:
            self.cmd.putSettings(['global', 'airplane_mode_on', '0'])
            self.cmd.shell(['am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'false'])

    def requestPackage(self, t):
        result = None
        if t == self.LIST_ALL:
            result = self.cmd.shell(['pm', 'list', 'packages'], output=True)
        elif t == self.LIST_SYSTEM:
            result = self.cmd.shell(['pm', 'list', 'packages', '-s'], output=True)
        elif t == self.LIST_3RD_PARTY:
            result = self.cmd.shell(['pm', 'list', 'packages', '-3'], output=True)

        if result:
            packages = result.split('\r\n')
            packages.remove('')
            packages.sort()
            return packages

    def getSerialNumber(self):
        return self.serialno
