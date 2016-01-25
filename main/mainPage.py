# -*- coding: utf-8 -*-
"""
Created on 2016/1/13

@author: Jerry Chen
"""
from subprocess import Popen, PIPE, CalledProcessError, check_output
from Adb import AdbDevice
from utility import ICON_FOLDER, SCRIPT_FOLDER, IS_RELATIVE_EXIST, IS_BLANK, IS_EXIST, NO_EXIST, PRIVATE_FOLDER
from autoSense import AutoSenseItem, INDEX, ACTION, PARAMETER, DESCRIPTION, INFORMATION
from Executor import workExecutor
from time import gmtime, strftime
from PySide import QtCore, QtGui
from GuiTemplate import MainTitleButton, IconButton, IconWithWordsButton, PushButton, TestPlanListView, MyLabel, \
    BottomLineWidget, HContainer, VContainer, ActionListItem, TestPlanListItem, DescriptionEdit, \
    PictureLabel, ActionListView, DelayDialog, MediaCheckDialog
import re
import os
import csv
import time
import glob
import json
import threading


def set_background_color(widget, color):
    c = QtGui.QColor()
    c.setNamedColor(color)
    widget.setAutoFillBackground(True)
    p = widget.palette()
    p.setColor(QtGui.QPalette.Background, c)
    widget.setPalette(p)


