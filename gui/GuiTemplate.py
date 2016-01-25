from PySide import QtGui, QtCore
from utility import FONT_FAMILY

import xml.etree.ElementTree as ET
import directory as folder
import time
import re


class Container(QtGui.QWidget):
    def __init__(self, witch):
        super(Container, self).__init__()
        if witch == 'H':
            self.mLayout = QtGui.QHBoxLayout()
        else:
            self.mLayout = QtGui.QVBoxLayout()
        self.mLayout.setContentsMargins(0, 0, 0, 0)
        self.mLayout.setSpacing(0)
        self.setLayout(self.mLayout)


class Container(QtGui.QWidget):
    needBottomBorder = False
    needBorder = False
    bottomColor = None
    resizeHappened = QtCore.Signal(QtGui.QResizeEvent)

    def __init__(self, witch):
        super(Container, self).__init__()
        if witch == 'H':
            self.mLayout = QtGui.QHBoxLayout()
        else:
            self.mLayout = QtGui.QVBoxLayout()
        self.mLayout.setContentsMargins(0, 0, 0, 0)
        self.mLayout.setSpacing(0)
        self.setLayout(self.mLayout)

    def drawBottomLine(self, qp, width, color):
        pen = QtGui.QPen()
        pen.setWidth(width)
        pen.setBrush(color)
        qp.setPen(pen)
        qp.drawLine(self.rect().bottomLeft(), self.rect().bottomRight())

    def addWidget(self, widget, alignment=None):
        if alignment:
            self.mLayout.addWidget(widget, alignment)
        else:
            self.mLayout.addWidget(widget)

    def setAutoFitSize(self):
        self.setFixedSize(self.mLayout.sizeHint())

    def setAutoFitHeight(self):
        self.setFixedHeight(self.mLayout.sizeHint().height())

    def setAutoFixedFitWidth(self):
        self.setFixedWidth(self.mLayout.sizeHint().width())

    def setSpacing(self, value):
        self.mLayout.setSpacing(value)

    def addStretch(self, value):
        self.mLayout.addStretch(value)

    def setMargins(self, left, top, right, bottom):
        self.mLayout.setContentsMargins(left, top, right, bottom)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            if self.needBottomBorder:
                self.drawBottomLine(qp, 1, QtGui.QColor('#333333'))
        finally:
            qp.end()

    def setBottomLine(self, isNeed, color=None):
        self.needBottomBorder = isNeed
        if color:
            self.bottomColor = color

    def resizeEvent(self, event):
        self.resizeHappened.emit(event)

    def setAlignment(self, alignment):
        self.mLayout.setAlignment(alignment)

class HContainer(Container):
    def __init__(self):
        super(HContainer, self).__init__(witch='H')


class VContainer(Container):
    def __init__(self):
        super(VContainer, self).__init__(witch='V')


