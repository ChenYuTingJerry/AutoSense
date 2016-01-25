import sys
import os
from os.path import dirname


def get_current_dir(file_name):
    # determine if application is a script file or frozen exe
    application_path = None
    if getattr(sys, 'frozen', False):
        application_path = dirname(sys.executable)
    elif __file__:
        application_path = dirname(dirname(os.path.abspath(file_name)))
    return application_path
