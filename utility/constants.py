import directory as folder
import os


class Global(object):
    print 'Global = ' + __file__
    ROOT_FOLDER = os.path.expanduser("~") + '/.autosense'
    RES_FOLDER = folder.get_current_dir(__file__) + '/res'
    FONT_FOLDER = RES_FOLDER + '/font'
    ICON_FOLDER = folder.get_current_dir(__file__) + '/icon'
    PRIVATE_FOLDER = ROOT_FOLDER + '/_data'
    LOG_FOLDER = folder.get_current_dir(__file__) + '/log'
    SOUND_FOLDER = folder.get_current_dir(__file__) + '/sound'
    APK_FOLDER = folder.get_current_dir(__file__) + '/apk'
    IMAGE_FOLDER = ROOT_FOLDER + '/image'
    SCRIPT_FOLDER = ROOT_FOLDER + '/script'
    FONT_FAMILY = 'Open Sans'


class Setting(object):

    WIFI = 'wifi'
    NFC = 'nfc'
    BLUETOOTH = 'bt'
    AIRPLANE = 'airplane'
    DATA_ROAMING = 'data_roaming'
    GPS = 'gps'
    AUTO_ROTATE = 'auto_rotate'
    AUTO_BRIGHTNESS = 'auto_brightness'
    BRIGHTNESS_SET = 'brightness_set'
    ALLOW_APP = 'allow_app'
    NO_KEEP_ACTIVITY = 'no_keep_activity'
    VIBRATE = 'vibrate'
    KEEP_WIFI = 'keep_wifi'
    WINDOW_ANIMATOR = 'window_animator'
    TRANSITION_ANIMATOR = 'transition_animator'
    DURATION_ANIMATION = 'duration_animation'


class UiCheck(object):
    IS_EXIST = 'Exist'
    NO_EXIST = 'NoExist'
    IS_BLANK = 'IsBlank'
    IS_RELATIVE_EXIST = 'RelativeExist'


class JudgeState(object):
    PASS = 0
    FAIL = -1
    SEMI = 1
    NORMAL = 2


class Sense(object):
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