class IntroWindow(QtGui.QWidget):
    def __init__(self):
        super(IntroWindow, self).__init__()
        self.deskInfo = QtGui.QApplication.desktop()
        self.leaveBtn = QtGui.QPushButton()
        self.leaveBtn.setFixedSize(self.leaveBtn.sizeHint())
        self.leaveBtn.setVisible(False)
        self.okBtn = QtGui.QPushButton()
        self.okBtn.setFixedSize(self.okBtn.sizeHint())
        self.okBtn.setVisible(False)
        buttonsLayout = QtGui.QHBoxLayout()
        buttonsLayout.addStretch(1)
        buttonsLayout.addWidget(self.leaveBtn)
        buttonsLayout.addWidget(self.okBtn)
        buttonsLayout.setContentsMargins(0, 0, 0, 0)

        self.line = QtGui.QFrame()
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setContentsMargins(0, 0, 0, 0)
        self.centralWidget = QtGui.QWidget()
        self.centralWidget.setContentsMargins(0, 0, 0, 0)

        bottomLayout = QtGui.QVBoxLayout()
        bottomLayout.addWidget(self.line, alignment=QtCore.Qt.AlignTop)
        bottomLayout.addLayout(buttonsLayout, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        bottomLayout.setContentsMargins(0, 0, 0, 0)
        bottomLayout.setSpacing(5)
        bottomWidget = QtGui.QWidget()
        bottomWidget.setLayout(bottomLayout)
        bottomWidget.setAutoFillBackground(True)
        bottomWidget.setFixedHeight(39)
        p = bottomWidget.palette()
        p.setColor(bottomWidget.backgroundRole(), QtGui.QColor(242, 243, 246))
        bottomWidget.setPalette(p)

        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.centralWidget)
        mainLayout.addWidget(bottomWidget)
        # for button in HCenter
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        # self.setMinimumSize(bottomLayout.sizeHint())

    def setLeaveBtnText(self, text):
        self.leaveBtn.setText(text)
        self.leaveBtn.setFixedSize(self.leaveBtn.sizeHint())
        self.leaveBtn.setVisible(True)

    def setOkBtnText(self, text):
        self.okBtn.setText(text)
        self.okBtn.setFixedSize(self.okBtn.sizeHint())
        self.okBtn.setVisible(True)

    def setCentralLayout(self, layout):
        self.centralWidget.setLayout(layout)

    def setCentralFixedSize(self, width, height):
        self.centralWidget.setFixedSize(width, height)

    def getScreenGeometry(self):
        return self.deskInfo.screenGeometry()


class ListWidget(QtGui.QListWidget):
    def __init__(self):
        super(ListWidget, self).__init__()
        self.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setStyleSheet('QListWidget::item:selected:active {background-color: #6C9EFF;}'
                           'QListWidget{border: 1px solid #CACACA;}')

    def addStyleSheet(self, sheet=''):
        self.setStyleSheet(self.styleSheet() + sheet)


class ListWidgetWithLine(ListWidget):
    def __init__(self):
        super(ListWidgetWithLine, self).__init__()
        self.addStyleSheet('QListWidget::item{border-bottom: 1px solid #CACACA; padding: 6px 0px 7px 9px;}')

    def addCustomItem(self, text):
        item = QtGui.QListWidgetItem()
        font = item.font()
        font.setPixelSize(12)
        font.setWeight(QtGui.QFont.Light)
        item.setFont(font)
        self.addItem(item)

    def addCustomItems(self, texts):
        for text in texts:
            item = QtGui.QListWidgetItem()
            font = item.font()
            font.setPixelSize(12)
            font.setWeight(QtGui.QFont.Light)
            item.setFont(font)
            item.setText(text)
            self.addItem(item)


class InfoListWidget(ListWidget):
    def __init__(self):
        super(InfoListWidget, self).__init__()
        self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.addStyleSheet('QListWidget::item{padding-bottom: 10px;}'
                           'QListWidget{ padding-left: 9px; background-color: white;}')

    def addInfos(self, infos):
        if 'model' in infos.keys():
            self.addItem(self._createItem('Model:\t' + infos.get('model')))

        if 'serialNo' in infos.keys():
            self.addItem(self._createItem('Serial No.:\t' + infos.get('serialNo')))

        if 'android' in infos.keys():
            self.addItem(self._createItem('Android:\t' + infos.get('android')))

        if 'buildNo' in infos.keys():
            self.addItem(self._createItem('Build No.:\t' + infos.get('buildNo')))

        if 'kernelNo' in infos.keys():
            self.addItem(self._createItem('Kernel No.:\t' + infos.get('kernelNo')))

        if 'resolution' in infos.keys():
            self.addItem(self._createItem('Resolution:\t' + infos.get('resolution')))

        if 'region' in infos.keys():
            self.addItem(self._createItem('Region:\t' + infos.get('region')))

    def _createItem(self, text):
        item = QtGui.QListWidgetItem()
        font = item.font()
        font.setPixelSize(14)
        font.setFmaily(FONT_FAMILY)
        item.setFont(font)
        item.setText(text)
        return item


