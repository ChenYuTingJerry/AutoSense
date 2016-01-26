# -*- coding: utf-8 -*-
"""
Created on 2015/12/8

@author: Jerry Chen
"""
import sys
import os
import subprocess
from constants import NFC, WIFI, AIRPLANE, GPS, AUTO_ROTATE, BLUETOOTH, DATA_ROAMING, ALLOW_APP, NO_KEEP_ACTIVITY, \
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