class UpdateScreen(QtCore.QThread):
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
        self.isStop = True

    def pause(self):
        self.isPause = True

    def resume(self):
        self.isPause = False

    def setDelay(self, delay=0):
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
        try:
            self.nconcurrent.acquire()
            time.sleep(delay)
            pp = time.time()
            self._device.takeSnapshot(path)
            print time.time() - pp
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
    offline = QtCore.Signal()

    def __init__(self, device):
        super(WaitForDevice, self).__init__()
        self.device = device
        self.isStop = False

    def stop(self):
        self.isStop = True

    def run(self):
        print 'start to monitor'
        self.isStop = False
        while not self.isStop:
            if self.device.isConnected():
                try:
                    print 'start to connect'
                    self.device.connect()
                    self.online.emit()
                    break
                except:
                    print 'Keep searching'
            else:
                self.offline.emit()
            time.sleep(1)


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
        self.monitor.offline.connect(self.deviceDisconnected)
        self.monitor.start()

        self.upsideBar()
        self.firstPage = PlayListPage(self._device)
        self.downsideContent()
        self.createMenus()
        self.initUi()

    def initUi(self):
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(1)
        mainLayout.addWidget(self.categoryWidget)
        mainLayout.addWidget(self.downsideWidget)
        self.setLayout(mainLayout)
        self.showMaximized()
        self.raise_()

    @QtCore.Slot()
    def deviceConnected(self):
        if self.currentPage() == 0:
            self.firstPage.connected()
            self.updateScreen = UpdateScreen(self._device, PRIVATE_FOLDER)
            self.updateScreen.loadDone.connect(self.loadDone)
            self.updateScreen.deviceOffline.connect(self.deviceOffline)
            self.updateScreen.start()

    @QtCore.Slot()
    def deviceDisconnected(self):
        if self.currentPage() == 0:
            self.firstPage.disconnected()


    def upsideBar(self):
        # self.playListBtn = QtGui.QPushButton('PLAYLIST')
        playListBtn = MainTitleButton('PLAYLIST', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        processBtn = MainTitleButton('PROCESS', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        semiCheckBtn = MainTitleButton('SEMI-CHECK', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        reportBtn = MainTitleButton('REPORT', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        playListBtn.setFixedSize(processBtn.sizeHint().width(), 28)
        processBtn.setFixedSize(processBtn.sizeHint().width(), 28)
        semiCheckBtn.setFixedSize(semiCheckBtn.sizeHint().width(), 28)
        reportBtn.setFixedSize(reportBtn.sizeHint().width(), 28)
        playListBtn.clicked.connect(lambda page=0: self.switchPage(page))
        processBtn.clicked.connect(lambda page=1: self.switchPage(page))
        semiCheckBtn.clicked.connect(lambda page=2: self.switchPage(page))
        reportBtn.clicked.connect(lambda page=3: self.switchPage(page))
        self.pageList.append(playListBtn)
        self.pageList.append(processBtn)
        self.pageList.append(semiCheckBtn)
        self.pageList.append(reportBtn)

        categoryLayout = QtGui.QHBoxLayout()
        categoryLayout.setContentsMargins(0, 0, 0, 0)
        categoryLayout.setSpacing(0)
        categoryLayout.addWidget(playListBtn)
        categoryLayout.addWidget(processBtn)
        categoryLayout.addWidget(semiCheckBtn)
        categoryLayout.addWidget(reportBtn)
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
        self.downsideWidget.addWidget(self.firstPage)

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

        # self.openAction.triggered.connect(self.widget.openScript)
        # self.saveAction.triggered.connect(self.widget.saveScript)
        # self.deleteAction.triggered.connect(self.widget.itemDelete)
        # self.clearAction.triggered.connect(self.widget.clear)
        # self.selectAction.triggered.connect(lambda: self.widget.selectAllItems(True))
        # self.deselectAction.triggered.connect(lambda: self.widget.selectAllItems(False))
        # self.deviceInfoAtion.triggered.connect(self.widget.showDeviceInfo)
        # self.scriptConvertAction.triggered.connect(self.widget.showScriptConvertion)
        # self.turnOffAnimation.triggered.connect(self.widget.turnOffAnimation)
        # self.installAction.triggered.connect(self.widget.install)
        # self.uninstallAction.triggered.connect(self.widget.uninstall)

    def switchPage(self, number):
        print 'switch page'
        self.enablePage(number)
        self.downsideWidget.setCurrentIndex(number)
        if number == 0:
            pass
        elif number == 1:
            pass
        elif number == 2:
            pass
        elif number == 3:
            pass

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
        self.firstPage.setScreenContent()

    @QtCore.Slot()
    def deviceOffline(self):
        self.monitor.start()

    def stopThread(self, t):
        if t and t.isRunning():
            t.stop()
            while not t.isFinished():
                time.sleep(0.05)
            print str(t) + ' is finished.'

    def closeEvent(self, event):
        print 'Window is closed.....'
        self.stopThread(self.monitor)
        self.stopThread(self.updateScreen)

        if self._device and self._device.isConnected():
            self._device.close()


class PlayListPage(VContainer):
    ratio = None
    _device = None
    createTimeStamp = None
    selectedPlanItem = None
    selectedActionItem = None
    buttonList = list()
    actionList = list()

    def __init__(self, device):
        super(PlayListPage, self).__init__()
        self._device = device
        self.picPath = PRIVATE_FOLDER + '/' + str(self._device.serialno) + '_screen.png'
        self.initActionBtns()
        self.initTestPlanField()
        self.initScreenFiled()
        self.initDownSide()
        self.enableButtons(False)
        self.setSpacing(1)
        self.addWidget(self.actionMenuWidget)
        self.addWidget(self.combineWidget)

    def initActionBtns(self):
        backBtn = IconButton()
        homeBtn = IconButton()
        menuBtn = IconButton()
        powerBtn = IconButton()
        volumeUp = IconButton()
        volmeDown = IconButton()
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
        volmeDown.setFixedSize(40, 40)
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
        volmeDown.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_zoonout_normal.png'))
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
        volmeDown.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_zoonout_press.png'))
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
        volmeDown.clicked.connect(self.volumeDown)
        rotateLeftBtn.clicked.connect(self.rotateLeft)
        rotateRightBtn.clicked.connect(self.rotateRight)
        unlockBtn.clicked.connect(self.unlockScreen)
        # typeTextBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_typetext_press.png'))
        hideKeyboardBtn.clicked.connect(self.hideKeyboard)

        self.buttonList.append(backBtn)
        self.buttonList.append(homeBtn)
        self.buttonList.append(menuBtn)
        self.buttonList.append(powerBtn)
        self.buttonList.append(volumeUp)
        self.buttonList.append(volmeDown)
        self.buttonList.append(rotateLeftBtn)
        self.buttonList.append(rotateRightBtn)
        self.buttonList.append(unlockBtn)
        self.buttonList.append(typeTextBtn)
        self.buttonList.append(hideKeyboardBtn)

        actionsWidget = HContainer()
        actionsWidget.setSpacing(1)
        for btn in self.buttonList:
            actionsWidget.addWidget(btn)
        set_background_color(actionsWidget, '#282828')

        checkUiBtn = IconWithWordsButton('Check', font_size=12, font_weight=QtGui.QFont.Light, text_color='#D1D1D1')
        checkUiBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        checkUiBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER + '/ic_check_normal.png'))
        checkUiBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER + '/ic_check_press.png'))
        checkUiBtn.setFixedSize(120, 40)
        checkMenu = QtGui.QMenu()
        checkMenu.setStyleSheet('QMenu{background-color: #282828; color: #A0A0A0}'
                                'QMenu::item:selected {background-color: #383838;}')
        checkMenu.addAction('UI exist', lambda check_type=IS_EXIST: self.checkUI(check_type))
        checkMenu.addAction('UI not exist', lambda check_type=NO_EXIST: self.checkUI(check_type))
        checkMenu.addAction('UI is blank', lambda check_type=IS_BLANK: self.checkUI(check_type))
        checkMenu.addAction('UI relative is exist', lambda check_type=IS_RELATIVE_EXIST: self.checkUI(check_type))
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
        mediaCheckBtn.setFixedSize(120, 40)

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

        self.actionMenuWidget = HContainer()
        self.actionMenuWidget.setSpacing(1)
        self.actionMenuWidget.addWidget(actionsWidget)
        self.actionMenuWidget.addWidget(checkUiWidget)
        self.actionMenuWidget.addWidget(mediaCheckWidget)
        self.actionMenuWidget.addWidget(delayWidget)
        self.actionMenuWidget.addWidget(blankWidget)
        self.actionMenuWidget.setAutoFitHeight()

    def initTestPlanField(self):
        # Test plan title filed
        testPlanBtn = MainTitleButton('TestPlan', text_color='#FFFFFF', rect_color='#282828')
        playQueueBtn = MainTitleButton('Play queue', text_color='#FFFFFF', rect_color='#282828')

        testPlanBtn.clicked.connect(lambda page=0: self.switchPage(page))
        playQueueBtn.clicked.connect(lambda page=1: self.switchPage(page))
        self.titleList = [testPlanBtn, playQueueBtn]

        testPlanTitleWidget = HContainer()
        testPlanTitleWidget.addWidget(testPlanBtn)
        testPlanTitleWidget.addWidget(playQueueBtn)
        testPlanTitleWidget.setFixedHeight(30)

        addPlanBtn = PushButton('Add new testplan', font_size=12, text_color='#FFFFFF', rect_color='#282828')
        addPlanBtn.setFixedHeight(30)
        addPlanBtn.clicked.connect(self.addTestPlan)
        appPlanWidget = HContainer()
        appPlanWidget.addWidget(addPlanBtn)
        appPlanWidget.setAutoFitHeight()

        self.startBtn = PushButton(text='PLAY', font_size=14, text_color='#A0A0A0', rect_color='#282828')
        self.startBtn.setNormalIcon(QtGui.QIcon(ICON_FOLDER+'/ic_play normal.png'))
        self.startBtn.setPressIcon(QtGui.QIcon(ICON_FOLDER+'/ic_play press.png'))
        self.startBtn.setFixedHeight(40)

        self.testPlanListView = TestPlanListView('#6C9EFF')
        self.testPlanListView.itemClicked.connect(self.testPlanSelected)

        self.testPlanWidget = VContainer()
        self.testPlanWidget.addWidget(testPlanTitleWidget)
        self.testPlanWidget.addWidget(appPlanWidget)
        self.testPlanWidget.addWidget(self.testPlanListView)
        self.testPlanWidget.addWidget(self.startBtn)
        self.testPlanWidget.setFixedWidth(200)
        set_background_color(self.testPlanWidget, '#282828')

        # switch to Test plan page
        self.switchPage(0)

        # Test plan detail filed
        self.planName = MyLabel('', font_size=12, color='#ffffff')
        self.planName.setFixedHeight(30)
        self.createTime = MyLabel('', font_size=12, color='#A0A0A0')
        self.createTime.setFixedHeight(30)

        testPlanDetailWidget = BottomLineWidget()
        testPlanDetailWidget.addWidget(self.planName)
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
        self.actionListView.itemClicked.connect(self.actionSelected)

        self.descriptionEdit = DescriptionEdit()
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

    def initScreenFiled(self):
        self.virtualScreen = PictureLabel(self, currentPath=self.picPath)
        self.virtualScreen.mouseClick.connect(self.getClick)
        self.virtualScreen.mouseLongClick.connect(self.getLongClick)
        self.virtualScreen.mouseSwipe.connect(self.getSwipe)
        self.virtualScreen.mouseDrag.connect(self.getDrag)
        self.virtualScreen.checkClick.connect(self.addCheck)
        self.virtualScreen.checkRelativeClick.connect(self.addCheckRelative)

        self.virtualWidget = HContainer()
        self.virtualWidget.addWidget(self.virtualScreen, alignment=QtCore.Qt.AlignCenter)
        self.virtualWidget.resizeHappened.connect(self.virtualScreenResize)

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

        self.disconnectView = VContainer()
        self.disconnectView.addWidget(self.noConnectPixLbl)
        self.disconnectView.addWidget(self.noConnectTitle)
        self.disconnectView.addWidget(self.noConnectSubTitle)
        self.disconnectView.setAlignment(QtCore.Qt.AlignCenter)

        self.aboutDeviceWidget = QtGui.QStackedWidget()
        self.aboutDeviceWidget.addWidget(self.virtualWidget)
        self.aboutDeviceWidget.addWidget(self.disconnectView)

    def initDownSide(self):
        line = QtGui.QFrame()
        line.setFrameShape(QtGui.QFrame.VLine)
        line.setStyleSheet('color: #404040;')

        self.combineWidget = HContainer()
        self.combineWidget.addWidget(self.testPlanWidget)
        self.combineWidget.addWidget(self.testActionWidget)
        self.combineWidget.addWidget(line)
        self.combineWidget.addWidget(self.aboutDeviceWidget)

    def enableButtons(self, state):
        self.virtualScreen.setEnabled(state)
        for btn in self.buttonList:
            btn.setEnabled(state)

    def addTestPlan(self):
        text, ok = QtGui.QInputDialog.getText(self, 'Input Dialog',
                                              'Enter Test Plan name:')
        if ok:
            print
            if not self.testPlanListView.haveItem(text):
                self.createTimeStamp = strftime("%Y/%m/%d %H:%M", gmtime())
                self.insertTestPlanItem(text)

    def insertTestPlanItem(self, text):
        fullName = SCRIPT_FOLDER + '/' + text + '.csv'
        if not os.path.exists(fullName):
            self.saveScript(text)
        self.testPlanListView.addCustomItem(self.testPlanListView.count(), TestPlanListItem(text))

    def findTestPlan(self):
        for f in glob.glob(SCRIPT_FOLDER + "/*.csv"):
            baseName = os.path.basename(f)
            self.insertTestPlanItem(baseName[0:baseName.find('.csv')])

    def editDone(self):
        if self.selectedActionItem:
            actionItem = self.actionList[self.actionListView.row(self.selectedActionItem)]
            actionItem.setAnnotation(self.descriptionEdit.toPlainText())
            self.saveScript(self.currentPlanName)

    def disconnected(self):
        self.enableButtons(False)
        self.aboutDeviceWidget.setCurrentIndex(1)

    def connected(self):
        self.aboutDeviceWidget.setCurrentIndex(0)

    def testPlanSelected(self, item):
        del self.actionList[:]
        self.selectedPlanItem = item
        self.selectedActionItem = None
        self.actionListView.clear()
        self.enableButtons(True)
        self.currentPlanName = self.testPlanListView.itemWidget(item).text()
        self.loadScript(self.currentPlanName + '.csv')
        self.planName.setText(self.currentPlanName)
        self.descriptionEdit.clear()

    def actionSelected(self, item):
        self.selectedActionItem = item
        print 'editDone = ' + str(self.actionListView.row(item))
        self.descriptionEdit.setEnabled(True)
        item = self.actionList[self.actionListView.row(item)]
        self.descriptionEdit.setPlainText(item.annotation())

    def checkUI(self, checkType):
        self.virtualScreen.drawGrid(self._device.dump(), checkType)
        self.virtualScreen.setMouseIgnore(True)

    def switchPage(self, number):

        if number == 0:
            self.titleList[0].setEnabled(False)
            self.titleList[1].setEnabled(True)
            self.startBtn.setVisible(False)
        else:
            self.titleList[0].setEnabled(True)
            self.titleList[1].setEnabled(False)
            self.startBtn.setVisible(True)

    def setScreenContent(self):
        try:
            pic = QtGui.QPixmap(self.picPath)
            if not pic.isNull():
                pic = pic.scaled(pic.size().width() * self.ratio,
                                 pic.size().height() * self.ratio,
                                 aspectMode=QtCore.Qt.KeepAspectRatio)
                if not self.virtualScreen.pixmap():
                    self.virtualScreen.setPixmap(pic)
                # self.scrollArea.setFixedSize(pic.size().width() + 2, pic.size().height() + 2)
                self.virtualScreen.setMaximumSize(pic.size().width(), pic.size().height())
                self.virtualScreen.setPicScale(self.ratio)
                self.virtualScreen.update()
        except IndexError as e:
            print 'IndexError: ' + e.message

    def calculateScale(self, displayInfo, size):
        width = displayInfo['width']
        height = displayInfo['height']
        if width > height:
            ratio = float(size.width()) / width
        elif width < height:
            ratio = float(size.height()) / height
        return ratio

    def addListItem(self, action, param='', info=''):
        print 'addListItem'
        insertRow = self.actionListView.getInsertRow()
        item = AutoSenseItem()
        item.setIndex(self.actionListView.count() + 1)
        item.setAction(action)
        item.setParameter(param)
        item.setInformation(info)
        self.actionList.insert(insertRow, item)
        self.restoreListView()

    def restoreListView(self, scrollToIndex=None):
        self.descriptionEdit.setEnabled(False)
        self.saveScript(self.currentPlanName)
        self.actionListView.clear()
        for i in range(len(self.actionList)):
            self.actionList[i].setIndex(str(i + 1))
            action = self.actionList[i].action()
            if self.actionList[i].parameter():
                action += '[' + ','.join(str(p) for p in self.actionList[i].parameter()) + ']'
            self.actionListView.addCustomItem(i, action)

        if scrollToIndex:
            self.scrollListViewTo(scrollToIndex, isSelect=False)

    @QtCore.Slot()
    def virtualScreenResize(self, event):
        self.ratio = self.calculateScale(self._device.getCurrDisplay(), event.size())
        self.setScreenContent()
        print self.ratio

    @QtCore.Slot()
    def getClick(self, point):
        print 'get Click'
        x = int(point.x() / self.ratio)
        y = int(point.y() / self.ratio)
        pressPoint = (x, y)
        info = self._device.getTouchViewInfo(pressPoint)

        s = json.dumps(info)
        param = list(pressPoint)
        self.addListItem('Click', param=param, info=s)

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
        self.addListItem('LongClick', param=param, info=s)
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
        self.addListItem('Drag', param, s)
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
        self.addListItem('Swipe', param, s)
        workExecutor(self._device.swipe, (self.dragFrom, self.dragTo, speed))

    @QtCore.Slot()
    def addCheck(self, point, check_type):
        x = int(point.x() / self.ratio)
        y = int(point.y() / self.ratio)
        press_point = (x, y)
        info = self._device.getTouchViewInfo(press_point)

        if check_type == IS_RELATIVE_EXIST:
            self.check_relative_ui(QtCore.QPoint(x, y))
            return

        param = list()
        if info['text'] != '':
            param.append('text=%s' % info['text'])
        elif info['content-desc'] != '':
            param.append('description=%s' % info['content-desc'])
        elif info['resource-id'] != '':
            param.append('resourceId=%s' % info['resource-id'])
        else:
            param.append('className=%s' % info['class'])
        center_point = self._device.getBoundsCenter(info['bounds'])
        param.append(center_point[0])
        param.append(center_point[1])
        self.addListItem(check_type, param)

        self.virtualScreen.doneDrawGrid()
        self.virtualScreen.setMouseIgnore(False)

    @QtCore.Slot()
    def addCheckRelative(self):
        print 'addCheckRelative'

    def pressMediaCheck(self):
        testTime, timeout, ok = MediaCheckDialog.getCheckTime()
        if ok and len(testTime) != 0 and len(timeout) != 0:
            self.addListItem('MediaCheck', param=[testTime, timeout])

    def pressDelay(self):
        inputDelay, ok = DelayDialog.getDelay()
        if ok and len(inputDelay) != 0:
            self.addListItem('Delay', param=inputDelay)

    def pressBack(self):
        workExecutor(self._device.backBtn)
        self.addListItem('Back')

    def pressPower(self):
        workExecutor(self._device.powerBtn)
        self.addListItem('Power')

    def pressHome(self):
        workExecutor(self._device.homeBtn)
        self.addListItem('Home')

    def pressMenu(self):
        workExecutor(self._device.menuBtn)
        self.addListItem('Menu')

    def unlockScreen(self):
        workExecutor(self._device.unlock)
        self.addListItem('Unlock')

    def volumeUp(self):
        self._device.volumeUp()

    def volumeDown(self):
        self._device.volumeDown()

    def rotateLeft(self):
        workExecutor(self._device.rotate, ('left',))
        self.addListItem('Rotate', param='left')

    def rotateRight(self):
        workExecutor(self._device.rotate, ('right',))
        self.addListItem('Rotate', param='right')

    def hideKeyboard(self):
        workExecutor(self._device.hideKeyboard)
        self.addListItem('HideKeyboard')

    def saveScript(self, fileName):
        with open(SCRIPT_FOLDER + '/' + fileName + '.csv', 'wb') as csvfile:
            fieldnames = [INDEX, ACTION, PARAMETER, INFORMATION, DESCRIPTION]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in self.actionList:
                writer.writerow(item.inDict())
            real = self._device.getRealDisplay()
            resolution = [real['width'], real['height']]
            writer.writerow({INDEX: '-1', ACTION: 'resolution', PARAMETER: str(resolution)})
            writer.writerow({INDEX: '-2', ACTION: 'create', PARAMETER: self.createTimeStamp})

    def loadScript(self, fileName):
        screenMode = self._device.getCurrDisplay()['mode']
        with open(SCRIPT_FOLDER + '/' + fileName, 'rt') as csvfile:
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
                    self.actionList.append(item)
                elif row[ACTION] == 'create':
                    self.createTimeStamp = row[PARAMETER]
                # else:
                #     if row[ACTION] == 'resolution':
                #         x, y = row[PARAMETER].strip('[\[\]]').split(',')
                #         param = [int(x), int(y)]
                #         display = self._device.getRealDisplay()
                #         curr = [display['width'], display['height']]
                #         if param != curr:
                #             self.showBox(QtGui.QMessageBox.Warning,
                #                          'The script is inappropriate for this device.' + str(x) + ' x' + str(y));
            self.restoreListView()
