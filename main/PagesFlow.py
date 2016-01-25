# -*- coding: utf-8 -*-
"""
Created on 2015/12/8

@author: Jerry Chen
"""
import sys
import os
import subprocess
from utility import NFC, WIFI, AIRPLANE, GPS, AUTO_ROTATE, BLUETOOTH, DATA_ROAMING, ALLOW_APP, NO_KEEP_ACTIVITY, \
                AUTO_BRIGHTNESS, BRIGHTNESS_SET, VIBRATE, WINDOW_ANIMATOR, TRANSITION_ANIMATOR, DURATION_ANIMATION, \
                KEEP_WIFI, ICON_FOLDER, ROOT_FOLDER, FONT_FOLDER, LOG_FOLDER, SCRIPT_FOLDER, PRIVATE_FOLDER, \
                IMAGE_FOLDER
from DeviceManager import Manager
import directory as folder
from Adb import AdbDevice
from mainPage import MainPage
from PySide import QtCore, QtGui
from GuiTemplate import IntroWindow, ListWidgetWithLine, InfoListWidget, IconButton, \
    MyCheckBox, MyLabel, MyLineEdit, SearchBox, MyProcessingBar, SettingIconButton, TitleButton


class DeviceInfoThread(QtCore.QThread):
    onDeviceInfo = QtCore.Signal(dict)

    def __init__(self, serialno=None):
        super(DeviceInfoThread, self).__init__()
        self.serialNo = serialno

    def setDeviceId(self, ID):
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

        holdInfo['resolution'] = device.cmd.shell(['cat', 'proc/version'], output=True).strip('\r\n')
        display = device.getRealDisplay()
        holdInfo['kernelNo'] = str(display['width']) + ' x ' + str(display['height'])

        self.onDeviceInfo.emit(holdInfo)


class DeviceSettingsThread(QtCore.QThread):
    currentSettings = QtCore.Signal(dict, bool)
    device = None

    def __init__(self):
        super(DeviceSettingsThread, self).__init__()

    def setDevice(self, device):
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
    currentPackages = QtCore.Signal(list)
    device = None
    t = ''

    def __init__(self):
        super(PackagesThread, self).__init__()

    def setDevice(self, device):
        self.device = device

    def setType(self, t):
        self.t = t

    def run(self):
        self.currentPackages.emit(self.device.requestPackage(self.t))


class SendSettingThread(QtCore.QThread):
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
    done = QtCore.Signal()

    def __init__(self, f, device):
        super(InstallThread, self).__init__()
        self.f = f
        self.device = device

    def run(self):
        self.device.install(self.f)
        self.done.emit()


