from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove, system
import os
from datetime import datetime as dt
from datetime import timedelta
file_path='./root/settings.py'
managePyLocation = 'C:\\wageup\\wageup_repo\\back_new\\root\\manage.py'


def setDebug(value):
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                if 'DEBUG = ' in line:
                    new_file.write('DEBUG = ' + str(value)  + '\n')
                else:
                    new_file.write(line)
    copymode(file_path, abs_path)
    remove(file_path)
    move(abs_path, file_path)

if __name__ == '__main__':
    setDebug('True')