class PushButton(QtGui.QPushButton):
    def __init__(self, text=None, font_size=None, font_weight=None, text_color=None, rect_color=None):
        super(PushButton, self).__init__()
        self.setStyleSheet('QPushButton{background-color: %s; color: %s;}' % (rect_color, text_color))
        self.pressed.connect(self.press)
        self.released.connect(self.release)
        font = self.font()
        font.setFamily(FONT_FAMILY)
        if font_size:
            font.setPixelSize(font_size)

        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        self.setFont(font)

    def setNormalIcon(self, icon):
        self.normalIcon = icon
        self.setIcon(icon)

    def setPressIcon(self, icon):
        self.pressIcon = icon

    def press(self):
        print 'press'
        if self.pressIcon:
            self.setIcon(self.pressIcon)

    def release(self):
        print 'release'
        if self.normalIcon:
            self.setIcon(self.normalIcon)

class IconButton(QtGui.QToolButton):
    normalIcon = None
    pressIcon = None
    isPress = False

    def __init__(self):
        super(IconButton, self).__init__()
        self.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.setStyleSheet('QToolButton{background-color: transparent;}')
        self.setIconSize(QtCore.QSize(40, 40))
        self.pressed.connect(self.press)
        self.released.connect(self.release)

    def setNormalIcon(self, icon):
        self.normalIcon = icon
        self.setIcon(icon)

    def setPressIcon(self, icon):
        self.pressIcon = icon

    def press(self):
        print 'press'
        if self.pressIcon:
            self.setIcon(self.pressIcon)

    def release(self):
        print 'release'
        if self.normalIcon:
            self.setIcon(self.normalIcon)

    def leaveEvent(self, event):
        if self.normalIcon:
            self.setIcon(self.normalIcon)

    def enterEvent(self, event):
        if self.pressIcon:
            self.setIcon(self.pressIcon)


class IconWithWordsButton(IconButton):
    def __init__(self, text=None, font_size=None, font_weight=None, text_color=None):
        super(IconWithWordsButton, self).__init__()
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet('QToolButton{background-color: transparent; color: %s}'
                           'QToolButton::menu-indicator { image: none; }' % text_color)
        font = self.font()
        font.setFamily(FONT_FAMILY)
        if font_size:
            font.setPixelSize(font_size)

        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        self.setFont(font)


class TitleButton(QtGui.QPushButton):
    def __init__(self, text=None, font_size=None, text_color=None, rect_color=None):
        super(TitleButton, self).__init__()
        font = self.font()
        font.setFamily(FONT_FAMILY)

        if font_size:
            font.setPixelSize(font_size)

        if text:
            self.setText(text)

        if text_color:
            self.textColor = text_color

        if rect_color:
            self.rectColor = rect_color

        self.setFont(font)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            self.drawRect(qp, self.rectColor)
            self.drawText(qp, self.textColor)
            if not self.isEnabled():
                self.drawBottomLine(qp, 4, QtGui.QColor('#6C9EFF'))

        finally:
            qp.end()

    def drawRect(self, qp, color):
        qp.setPen(QtGui.QColor(color))
        qp.setBrush(QtGui.QColor(color))
        qp.drawRect(self.rect())

    def drawText(self, qp, color):
        qp.setPen(QtGui.QColor(color))
        font = QtGui.QFont(self.font().family(), self.font().pixelSize())
        fm = QtGui.QFontMetrics(font)
        qp.setFont(font)
        qp.drawText(self.rect().center().x() - fm.width(self.text()) / 2,
                    self.rect().center().y() + fm.height() / 2,
                    self.text())

    def drawBottomLine(self, qp, width, color):
        pen = QtGui.QPen()
        pen.setWidth(width)
        pen.setBrush(color)
        qp.setPen(pen)
        qp.drawLine(self.rect().bottomLeft(), self.rect().bottomRight())


