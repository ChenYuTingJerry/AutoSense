from PySide import QtGui, QtCore
from main import constants
import xml.etree.ElementTree as ET
import directory as folder
import time
import sys
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


class IntroWindow(QtGui.QDialog):
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
        self.leaveBtn.setFocus(QtCore.Qt.TabFocusReason)
        self.leaveBtn.setFixedSize(self.leaveBtn.sizeHint())
        self.leaveBtn.setVisible(True)

    def setOkBtnText(self, text):
        self.okBtn.setText(text)
        self.okBtn.setFocus(QtCore.Qt.TabFocusReason)
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
        font.setFamily(constants.FONT_FAMILY)
        item.setFont(font)
        item.setText(text)
        return item


class PushButton(QtGui.QPushButton):
    pressIcon = None
    normalIcon = None

    def __init__(self, text=None, font_size=None, font_weight=None, text_color=None, rect_color=None):
        super(PushButton, self).__init__()
        self.setStyleSheet('QPushButton{background-color: %s; color: %s;}' % (rect_color, text_color))
        self.pressed.connect(self.press)
        self.released.connect(self.release)
        font = self.font()
        font.setFamily(constants.FONT_FAMILY)
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
        if self.pressIcon:
            self.setIcon(self.pressIcon)

    def release(self):
        if self.normalIcon:
            self.setIcon(self.normalIcon)


class IconButton(QtGui.QToolButton):
    normalIcon = None
    pressIcon = None
    isPress = False
    ignoreMouse = False

    def __init__(self):
        super(IconButton, self).__init__()
        self.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.setStyleSheet('IconButton{background-color: transparent;}')
        self.setIconSize(QtCore.QSize(40, 40))
        self.pressed.connect(self.press)
        self.released.connect(self.release)

    def setNormalIcon(self, icon):
        self.normalIcon = icon
        self.setIcon(icon)

    def setPressIcon(self, icon):
        self.pressIcon = icon

    def press(self):
        if self.pressIcon:
            self.setIcon(self.pressIcon)

    def release(self):
        if self.normalIcon:
            self.setIcon(self.normalIcon)

    def setIgnoreMouse(self, status):
        self.ignoreMouse = status

    def leaveEvent(self, event):
        if self.normalIcon and not self.ignoreMouse:
            self.setIcon(self.normalIcon)

    def enterEvent(self, event):
        if self.pressIcon and not self.ignoreMouse:
            self.setIcon(self.pressIcon)


class IconWithWordsButton(IconButton):
    def __init__(self, text=None, font_size=None, font_weight=None, text_color=None):
        super(IconWithWordsButton, self).__init__()
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet('IconWithWordsButton{background-color: transparent; color: %s}'
                           'IconWithWordsButton::menu-indicator { image: none; }' % text_color)
        font = self.font()
        font.setFamily(constants.FONT_FAMILY)
        if font_size:
            font.setPixelSize(font_size)

        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        self.setFont(font)


class MenuButton(IconButton):
    def __init__(self, text=None, font_size=None, font_weight=None, text_color=None):
        super(MenuButton, self).__init__()
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet('MenuButton{background-color: transparent; color: %s}' % text_color)

        font = self.font()
        font.setFamily(constants.FONT_FAMILY)
        if font_size:
            font.setPixelSize(font_size)

        if text:
            self.setText(text)

        if font_weight:
            font.setWeight(font_weight)

        self.setFont(font)

    def setMenuIndicator(self, normalPic, pressPic=None):
        self.setStyleSheet(self.styleSheet() + 'MenuButton::menu-indicator { image: url(%s);}' % normalPic)
        if pressPic:
            self.setStyleSheet(self.styleSheet() + 'MenuButton::menu-indicator:open { image: url(%s);}' % pressPic)


class TitleButton(QtGui.QPushButton):
    rectColor = None
    textColor = None

    def __init__(self, text=None, font_size=None, text_color=None, rect_color=None):
        super(TitleButton, self).__init__()
        font = self.font()
        font.setFamily(constants.FONT_FAMILY)

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
            if self.rectColor:
                self.drawRect(qp, self.rectColor)
            if self.textColor:
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


