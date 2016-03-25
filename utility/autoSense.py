# -*- coding: utf-8 -*-
'''
Created on 2015年9月1日

@author: jerrychen
'''
import base64
from constants import Sense, JudgeState as State

class AutoSenseItem(object):
    def __init__(self, content=None):
        self.itemDict = {Sense.INDEX: '',
                         Sense.ACTION: '',
                         Sense.PARAMETER: '',
                         Sense.DESCRIPTION: '',
                         Sense.INFORMATION: '',
                         Sense.TESTED: State.NORMAL}

        if content:
            self.analysis(content)

    def analysis(self, content):
        self.setIndex(content[Sense.INDEX])
        self.setAction(content[Sense.ACTION])
        self.setAnnotation(content[Sense.DESCRIPTION])
        self.setInformation(content[Sense.INFORMATION], encode=False)
        self.setParameter(content[Sense.PARAMETER])
        # self.setTested(content[TESTED])

    def setIndex(self, value):
        self.itemDict[Sense.INDEX] = str(value)

    def setAction(self, value):
        self.itemDict[Sense.ACTION] = value

    def setParameter(self, value):
        # for saving parameter
        if type(value) == list:
            self.itemDict[Sense.PARAMETER] = ','.join(map(unicode, value))
        # for loading parameter
        elif value != '' and value[0] == '[':
            self.itemDict[Sense.PARAMETER] = value.strip('[\[\]]')
        else:
            self.itemDict[Sense.PARAMETER] = value

    def setAnnotation(self, value):
        self.itemDict[Sense.DESCRIPTION] = value

    def setInformation(self, value, encode=True):
        if value:
            if encode:
                self.itemDict[Sense.INFORMATION] = base64.b64encode(value)
            else:
                self.itemDict[Sense.INFORMATION] = value
        else:
            self.itemDict[Sense.INFORMATION] = ''

    def setTested(self, tested):
        self.itemDict[Sense.TESTED] = tested

    def index(self):
        return self.itemDict[Sense.INDEX]

    def action(self):
        return self.itemDict[Sense.ACTION]

    def parameter(self):
        if self.itemDict[Sense.PARAMETER].find(',') != -1:
            return self.itemDict[Sense.PARAMETER].strip('[\[\]]').split(',')
        else:
            if len(self.itemDict[Sense.PARAMETER]) > 0:
                return [self.itemDict[Sense.PARAMETER].strip('[\[\]]')]
            else:
                return ''

    def annotation(self):
        return self.itemDict[Sense.DESCRIPTION]

    def informationIn64(self):
        return self.itemDict[Sense.INFORMATION]

    def information(self):
        return base64.b64decode(self.itemDict[Sense.INFORMATION])

    def tested(self):
        return self.itemDict.get(Sense.TESTED)

    def inDict(self):
        tmp = self.itemDict.copy()
        tmp[Sense.PARAMETER] = '[' + tmp[Sense.PARAMETER] + ']'
        del tmp[Sense.TESTED]
        return tmp


class ApkItem(object):
    def __init__(self, content=None):
        self.itemDict = {Sense.APK_NAME: '',
                         Sense.VERSION: ''}

        if content: self.analisys(content)

    def analisys(self, content):
        self.setName(content[Sense.APK_NAME])
        self.setVersion(content[Sense.VERSION])
        self.setVersion(content[Sense.PACKAGE_NAME])

    def setName(self, name):
        self.itemDict[Sense.APK_NAME] = name

    def setVersion(self, version):
        if version != '' and version[0] == '[':
            self.itemDict[Sense.VERSION] = version.strip('[\[\]]')
        else:
            self.itemDict[Sense.VERSION] = version

    def setPackageName(self, name):
        self.itemDict[Sense.PACKAGE_NAME] = name

    def name(self):
        return self.itemDict.get(Sense.APK_NAME)

    def version(self):
        return self.itemDict.get(Sense.VERSION).strip('[\[\]]')

    def packageName(self):
        return self.itemDict.get(Sense.PACKAGE_NAME)

    def inDict(self):
        tmp = self.itemDict.copy()
        tmp[Sense.VERSION] = '[' + tmp[Sense.VERSION] + ']'
        return tmp


class PlayItem(object):
    def __init__(self):
        self.itemDict = {Sense.INDEX: -1,
                         Sense.CHECKED: False,
                         Sense.PLAY_NAME: '',
                         Sense.RANGE: [0, 0],
                         Sense.REPEAT: 0,
                         Sense.ACTION: list(),
                         Sense.TESTED: False}

    def setIndex(self, index):
        self.itemDict[Sense.INDEX] = index

    def setChecked(self, checked):
        self.itemDict[Sense.CHECKED] = checked

    def setPlayName(self, text):
        self.itemDict[Sense.PLAY_NAME] = text

    def setRange(self, range):
        self.itemDict[Sense.RANGE] = range

    def setActions(self, actions):
        self.itemDict[Sense.ACTION] = actions

    def setTested(self, tested):
        self.itemDict[Sense.TESTED] = tested

    def setRepeat(self, repeat):
        self.itemDict[Sense.REPEAT] = repeat

    def index(self):
        return self.itemDict.get(Sense.INDEX)

    def repeat(self):
        return self.itemDict.get(Sense.REPEAT)

    def isChecked(self):
        return self.itemDict.get(Sense.CHECKED)

    def playName(self):
        return self.itemDict.get(Sense.PLAY_NAME)

    def actions(self):
        return self.itemDict.get(Sense.ACTION)

    def range(self):
        return self.itemDict.get(Sense.RANGE)

    def tested(self):
        return self.itemDict.get(Sense.TESTED)


class TestPlanItem(object):

    def __init__(self):
        self.itemDict = {Sense.INDEX: '',
                         Sense.PLAN_NAME: '',
                         Sense.ACTION: '',
                         Sense.CREATE_TIME: ''}

    def setIndex(self, index):
        self.itemDict[Sense.INDEX] = index

    def setPlanName(self, text):
        self.itemDict[Sense.PLAN_NAME] = text

    def setActions(self, actions):
        self.itemDict[Sense.ACTION] = actions

    def setCreateTime(self, createTime):
        self.itemDict[Sense.CREATE_TIME] = createTime

    def planName(self):
        return self.itemDict.get(Sense.PLAN_NAME)

    def actions(self):
        return self.itemDict.get(Sense.ACTION)

    def index(self):
        return self.itemDict.get(Sense.INDEX)

    def createTime(self):
        return self.itemDict.get(Sense.CREATE_TIME)


class TestResultItem(object):
    _total = 0
    _passed = 0
    _failed = 0
    _semi = 0
    _pass_ratio = 0
    _fail_ratio = 0
    _semi_ratio = 0

    def __init__(self, testResults):
        self.__calculate__(testResults)

    def __calculate__(self, items):
        self._total = len(items)
        for item in items:
            if item.action() == 'CheckPoint':
                self._semi += 1

            if item.tested() == State.PASS:
                self._passed += 1
            elif item.tested() == State.FAIL:
                self._failed += 1

        self._pass_ratio = self._passed * 100 / self._total
        self._fail_ratio = 100 - self._pass_ratio
        self._semi_ratio = self._semi * 100 / self._total

    def pass_count(self):
        return self._passed

    def fail_count(self):
        return self._failed

    def semi_ratio(self):
        return self._semi_ratio

    def pass_ratio(self):
        return self._pass_ratio

    def fail_ratio(self):
        return self._fail_ratio

    def total_count(self):
        return self._total
