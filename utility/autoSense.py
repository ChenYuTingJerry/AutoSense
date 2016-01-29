# -*- coding: utf-8 -*-
'''
Created on 2015年9月1日

@author: jerrychen
'''
import base64

INDEX = 'index'
ACTION = 'action'
PARAMETER = 'parameter'
DESCRIPTION = 'description'
INFORMATION = 'information'
VERSION = 'version'
APK_NAME = 'apkName'
PACKAGE_NAME = 'packageName'
PLAY_NAME = 'playName'
PLAN_NAME = 'planName'
RANGE = 'range'
CHECKED = 'checked'
TESTED = 'tested'
REPEAT = 'repeat'
CREATE_TIME = 'createTime'


class AutoSenseItem(object):
    def __init__(self, content=None):
        self.itemDict = {INDEX: '',
                         ACTION: '',
                         PARAMETER: '',
                         DESCRIPTION: '',
                         INFORMATION: '',
                         TESTED: 0}

        if content:
            self.analysis(content)

    def analysis(self, content):
        self.setIndex(content[INDEX])
        self.setAction(content[ACTION])
        self.setAnnotation(content[DESCRIPTION])
        self.setInformation(content[INFORMATION], encode=False)
        self.setParameter(content[PARAMETER])

    def setIndex(self, value):
        self.itemDict[INDEX] = str(value)

    def setAction(self, value):
        self.itemDict[ACTION] = value

    def setParameter(self, value):
        # for saving parameter
        if type(value) == list:
            self.itemDict[PARAMETER] = ','.join(map(unicode, value))
        # for loading parameter
        elif value != '' and value[0] == '[':
            self.itemDict[PARAMETER] = value.strip('[\[\]]')
        else:
            self.itemDict[PARAMETER] = value

    def setAnnotation(self, value):
        self.itemDict[DESCRIPTION] = value

    def setInformation(self, value, encode=True):
        if value:
            if encode:
                self.itemDict[INFORMATION] = base64.b64encode(value)
            else:
                self.itemDict[INFORMATION] = value
        else:
            self.itemDict[INFORMATION] = ''

    def setTested(self, tested):
        self.itemDict[TESTED] = tested

    def index(self):
        return self.itemDict[INDEX]

    def action(self):
        return self.itemDict[ACTION]

    def parameter(self):
        if self.itemDict[PARAMETER].find(',') != -1:
            return self.itemDict[PARAMETER].strip('[\[\]]').split(',')
        else:
            if len(self.itemDict[PARAMETER]) > 0:
                return [self.itemDict[PARAMETER].strip('[\[\]]')]
            else:
                return ''

    def annotation(self):
        return self.itemDict[DESCRIPTION]

    def informationIn64(self):
        return self.itemDict[INFORMATION]

    def information(self):
        return base64.b64decode(self.itemDict[INFORMATION])

    def tested(self):
        return self.itemDict.get(TESTED)

    def inDict(self):
        tmp = self.itemDict.copy()
        tmp[PARAMETER] = '[' + tmp[PARAMETER] + ']'
        del tmp[TESTED]
        return tmp


class ApkItem(object):
    def __init__(self, content=None):
        self.itemDict = {APK_NAME: '',
                         VERSION: ''}

        if content: self.analisys(content)

    def analisys(self, content):
        self.setName(content[APK_NAME])
        self.setVersion(content[VERSION])
        self.setVersion(content[PACKAGE_NAME])

    def setName(self, name):
        self.itemDict[APK_NAME] = name

    def setVersion(self, version):
        if version != '' and version[0] == '[':
            self.itemDict[VERSION] = version.strip('[\[\]]')
        else:
            self.itemDict[VERSION] = version

    def setPackageName(self, name):
        self.itemDict[PACKAGE_NAME] = name

    def name(self):
        return self.itemDict.get(APK_NAME)

    def version(self):
        return self.itemDict.get(VERSION).strip('[\[\]]')

    def packageName(self):
        return self.itemDict.get(PACKAGE_NAME)

    def inDict(self):
        tmp = self.itemDict.copy()
        tmp[VERSION] = '[' + tmp[VERSION] + ']'
        return tmp


class PlayItem(object):
    def __init__(self):
        self.itemDict = {INDEX: -1,
                         CHECKED: False,
                         PLAY_NAME: '',
                         RANGE: [0, 0],
                         REPEAT: 0,
                         ACTION: list(),
                         TESTED: False}

    def setIndex(self, index):
        self.itemDict[INDEX] = index

    def setChecked(self, checked):
        self.itemDict[CHECKED] = checked

    def setPlayName(self, text):
        self.itemDict[PLAY_NAME] = text

    def setRange(self, range):
        self.itemDict[RANGE] = range

    def setActions(self, actions):
        self.itemDict[ACTION] = actions

    def setTested(self, tested):
        self.itemDict[TESTED] = tested

    def setRepeat(self, repeat):
        self.itemDict[REPEAT] = repeat

    def index(self):
        return self.itemDict.get(INDEX)

    def repeat(self):
        return self.itemDict.get(REPEAT)

    def isChecked(self):
        return self.itemDict.get(CHECKED)

    def playName(self):
        return self.itemDict.get(PLAY_NAME)

    def actions(self):
        return self.itemDict.get(ACTION)

    def range(self):
        return self.itemDict.get(RANGE)

    def tested(self):
        return self.itemDict.get(TESTED)


class TestPlanItem(object):

    def __init__(self):
        self.itemDict = {INDEX: '',
                         PLAN_NAME: '',
                         ACTION: '',
                         CREATE_TIME: ''}

    def setIndex(self, index):
        self.itemDict[INDEX] = index

    def setPlanName(self, text):
        self.itemDict[PLAN_NAME] = text

    def setActions(self, actions):
        self.itemDict[ACTION] = actions

    def setCreateTime(self, createTime):
        self.itemDict[CREATE_TIME] = createTime

    def planName(self):
        return self.itemDict.get(PLAN_NAME)

    def actions(self):
        return self.itemDict.get(ACTION)

    def index(self):
        return self.itemDict.get(INDEX)

    def createTime(self):
        return self.itemDict.get(CREATE_TIME)