class MyButton(QtGui.QToolButton):
    def __init__(self, text, font_size=None, font_color=None):
        super(MyButton, self).__init__()
        self.setStyleSheet('MyButton{background-color: transparent; border: 1px solid #A0A0A0;'
                           'border-radius: 12px; height: 24px; width: 80px}')
        font = self.font()
        font.setFamily('Open Sans')
        if text:
            self.setText(text)

        if font_size:
            font.setPixelSize(font_size)

        if font_color:
            self.setColor(font_color)

        self.setFont(font)

    def setColor(self, color):
        self.setStyleSheet(self.styleSheet() + 'MyButton{color: %s;}' % color)


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

    def __init__(self, text=None, font_weight=None, font_size=None, identity=None):
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

        self.setFont(font)

    def changedState(self, state):
        self.onStateChanged.emit(self.identity, state)

    def setUncheckedIcon(self, imageName):
        self.setStyleSheet(self.styleSheet() + ' QCheckBox::indicator:unchecked {image: url('
                                               '%s);}' % imageName)

    def setHoverIcon(self, imageName):
        self.setStyleSheet(self.styleSheet() + ' QCheckBox::indicator:unchecked:hover {image: url('
                                               '%s);}' % imageName)

    def setCheckedIcon(self, imageName):
        self.setStyleSheet(self.styleSheet() + ' QCheckBox::indicator:checked {image: url('
                                               '%s);}' % imageName)


class MyProgressBar(QtGui.QProgressBar):
    def __init__(self):
        super(MyProgressBar, self).__init__()
        self.setStyleSheet('QProgressBar{background-color: #2D2D2D; '
                           'color: transparent; border: 2px solid #181818; border-radius: 3px; height: 8px}'
                           'QProgressBar::chunk{background-color: #6C9EFF;}')


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
        self.setStyleSheet(self.styleSheet() + 'color: %s;' % color)

    def setBoader(self, color):
        self.setStyleSheet(self.styleSheet() + 'border: 1px solid %s;' % color)


class MyLineEdit(QtGui.QLineEdit):
    def __init__(self, text=None, font_weight=None, font_size=None, color=None):
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

        if color:
            self.setColor(color)

        self.setFont(font)

    def setId(self, identity):
        self.identity = identity

    def setColor(self, color):
        self.setStyleSheet('color: %s' % color)


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
        self.setStyleSheet(
            '''
        QScrollBar {background: transparent; width: 10px; height: 10px}
        QScrollBar::add-line, QScrollBar::sub-line{ background: transparent;}
        QScrollBar::add-page, QScrollBar::sub-page{ background: transparent;}
        QScrollBar::handle {background: #282828; border: 5px solid #282828; border-radius: 5px;}
        ''')

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

    def firstSelectedRow(self):
        row = sys.maxint
        selectedItems = self.selectedItems()
        for item in selectedItems:
            if self.row(item) < row:
                row = self.row(item)

        if row == sys.maxint:
            return -1
        else:
            return row

    def itemByItemWidget(self, itemWidget):
        for num in range(self.count()):
            tempItem = self.item(num)
            if itemWidget == self.itemWidget(tempItem):
                return tempItem
        return None

    def itemWidgetByRow(self, row):
        return self.itemWidget(self.item(row))


class MenuListView(BaseListView):
    itemDelete = QtCore.Signal(int, QtGui.QListWidgetItem, QtGui.QWidget)

    def __init__(self, active_color=None):
        super(MenuListView, self).__init__()
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menuOpen)
        self.addStyleSheet('MenuListView::item{border-bottom: 1px solid #181818; }'
                           'MenuListView{background-color: transparent;}')
        if active_color:
            self.setActiveColor(active_color)

    def haveItem(self, text):
        for num in range(self.count()):
            widget = self.itemWidget(self.item(num))
            if widget.planName() == text:
                return True
        return False

    def menuOpen(self, pos):
        listItem = self.itemAt(pos)
        if listItem:
            row = self.row(listItem)
            self.setCurrentRow(row)
            menu = QtGui.QMenu()
            deleteAct = menu.addAction("Delete\t")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == deleteAct:
                listItemWidget = self.itemWidget(listItem)
                self.itemDelete.emit(row, self.takeItem(row), listItemWidget)