class MainTitleButton(TitleButton):
    def __init__(self, text=None, font_size=None, text_color=None, rect_color=None):
        super(MainTitleButton, self).__init__(text, font_size, text_color, rect_color)

        self.disableTextColor = '#404040'

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            self.drawRect(qp, self.rectColor)

            if not self.isEnabled():
                self.drawText(qp, self.textColor)
                self.drawBottomLine(qp, 4, QtGui.QColor('#6C9EFF'))
            else:
                self.drawText(qp, self.disableTextColor)
        finally:
            qp.end()


class SettingIconButton(IconWithWordsButton):
    def __init__(self, text=None, font_size=None, color=None):
        super(SettingIconButton, self).__init__()

        if font_size:
            font = self.font()
            font.setPixelSize(font_size)
            self.setFont(font)

        if text:
            self.setText(text)

        if color:
            self.color = color

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            self.drawPixmap(qp)
            self.drawText(qp)
            if not self.isEnabled():
                self.drawPie(qp)
        finally:
            qp.end()

    def drawText(self, qp):
        qp.setPen(self.color)
        font = QtGui.QFont(self.font().family(), self.font().pixelSize())
        fm = QtGui.QFontMetrics(font)
        qp.setFont(font)
        qp.drawText(self.rect().center().x() - fm.width(self.text()) / 2, self.rect().bottom() - 30, self.text())

    def drawPixmap(self, qp):
        pix = self.icon().pixmap(30, 30)
        qp.drawPixmap(self.rect().center().x() - 15, self.rect().top() + 20, pix)

    def drawPie(self, qp):
        qp.setBrush(QtGui.QColor.fromRgb(108, 158, 255))
        qp.setPen(QtGui.QColor.fromRgb(108, 158, 255))
        rectangle = QtCore.QRect(self.rect().center().x() - 8, self.rect().bottom() - 8, 16.0, 16.0)
        startAngle = 0 * 16
        spanAngle = 180 * 16
        qp.drawPie(rectangle, startAngle, spanAngle)


class MyGroup(QtGui.QGroupBox):
    def __init__(self, text=None, font_size=None):
        super(MyGroup, self).__init__()
        # self.setAutoFillBackground(True)
        self.setFlat(True)
        if text:
            self.setTitle(text)
        if font_size:
            self.setTextSize(font_size)

    def setTextSize(self, size):
        font = self.font()
        font.setPixelSize(size)
        self.setFont(font)


class MyCheckBox(QtGui.QCheckBox):
    identity = None
    onStateChanged = QtCore.Signal(str, bool)

    def __init__(self, text=None, font_weight=None, font_size=None, identity=None, color=None):
        super(MyCheckBox, self).__init__()
        self.stateChanged.connect(self.changedState)
        self.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        font = self.font()
        font.setFamily('Open Sans')

        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        if font_size:
            font.setPixelSize(font_size)

        if identity:
            self.identity = identity

        if color:

        self.setFont(font)

    def changedState(self, state):
        self.onStateChanged.emit(self.identity, state)

    def setUncheckedIcon(self, icon):
        self.setIcon(icon)

    def setColor(self, color):
        self.setStyleSheet('QCheckBox{Checkcolor: %s;}' % color)

class MyLabel(QtGui.QLabel):
    def __init__(self, text=None, font_weight=None, font_size=None, color=None):
        super(MyLabel, self).__init__()
        font = self.font()
        font.setFamily('Open Sans')
        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        if font_size:
            font.setPixelSize(font_size)

        if color:
            self.setColor(color)

        self.setFont(font)

    def setColor(self, color):
        self.setStyleSheet('color: %s;' % color)


class MyLineEdit(QtGui.QLineEdit):
    def __init__(self, text=None, font_weight=None, font_size=None):
        super(MyLineEdit, self).__init__()
        self.setStyleSheet('color: #6C9EFF')
        self.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        font = self.font()
        font.setFamily('Open Sans')
        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        if font_size:
            font.setPixelSize(font_size)

        self.setFont(font)

    def setId(self, identity):
        self.identity = identity


