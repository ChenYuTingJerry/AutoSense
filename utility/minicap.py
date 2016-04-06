import binascii
import socket
from PySide.QtCore import QThread, QByteArray


MINICAP_CMD = ['LD_LIBRARY_PATH=/data/local/tmp', '/data/local/tmp/minicap']


class MiniServer(QThread):

    def __init__(self, device):
        super(MiniServer, self).__init__()
        self._device = device
        self._device.cmd.adb(['forward', 'tcp:1717', 'localabstract:minicap'])
        self.__rotate = 0

    def run(self):
        self.__rotate = self.getCurrentRotation()
        if not self.isActive():
            displayInfo = self._device.getCurrDisplay()
            size = str(displayInfo['width']) + 'x' + str(displayInfo['height'])
            param = size + '@' + size + '/0'
            self._device.cmd.shell(MINICAP_CMD + ['-P', param], shell=True)
            print 'kill'

    def isActive(self):
        p = self._device.cmd.popen(['ps'])
        stdout, stderr = p.communicate()
        for line in stdout.split('\r\n'):
            if line.find('/data/local/tmp/minicap')!=-1:
                return True
        return False

    def pid(self):
        p = self._device.cmd.popen(['ps'])
        stdout, stderr = p.communicate()
        for line in stdout.split('\r\n'):
            if line.find('/data/local/tmp/minicap') != -1:
                return line.split()[1]

    def stop(self):
        self._device.cmd.shell(['kill', self.pid()])

    def reStart(self):
        self.stop()
        self.wait()
        self.start()

    def needRestart(self):
        if self.__rotate != self.getCurrentRotation():
            return True
        else:
            return False

    def getCurrentRotation(self):
        return self._device.getCurrDisplay()['orientation']


class MiniReader(object):
    PORT = 1717
    HOST = 'localhost'

    def __init__(self, device):
        self._device = device

    def getDisplay(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.HOST, self.PORT))

        data = s.recv(24)
        print self.parseBanner(data)
        data = s.recv(4)
        size = self.parsePicSize(data)
        print 'size = ' + str(size)
        picData = ''
        while True:
            if size >= 4096:
                data = s.recv(4096)
                picData += data
                size -= len(data)
            elif 0 < size < 4096:
                data = s.recv(size)
                picData += data
                size -= len(data)
            elif size <= 0:
                break
        s.close()
        return picData

    def parsePicSize(self, data):
        return int(binascii.hexlify(data[::-1]), 16)

    def parseBanner(self, data):
        if len(data) == 24:
            banner = dict()
            banner['version'] = int(binascii.hexlify(data[0]), 16)
            banner['length'] = int(binascii.hexlify(data[1]), 16)
            banner['pid'] = int(binascii.hexlify(data[2:5][::-1]), 16)
            banner['real.width'] = int(binascii.hexlify(data[6:9][::-1]), 16)
            banner['real.height'] = int(binascii.hexlify(data[7:13][::-1]), 16)
            banner['virtual.width'] = int(binascii.hexlify(data[14:17][::-1]), 16)
            banner['virtual.height'] = int(binascii.hexlify(data[18:21][::-1]), 16)
            banner['orient'] = int(binascii.hexlify(data[22]), 16)
            banner['policy'] = int(binascii.hexlify(data[23]), 16)
            return banner