class TestPlanListItem(HContainer):
    def __init__(self, planItem):
        super(TestPlanListItem, self).__init__()
        self.planItem = planItem
        self.checkWidget = VContainer()
        self.checkWidget.setFixedSize(30, 30)
        self.label = MyLabel(self.planItem.planName(), font_size=12, color='#FFFFFF')
        self.label.setFixedHeight(30)
        self.addWidget(self.checkWidget)
        self.addWidget(self.label)
        self.setContentsMargins(0, 0, 0, 0)

    def planName(self):
        return self.planItem.planName()

    def createTime(self):
        return self.planItem.createTime()

    def index(self):
        return self.planItem.index()

    def actions(self):
        return self.planItem.actions()

    def text(self):
        return self.label.text()


class TestPlanListView(MenuListView):
    def __init__(self, active_color=None):
        super(TestPlanListView, self).__init__(active_color)


class PlayQueueListItem(HContainer):
    def __init__(self, playItem=None):
        super(PlayQueueListItem, self).__init__()
        self.playItem = playItem
        self.box = MyCheckBox()
        self.box.setUncheckedIcon(constants.ICON_FOLDER + '/ic_add to q_normal.png')
        self.box.setCheckedIcon(constants.ICON_FOLDER + '/ic_confirm add to quene.png')
        self.box.setHoverIcon(constants.ICON_FOLDER + '/ic_add to q_press.png')
        self.box.onStateChanged.connect(self.onStateChange)

        self.checkWidget = VContainer()
        self.checkWidget.addWidget(self.box)
        self.checkWidget.setFixedSize(30, 30)
        showText = '%s (%d to %d, %d)' % (self.playItem.playName(),
                                          self.playItem.range()[0],
                                          self.playItem.range()[1],
                                          self.playItem.repeat())
        self.label = MyLabel(showText, font_size=12, color='#4F4F4F')
        self.label.setFixedHeight(30)
        self.addWidget(self.checkWidget)
        self.addWidget(self.label)
        self.setContentsMargins(0, 0, 0, 0)

        self.box.setChecked(True)

    def text(self):
        return self.label.text()

    def isChecked(self):
        return self.box.isChecked()

    def setCheckBoxVisible(self, status):
        if status:
            if not self.box.isChecked():
                self.label.setColor('#4F4F4F')
        else:
            self.label.setColor('#FFFFFF')

    def actions(self):
        return self.playItem.actions()

    def playName(self):
        return self.playItem.playName()

    def range(self):
        return self.playItem.range()

    def repeat(self):
        return self.playItem.repeat()

    def actionsCount(self):
        return len(self.playItem.actions())

    def onStateChange(self, identify, status):
        if status:
            self.label.setColor('#FFFFFF')
        else:
            self.label.setColor('#4F4F4F')


class PlayQueueListView(MenuListView):
    def __init__(self, active_color=None):
        super(PlayQueueListView, self).__init__(active_color)


class ActionListItem(HContainer):
    def __init__(self, autoSenseItem, index):
        super(ActionListItem, self).__init__()
        self.autoSenseItem = autoSenseItem
        self.autoSenseItem.setIndex(index)
        action = self.autoSenseItem.action()
        if self.autoSenseItem.parameter():
            action += ' [ ' + ','.join(str(p) for p in self.autoSenseItem.parameter()) + ' ]'
        self.iconLabel = IconButton()
        self.iconLabel.setIconSize(QtCore.QSize(30, 30))
        self.iconLabel.setFixedSize(QtCore.QSize(30, 30))
        self.indexLabel = MyLabel('%s' % self.autoSenseItem.index(), font_size=12, color='#A0A0A0')
        self.contentLabel = MyLabel('%s' % action, font_size=12, color='#FFFFFF')
        self.indexLabel.setFixedSize(30, 30)
        self.contentLabel.setFixedHeight(30)
        self.addWidget(self.iconLabel)
        self.addWidget(self.indexLabel)
        self.addWidget(self.contentLabel)
        self.addStretch(1)
        self.setContentsMargins(0, 0, 0, 0)
        self.setBottomLine(True, '#333333')

    def action(self):
        return self.autoSenseItem.action()

    def index(self):
        return self.autoSenseItem.index()

    def setIndex(self, index):
        self.indexLabel.setText('%d' % index)

    def setContent(self, content):
        self.contentLabel.setText('%s' % content)

    def setSignal(self, icon):
        self.iconLabel.setIcon(icon)

    def tested(self):
        return self.autoSenseItem.tested()

    def text(self):
        return self.contentLabel.text()

    def setTested(self, state):
        self.autoSenseItem.setTested(state)