class SearchBox(QtGui.QLineEdit):
    def __init__(self):
        super(SearchBox, self).__init__()
        self.button = QtGui.QToolButton(self)
        self.button.setIcon(QtGui.QIcon(folder.get_current_dir(__file__) + '/icon/ic_search.png'))
        self.button.setStyleSheet('border: 0px; padding: 3px 0px 3px 8px;')
        # self.button.setCursor(QtCore.Qt.ArrowCursor)
        # self.button.clicked.connect(self.buttonClicked.emit)

        frameWidth = self.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        buttonSize = self.button.sizeHint()

        self.setStyleSheet('padding-left: %spx; border-radius: 10px; border: 1px solid #979797;' %
                           str(buttonSize.width() + frameWidth + 1))
        self.setMinimumSize(max(self.minimumSizeHint().width(), buttonSize.width() + frameWidth * 2 + 2),
                            max(self.minimumSizeHint().height(), buttonSize.height() + frameWidth * 2 + 2))

        self.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)


class NotifyThread(QtCore.QThread):
    oo = QtCore.Signal()
    isStop = False

    def __init__(self):
        super(NotifyThread, self).__init__()

    def stop(self):
        self.isStop = True

    def run(self):
        self.isStop = False
        while not self.isStop:
            self.msleep(150)
            self.oo.emit()


class MyProcessingBar(QtGui.QLabel):
    brush = None
    colorList = list()
    scaleList = list()
    currentIndex = 0
    range = 10

    def __init__(self):
        super(MyProcessingBar, self).__init__()
        self.notify = NotifyThread()
        self.notify.oo.connect(self.draw)
        for num in range(self.range):
            self.scaleList.append('stop: %0.01f' % (float(num) / float(self.range)))

    def setMovingColor(self, color, sideColor):
        self.movingColor = color
        self.sideColor = sideColor
        self._arrangeColor()

    def _arrangeColor(self):
        for num in range(self.range):
            if num == self.currentIndex:
                self.colorList.append('%s' % self.movingColor)
            else:
                self.colorList.append('%s' % self.sideColor)

    def draw(self):
        sheet = self.styleSheet()
        if len(sheet) == 0:
            newSheet = 'background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,'
        else:
            newSheet = sheet[0:sheet.find('stop')]

        for num in range(self.range):
            if num == self.range - 1:
                newSheet += '%s %s);' % (self.scaleList[num], self.colorList[num])
            else:
                newSheet += '%s %s,' % (self.scaleList[num], self.colorList[num])

        self.setStyleSheet(newSheet)
        self.moveColorIndex()

    def moveColorIndex(self):
        mainColor = self.colorList.pop(self.currentIndex)
        self.currentIndex += 1
        if self.currentIndex < len(self.colorList):
            self.colorList.insert(self.currentIndex, mainColor)
        else:
            self.scaleList.reverse()
            self.currentIndex = 0
            self.colorList.insert(self.currentIndex, mainColor)

    def start(self):
        self.notify.start()

    def stop(self):
        self.notify.stop()
        while not self.notify.isFinished():
            pass


class BaseListView(QtGui.QListWidget):
    def __init__(self):
        super(BaseListView, self).__init__()
        self.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.setSelectionMode(QtGui.QAbstractItemView.NoSelection)

    def addStyleSheet(self, styleSheet=''):
        self.setStyleSheet(self.styleSheet() + styleSheet)

    def getModelIndex(self, row):
        return self.indexFromItem(self.item(row))

    def addCustomItem(self, index, item):
        listItem = QtGui.QListWidgetItem()
        listItem.setSizeHint(item.sizeHint())
        self.insertItem(index, listItem)
        self.setItemWidget(listItem, item)

    def setActiveColor(self, color):
        self.setStyleSheet(self.styleSheet() + 'BaseListView::item:selected:active {background: %s;}' % color)

    def getInsertRow(self):
        selectedItems = self.selectedItems()
        if len(selectedItems) == 1:
            return self.row(selectedItems[0])
        else:
            return self.count()