class LandingPage(IntroWindow):
    w = None

    def __init__(self):
        super(LandingPage, self).__init__()
        logo = QtGui.QPixmap(ICON_FOLDER + '/' + 'ic_logo_with_shadow.png')
        self.lbl = QtGui.QLabel()
        self.lbl.setPixmap(logo)

        self.welcomeTitle = QtGui.QLabel('Welcome to Autosense')
        font = self.welcomeTitle.font()
        font.setBold(True)
        font.setPixelSize(30)
        self.welcomeTitle.setFont(font)

        self.welcomeSubTitle = QtGui.QLabel('What do you want to do first?')
        self.welcomeSubTitle.setStyleSheet('font: Light')
        font = self.welcomeSubTitle.font()
        font.setPixelSize(12)
        font.setWeight(QtGui.QFont.Light)
        self.welcomeSubTitle.setFont(font)

        self.createBtn = QtGui.QPushButton()
        self.createBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_add_new_testplan.png'))
        self.createBtn.setStyleSheet('border: 0px')
        self.createBtn.setIconSize(QtCore.QSize(128, 128))
        self.createBtn.clicked.connect(self.button_clicked)
        self.createTitle = QtGui.QLabel('Create\nNew Testplan')
        self.createTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.createLayout = QtGui.QVBoxLayout()
        self.createLayout.addWidget(self.createBtn)
        self.createLayout.addWidget(self.createTitle)
        self.createLayout.setSpacing(0)
        self.createLayout.setContentsMargins(0, 0, 36, 0)

        self.loadBtn = QtGui.QPushButton()
        self.loadBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_load_testplan.png'))
        self.loadBtn.setStyleSheet('border: 0px')
        self.loadBtn.setIconSize(QtCore.QSize(128, 128))
        self.loadTitle = QtGui.QLabel('Load\nTestplan')
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
        titleLayout.addWidget(self.lbl, alignment=QtCore.Qt.AlignHCenter)
        titleLayout.addWidget(self.welcomeTitle, alignment=QtCore.Qt.AlignHCenter)
        titleLayout.addWidget(self.welcomeSubTitle, alignment=QtCore.Qt.AlignHCenter)
        titleWidget = QtGui.QWidget()
        titleWidget.setLayout(titleLayout)
        titleWidget.setFixedSize(titleLayout.sizeHint())

        choseLayout = QtGui.QHBoxLayout()
        choseLayout.addLayout(self.createLayout)
        choseLayout.addLayout(self.loadLayout)
        choseLayout.addLayout(self.readLayout)
        choseWidget = QtGui.QWidget()
        choseWidget.setLayout(choseLayout)
        choseWidget.setFixedSize(choseLayout.sizeHint())

        bottomLayout = QtGui.QVBoxLayout()
        bottomLayout.addWidget(self.noShowCheck)
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        bottomWidget = QtGui.QWidget()
        bottomWidget.setLayout(bottomLayout)

        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(titleWidget, alignment=QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        mainLayout.addWidget(choseWidget, alignment=QtCore.Qt.AlignCenter)
        mainLayout.addWidget(bottomWidget, alignment=QtCore.Qt.AlignBottom)
        mainLayout.setContentsMargins(0, 0, 0, 0)

        self.setCentralLayout(mainLayout)
        self.setOkBtnText('OK')
        self.setWindowTitle('Autosense')
        self.setStyleSheet('color: #585858')
        x = self.getScreenGeometry().width() / 2 - (mainLayout.sizeHint().width() + 400) / 2
        y = self.getScreenGeometry().height() / 2 - self.sizeHint().height() / 2
        self.setGeometry(x,
                         y,
                         mainLayout.sizeHint().width() + 400,
                         self.sizeHint().height())
        self.setFixedSize(mainLayout.sizeHint().width() + 400, self.sizeHint().height())
        self.show()
        self.raise_()

    def button_clicked(self):
        self.newPage = CreateNewPage()
        self.close()


class CreateNewPage(IntroWindow):
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
        self.show()
        self.raise_()

    def button_clicked(self):
        if len(self.nameInput.text()) == 0 or len(self.describeInput.toPlainText()) == 0:
            self.warningWidget.setHidden(False)
        else:
            self.cd = ChoseDevicePage()
            self.close()


class ChoseDevicePage(IntroWindow):
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
        self.setOkBtnText('Next')
        self.okBtn.clicked.connect(self.next_click)
        self.setLeaveBtnText('Setting')
        self.leaveBtn.clicked.connect(self.setting_click)
        self.setWindowTitle('Create New Testplan')
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

    def next_click(self):
        items = self.deviceList.selectedItems()
        if len(items) == 1:
            print items[0].text()
            self.w = MainPage()
            self.close()
        else:
            print 'No selected item'

    def setting_click(self):
        if self.deviceList.currentItem():
            self.w = SettingPage(self.deviceList.currentItem().text())
            self.close()

    def refreshDeviceList(self):
        self.deviceList.clear()
        self.infoList.clear()
        self.deviceName.setText('')
        devices = self.askForDevices()
        if len(devices) == 0:
            self.w = NoConnectDevicePage()
            self.close()
            return False
        else:
            self.loadDeviceList(devices)
            return True

    def loadDeviceList(self, devices):
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
        installBtn.clicked.connect(self.install)
        uninstallBtn = IconButton()
        uninstallBtn.setIcon(QtGui.QIcon(ICON_FOLDER + '/ic_delete app_normal.png'))
        uninstallBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_delete app_press.png'))
        uninstallBtn.clicked.connect(self.uninstall)

        apkLayout = QtGui.QHBoxLayout()
        apkLayout.setContentsMargins(0, 0, 0, 0)
        apkLayout.setSpacing(0)
        apkLayout.addWidget(uninstallBtn)
        apkLayout.addWidget(installBtn)
        apkWidget = QtGui.QWidget()
        apkWidget.setLayout(apkLayout)
        apkWidget.setFixedSize(apkLayout.sizeHint())

        self.allBtn = TitleButton('All', font_size=12, color='#464646')
        self.allBtn.clicked.connect(lambda result=AdbDevice.LIST_ALL: self.refreshPackageList(result))
        self.allBtn.setFixedHeight(40)
        self.systemBtn = TitleButton('System', font_size=12, color='#464646')
        self.systemBtn.clicked.connect(lambda result=AdbDevice.LIST_SYSTEM: self.refreshPackageList(result))
        self.systemBtn.setFixedHeight(40)
        self.trdPartyBtn = TitleButton('3rd Party', font_size=12, color='#464646')
        self.trdPartyBtn.clicked.connect(lambda result=AdbDevice.LIST_3RD_PARTY: self.refreshPackageList(result))
        self.trdPartyBtn.setFixedHeight(40)
        self.recentBtn = TitleButton('Recent', font_size=12, color='#464646')
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
        print item
        if item:
            self.device.uninstall(str(item.text()))
            self.refreshPackageList(self.packageType)

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
        self.show()
        self.raise_()
        self.loadingBar.setMovingColor('#1E90FF', '#82B1FF')
        self.loadingBar.start()

    def onDone(self):
        self.loadingBar.stop()
        self.close()
        print self.device.getSerialNumber()
        self.w = SettingPage(self.device.getSerialNumber())


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


def add_font_family(app):
    for f in os.listdir(FONT_FOLDER):
        if f[-4:len(f)] == '.ttf':
            mid = QtGui.QFontDatabase.addApplicationFont(FONT_FOLDER + '/' + f)

    print QtGui.QFontDatabase.applicationFontFamilies(mid)[0]
    app.setFont(QtGui.QFont('Open Sans'))


def main():
    if not os.path.exists(ROOT_FOLDER): os.mkdir(ROOT_FOLDER)
    if not os.path.exists(LOG_FOLDER): os.mkdir(LOG_FOLDER)
    if not os.path.exists(SCRIPT_FOLDER): os.mkdir(SCRIPT_FOLDER)
    if not os.path.exists(PRIVATE_FOLDER): os.mkdir(PRIVATE_FOLDER)
    if not os.path.exists(IMAGE_FOLDER): os.mkdir(IMAGE_FOLDER)

    app = QtGui.QApplication(sys.argv)
    add_font_family(app)
    wid = MainPage('DT08A00003871140504')
    # wid = SettingPage('DT08A00003871140504')
    # wid = waitDevicePage()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