class ActionListView(MenuListView):
    takeItemsDone = QtCore.Signal(list)

    def __init__(self, active_color=None):
        super(ActionListView, self).__init__(active_color)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

    def menuOpen(self, pos):
        listItem = self.itemAt(pos)
        if listItem:
            menu = QtGui.QMenu()
            deleteAct = menu.addAction("Delete\t")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == deleteAct:
                deletedList = list()
                for item in self.selectedItems():
                    temp = dict()
                    listItemWidget = self.itemWidget(item)
                    index = self.row(item)
                    temp['row'] = index
                    temp['take_item'] = self.takeItem(index)
                    temp['item_widget'] = listItemWidget
                    deletedList.append(temp)
                deletedList.reverse()
                self.takeItemsDone.emit(deletedList)


class MyPlainTextEdit(QtGui.QPlainTextEdit):
    focusIn = QtCore.Signal()
    focusOut = QtCore.Signal()

    def __init__(self, font_color=None, text=None, font_size=None):
        super(MyPlainTextEdit, self).__init__()
        self.setStyleSheet('MyPlainTextEdit{border: 1px solid #404040; background-color: transparent;}')
        font = self.font()
        font.setFamily(constants.FONT_FAMILY)
        if font_size:
            font.setPixelSize(font_size)

        if text:
            self.setPlainText(text)

        if font_color:
            self.setColor(font_color)

        self.setFont(font)

    def focusInEvent(self, event):
        self.focusIn.emit()

    def focusOutEvent(self, event):
        self.focusOut.emit()

    def setColor(self, color):
        self.setStyleSheet(self.styleSheet() + 'MyPlainTextEdit{color: %s;}' % color)


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


class DonutPie(QtGui.QLabel):
    _radius = 0
    _thickness = 0
    _color = None
    _second_color = None
    _span_angle = 0
    _start_angle = 0

    def __init__(self, radius=None, thickness=None, color=None, second_color=None):
        super(DonutPie, self).__init__()
        if radius:
            self.setRadius(radius)

        if thickness:
            self._thickness = thickness

        if color:
            self._color = color

        if second_color:
            self._second_color = second_color

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        try:
            self.drawRect(qp, '#404040')
            self.drawPie(qp, self._second_color, self._radius, 0, 360)
            self.drawPie(qp, self._color, self._radius, self._start_angle, self._span_angle)
            self.drawPie(qp, '#181818', self._radius - self._thickness, 0, 360)
        finally:
            qp.end()

    def setRadius(self, radius):
        self._radius = radius

    def setThickness(self, thickness):
        self._thickness = thickness

    def setColor(self, color):
        self._color = color

    def setSecondColor(self, color):
        self._second_color = color

    def setStartAngle(self, angle):
        self._start_angle = angle

    def setSpanAngle(self, angle):
        self._span_angle = angle

    def drawPie(self, qp, color, radius, start_angle, span_angle):
        qp.setBrush(QtGui.QColor(color))
        qp.setPen(QtGui.QColor(color))
        rectangle = QtCore.QRect(self.rect().center().x() - radius, self.rect().center().y() - radius,
                                 radius * 2, radius * 2)
        startAngle = start_angle * 16
        spanAngle = span_angle * 16
        qp.drawPie(rectangle, startAngle, spanAngle)

    def drawRect(self, qp, color):
        qp.setPen(QtGui.QColor(color))
        qp.drawRect(0, 9, self.width()-1, self.height()-10)