class TestPlanListItem(HContainer):
    def __init__(self, text=None):
        super(TestPlanListItem, self).__init__()
        self.label = MyCheckBox(text, font_size=12, color='#FFFFFF')
        self.label.setFixedHeight(30)
        self.mLayout.addWidget(self.label)
        self.setContentsMargins(36, 0, 0, 0)

    def text(self):
        return self.label.text()


class TestPlanListView(BaseListView):
    def __init__(self, active_color=None):
        super(TestPlanListView, self).__init__()
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.addStyleSheet('TestPlanListView::item{border-bottom: 1px solid #181818; }'
                           'TestPlanListView{background-color: transparent;}')
        if active_color:
            self.setActiveColor(active_color)

    def haveItem(self, text):
        for num in range(self.count()):
            widget = self.itemWidget(self.item(num))
            if widget.text() == text:
                return True

        return False


class ActionListItem(HContainer):
    def __init__(self, i, text):
        super(ActionListItem, self).__init__()
        self.indexLabel = MyLabel('%d' % i, font_size=12, color='#A0A0A0')
        self.contentLabel = MyLabel('%s' % text, font_size=12, color='#FFFFFF')
        self.indexLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.indexLabel.setFixedSize(36, 30)
        self.contentLabel.setFixedHeight(30)
        self.mLayout.addWidget(self.indexLabel)
        self.mLayout.addWidget(self.contentLabel)
        self.mLayout.addStretch(1)
        self.mLayout.setSpacing(24)
        self.setContentsMargins(0, 0, 0, 0)
        self.setBottomLine(True, '#333333')

    def setIndex(self, index):
        self.indexLabel.setText('%d' % index)

    def setContent(self, content):
        self.contentLabel.setText('%s' % content)


class ActionListView(BaseListView):
    def __init__(self, active_color=None):
        super(ActionListView, self).__init__()
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.addStyleSheet('ActionListView::item{border-bottom: 1px solid #181818; }'
                           'ActionListView{background-color: transparent;}')
        if active_color:
            self.setActiveColor(active_color)

    def addCustomItem(self, index, content):
        actionListItem = ActionListItem(index + 1, content)
        item = QtGui.QListWidgetItem()
        item.setSizeHint(actionListItem.sizeHint())
        self.insertItem(index, item)
        self.setItemWidget(item, actionListItem)


class DescriptionEdit(QtGui.QPlainTextEdit):

    focusIn = QtCore.Signal()
    focusOut = QtCore.Signal()

    def __init__(self):
        super(DescriptionEdit, self).__init__()
        self.setStyleSheet('DescriptionEdit{border: 1px solid #404040; background-color: transparent; '
                           'color: #FFFFFF}')
        font = self.font()
        font.setFamily(FONT_FAMILY)
        font.setPixelSize(10)
        self.setFont(font)

    def focusInEvent(self, event):
        self.focusIn.emit()

    def focusOutEvent(self, event):
        self.focusOut.emit()


class BottomLineWidget(HContainer):
    def __init__(self):
        super(BottomLineWidget, self).__init__()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            self.drawBottomLine(qp, 1, QtGui.QColor('#333333'))
        finally:
            qp.end()

    def drawBottomLine(self, qp, width, color):
        pen = QtGui.QPen()
        pen.setWidth(width)
        pen.setBrush(color)
        qp.setPen(pen)
        qp.drawLine(self.rect().bottomLeft(), self.rect().bottomRight())


