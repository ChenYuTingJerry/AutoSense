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


class AutoSenseItem(object):
    def __init__(self, content=None):
        self.senseDict = {INDEX: '',
                          ACTION: '',
                          PARAMETER: '',
                          DESCRIPTION: '',
                          INFORMATION: ''}

        if content:
            self.analysis(content)

    def analysis(self, content):
        self.setIndex(content[INDEX])
        self.setAction(content[ACTION])
        self.setAnnotation(content[DESCRIPTION])
        self.setInformation(content[INFORMATION], encode=False)
        self.setParameter(content[PARAMETER])

    def setIndex(self, value):
        self.senseDict[INDEX] = str(value)

    def setAction(self, value):
        self.senseDict[ACTION] = value

    def setParameter(self, value):
        # for saving parameter
        if type(value) == list:
            self.senseDict[PARAMETER] = ','.join(map(unicode, value))
        # for loading parameter
        elif value != '' and value[0] == '[':
            self.senseDict[PARAMETER] = value.strip('[\[\]]')
        else:
            self.senseDict[PARAMETER] = value

    def setAnnotation(self, value):
        self.senseDict[DESCRIPTION] = value

    def setInformation(self, value, encode=True):
        if value:
            if encode:
                self.senseDict[INFORMATION] = base64.b64encode(value)
            else:
                self.senseDict[INFORMATION] = value
        else:
            self.senseDict[INFORMATION] = ''

    def index(self):
        return self.senseDict[INDEX]

    def action(self):
        return self.senseDict[ACTION]

    def parameter(self):
        if self.senseDict[PARAMETER].find(',') != -1:
            return self.senseDict[PARAMETER].strip('[\[\]]').split(',')
        else:
            if len(self.senseDict[PARAMETER]) > 0:
                return [self.senseDict[PARAMETER].strip('[\[\]]')]
            else:
                return ''

    def annotation(self):
        return self.senseDict[DESCRIPTION]

    def informationIn64(self):
        return self.senseDict[INFORMATION]

    def information(self):
        return base64.b64decode(self.senseDict[INFORMATION])

    def inDict(self):
        tmp = self.senseDict.copy()
        tmp[PARAMETER] = '[' + tmp[PARAMETER] + ']'
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