class PictureLabel(QtGui.QLabel):
    mouseClick = QtCore.Signal(QtCore.QPoint)
    mouseLongClick = QtCore.Signal(QtCore.QPoint, int)
    mouseSwipe = QtCore.Signal(QtCore.QPoint, QtCore.QPoint, int)
    mouseDrag = QtCore.Signal(QtCore.QPoint, QtCore.QPoint, int)
    checkClick = QtCore.Signal(QtCore.QPoint, str)
    checkRelativeClick = QtCore.Signal(QtCore.QPoint)
    checkRelativeDone = QtCore.Signal(QtCore.QPoint, QtCore.QPoint)
    dragFrom = None
    dragTo = None
    isRelease = True
    isStartLoad = True
    isMouseIgnored = False
    isDrawGrid = True
    isDrawRelativeGrid = False
    isSelecting = False
    check_type = None
    viewHierarchy = None
    relativePivot = None
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
                if self.isDrawRelativeGrid:
                    if not self.isSelecting:
                        self.isSelecting = True
                        self.relativePivot = self.dragTo
                        self.checkRelativeClick.emit(self.dragTo)
                    elif self.isClickInRelative(self.dragTo):
                        self.isSelecting = False
                        self.isDrawRelativeGrid = False
                        self.checkRelativeDone.emit(self.relativePivot, self.dragTo)
                else:
                    self.checkClick.emit(self.dragTo, self.check_type)

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
        if set_type == 'RelativeExist':
            self.isDrawRelativeGrid = True
        else:
            self.isDrawGrid = True
        self.check_type = set_type

    def analysisBounds(self, boundsInfo):
        output = re.match('\[(?P<x1>[\d]+),(?P<y1>[\d]+)\]\[(?P<x2>[\d]+),(?P<y2>[\d]+)\]', boundsInfo)
        x1 = int(output.group('x1'))
        y1 = int(output.group('y1'))
        x2 = int(output.group('x2'))
        y2 = int(output.group('y2'))
        item = dict()
        item['width'] = x2 - x1
        item['height'] = y2 - y1
        item['point'] = QtCore.QPoint(x1, y1)
        item['point_end'] = QtCore.QPoint(x2, y2)
        return item

    def drawGrid(self, view_hierarchy, set_type):
        self.set_check_type(set_type)
        self.root = ET.fromstring(view_hierarchy)
        del self.rects[:]
        for node in self.root.iter('node'):
            self.rects.append(self.analysisBounds(node.get('bounds')))
        self.update()

    def isClickInRelative(self, point):
        for rect in self.rects:
            print rect
            if rect['point'].x() <= point.x() / self.ratio <= rect['point_end'].x():
                if rect['point'].y() <= point.y() / self.ratio <= rect['point_end'].y():
                    return True
        return False

    def drawRelativeGrid(self, boundsInfo):
        targetItem = self.analysisBounds(boundsInfo)
        del self.rects[:]
        for node in self.root.iter('node'):
            item = self.analysisBounds(node.get('bounds'))
            if self.isRelativeView(targetItem, item):
                self.rects.append(item)
        self.update()

    def isRelativeView(self, origin, relative):
        if relative['point_end'].x() <= origin['point'].x():
            if origin['point'].y() <= relative['point'].y() <= origin['point_end'].y():
                if origin['point'].y() <= relative['point_end'].y() <= origin['point_end'].y():
                    return True

        if relative['point_end'].x() >= origin['point'].x():
            if origin['point'].y() <= relative['point'].y() <= origin['point_end'].y():
                if origin['point'].y() <= relative['point_end'].y() <= origin['point_end'].y():
                    return True

        if relative['point_end'].y() <= origin['point'].y():
            if origin['point'].x() <= relative['point'].x() <= origin['point_end'].x():
                if origin['point'].x() <= relative['point_end'].x() <= origin['point_end'].x():
                    return True

        if relative['point_end'].y() >= origin['point'].y():
            if origin['point'].x() <= relative['point'].x() <= origin['point_end'].x():
                if origin['point'].x() <= relative['point_end'].x() <= origin['point_end'].x():
                    return True

        return False;

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
        self.edit1.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.edit1.setInputMask('0000000')
        self.edit1.setAlignment(QtCore.Qt.AlignCenter)
        self.edit2 = QtGui.QLineEdit()
        self.edit2.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.edit2.setInputMask('0000000')
        self.edit2.setAlignment(QtCore.Qt.AlignCenter)
        self.label1 = MyLabel('test-time(sec.):')
        self.label2 = MyLabel('timeout(sec.):')
        self.checkBox = QtGui.QCheckBox('hold to media finished')

        layout.addWidget(self.label1)
        layout.addWidget(self.edit1, 0, 0)
        layout.addWidget(self.label2)
        layout.addWidget(self.edit2, 1, 0)
        layout.addStretch(1)
        layout.addWidget(self.checkBox, 2, 1)
        buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setMinimumSize(200, 200)

    def getTestTime(self):
        return self.edit1.text()

    def getTimeout(self):
        return self.edit2.text()

    def isChecked(self):
        return self.checkBox.isChecked()

    @staticmethod
    def getCheckTime():
        window = MediaCheckDialog()
        result = window.exec_()
        return window.getTestTime(), window.getTimeout(), window.isChecked(), result