class PictureLabel(QtGui.QLabel):
    mouseClick = QtCore.Signal(QtCore.QPoint)
    mouseLongClick = QtCore.Signal(QtCore.QPoint, int)
    mouseSwipe = QtCore.Signal(QtCore.QPoint, QtCore.QPoint, int)
    mouseDrag = QtCore.Signal(QtCore.QPoint, QtCore.QPoint, int)
    checkClick = QtCore.Signal(QtCore.QPoint, str)
    checkRelativeClick = QtCore.Signal(QtCore.QPoint, QtCore.QPoint)
    dragFrom = None
    dragTo = None
    refPoint = None
    isRelease = True
    isStartLoad = True
    isMouseIgnored = False
    isDrawGrid = True
    isDrawRelativeGrid = False
    check_type = None
    viewHierarchy = None
    rects = []
    image = QtGui.QImage()

    def __init__(self, parent=None, currentPath=None):
        super(PictureLabel, self).__init__(parent)
        self.picPath = currentPath

    def setPicScale(self, ratio):
        self.ratio = ratio

    def setMouseIgnore(self, value):
        self.isMouseIgnored = value

    def mousePressEvent(self, event):
        print 'mousePressEvent'
        self.isRelease = False
        self.presstime = time.time()
        self.dragFrom = event.pos()
        self.dragTo = self.dragFrom

    def mouseReleaseEvent(self, event):
        print 'mouseReleaseEvent'
        self.isRelease = True
        if not self.isMouseIgnored:
            self.dragTo = event.pos()
            elapse_time = int((time.time() - self.presstime) * 1000)
            if self.dragFrom == self.dragTo:
                if elapse_time < 300:
                    self.mouseClick.emit(self.dragTo)
                else:
                    self.mouseLongClick.emit(self.dragTo, elapse_time)
            else:
                if elapse_time < 500:
                    self.mouseSwipe.emit(self.dragFrom, self.dragTo, elapse_time)
                else:
                    self.mouseDrag.emit(self.dragFrom, self.dragTo, elapse_time)

            self.update()
        elif self.isDrawGrid:
            self.dragTo = event.pos()
            if self.dragFrom == self.dragTo:
                if not self.isDrawRelativeGrid:
                    self.checkClick.emit(self.dragTo, self.check_type)
                else:
                    self.isDrawRelativeGrid = False
                    self.checkRelativeClick.emit(self.refPoint, self.dragTo)

    def redrawLine(self, dragFrom, dragTo):
        self.dragFrom = dragFrom
        self.dragTo = dragTo
        self.update()

    def redrawPoint(self, point):
        self.dragFrom = point
        self.dragTo = self.dragFrom
        self.update()

    def doneDrawGrid(self):
        self.isDrawGrid = False

    def set_check_type(self, set_type):
        self.check_type = set_type

    def drawGrid(self, view_hierarchy, set_type):
        self.isDrawGrid = True
        self.set_check_type(set_type)
        root = ET.fromstring(view_hierarchy)
        del self.rects[:]
        for node in root.iter('node'):
            output = re.match('\[(?P<x1>[\d]+),(?P<x2>[\d]+)\]\[(?P<y1>[\d]+),(?P<y2>[\d]+)\]', node.get('bounds'))
            x1 = int(output.group('x1'))
            x2 = int(output.group('x2'))
            y1 = int(output.group('y1'))
            y2 = int(output.group('y2'))
            item = dict()
            item['width'] = y1 - x1
            item['height'] = y2 - x2
            item['point'] = QtCore.QPoint(x1, x2)
            self.rects.append(item)
        self.update()

    def drawRelativeGrid(self, view_hierarchy, point):
        print 'draw_relative_grid' + str(point.x()) + ', ' + str(point.y())
        self.isDrawRelativeGrid = True
        self.refPoint = point
        root = ET.fromstring(view_hierarchy)
        del self.rects[:]
        for node in root.iter('node'):
            output = re.match('\[(?P<x1>[\d]+),(?P<x2>[\d]+)\]\[(?P<y1>[\d]+),(?P<y2>[\d]+)\]', node.get('bounds'))
            x1 = int(output.group('x1'))
            x2 = int(output.group('x2'))
            y1 = int(output.group('y1'))
            y2 = int(output.group('y2'))
            if x1 <= point.x() <= point.y():
                item = dict()
                item['width'] = y1 - x1
                item['height'] = y2 - x2
                item['point'] = QtCore.QPoint(x1, x2)
                self.rects.append(item)

        self.update()

    def paintEvent(self, event):
        if self.pixmap() is not None:
            qp = QtGui.QPainter()
            qp.begin(self)
            try:
                tmp = QtGui.QImage(self.picPath)
                if not tmp.isNull():
                    self.image = tmp
                self.drawBackground(self.image, qp)
                if self.isDrawGrid:
                    for rect in self.rects:
                        self.drawRect(rect['point'], qp, w=rect['width'], h=rect['height'], isRealSize=True)
                else:
                    if self.isRelease:
                        if self.dragFrom == self.dragTo:
                            self.drawRect(self.dragTo, qp, isRealSize=False)
                        else:
                            self.drawLine(qp, self.dragFrom, self.dragTo)
            finally:
                qp.end()

    def drawRect(self, point, qp, w=None, h=None, isRealSize=False):
        if point:
            pen = QtGui.QPen()
            pen.setWidth(1.5)
            pen.setBrush(QtCore.Qt.yellow)
            qp.setPen(pen)
            if w == None or h == None:
                if isRealSize:
                    qp.drawRect(point.x() * self.ratio, point.y() * self.ratio, 5, 5)
                else:
                    qp.drawRect(point.x(), point.y(), 5, 5)
            else:
                if isRealSize:
                    qp.drawRect(point.x() * self.ratio, point.y() * self.ratio, w * self.ratio, h * self.ratio)
                else:
                    qp.drawRect(point.x(), point.y(), w, h)

    def drawBackground(self, image, qp):
        if image:
            w = image.size().width() * self.ratio
            h = image.size().height() * self.ratio
            im = image.scaled(w, h)
            qp.drawImage(0, 0, im)

    def drawLine(self, qp, start, end):
        if start and end:
            pen = QtGui.QPen()
            pen.setWidth(2)
            pen.setBrush(QtCore.Qt.red)
            qp.setPen(pen)
            qp.drawLine(start, end)


class DelayDialog(QtGui.QDialog):

    def __init__(self):
        super(DelayDialog, self).__init__()
        self.setWindowTitle('Delay')
        layout = QtGui.QVBoxLayout(self)
        inputLabel = MyLabel('Input delay time (sec.)')

        self.inputEdit = QtGui.QLineEdit(self)
        self.inputEdit.setInputMask('0000000')
        self.inputEdit.setAlignment(QtCore.Qt.AlignCenter)
        # OK and Cancel views
        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)

        layout.addWidget(inputLabel)
        layout.addWidget(self.inputEdit)
        layout.addWidget(buttons)

    def getInputDelay(self):
        return self.inputEdit.text()

    @staticmethod
    def getDelay():
        window = DelayDialog()
        result = window.exec_()
        return window.getInputDelay(), result


class MediaCheckDialog(QtGui.QDialog):

    def __init__(self):
        super(MediaCheckDialog, self).__init__()
        self.setWindowTitle('Media check')
        layout = QtGui.QVBoxLayout(self)
        self.edit1 = QtGui.QLineEdit()
        self.edit1.setInputMask('0000000')
        self.edit1.setAlignment(QtCore.Qt.AlignCenter)
        self.edit2 = QtGui.QLineEdit()
        self.edit2.setInputMask('0000000')
        self.edit2.setAlignment(QtCore.Qt.AlignCenter)
        self.label1 = MyLabel('test-time(sec.):')
        self.label2 = MyLabel('timeout(sec.):')

        layout.addWidget(self.label1)
        layout.addWidget(self.edit1, 0, 1)
        layout.addWidget(self.label2)
        layout.addWidget(self.edit2, 1, 1)
        layout.addStretch(1)
        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setMinimumSize(200, 200)

    def getTestTime(self):
        return self.edit1.text()

    def getTimeout(self):
        return self.edit2.text()

    @staticmethod
    def getCheckTime():
        window = MediaCheckDialog()
        result = window.exec_()
        return window.getTestTime(), window.getTimeout(), result