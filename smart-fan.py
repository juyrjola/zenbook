#!/usr/bin/env python

import os
import re
import subprocess
import time
import atexit

TEMP_BASE = '/sys/devices/virtual/hwmon'
FAN_CONTROL = '/usr/local/bin/asus-fanctrl'

POLL_INTERVAL = 2000
TEMP_MAX = 77
TEMP_MIN = 39

class TempController(object):
    last_fan_setting = -1
    last_temp = -1

    def set_fan(self, val):
        fan_max = 255
        arg = val * 255 / 100
        if arg < 1:
            arg = 1
        args = (FAN_CONTROL, '%d' % arg)
        subprocess.check_call(args)

    def scan_sensors(self):
        self.temp_sensor_files = []
        for dirpath, dirnames, fnames in os.walk(TEMP_BASE):
            for fn in fnames:
                if re.match(r'temp[\d]+_input', fn):
                    self.temp_sensor_files.append(os.path.join(dirpath, fn))

        if not self.temp_sensor_files:
            raise Exception("No temperature sensors found!")

    def process_temps(self):
        max_temp = max([int(open(fn).read()) for fn in self.temp_sensor_files])
        if max_temp < 1000:
            raise Exception("Temperature too low (%d)" % max_temp)
        max_temp = max_temp / 1000
        if self.last_temp >= 0:
            # If the temperature is going down, react to it slower
            if max_temp < self.last_temp:
                temp = (self.last_temp * 9 + max_temp) / 10.0
            else:
                temp = (self.last_temp * 3 + max_temp) / 4.0
        else:
            temp = max_temp
        self.last_temp = temp
        print "Current temp %.2f" % temp
        if temp < TEMP_MIN:
            fan_setting = 0
        elif temp >= TEMP_MAX or max_temp >= TEMP_MAX:
            fan_setting = 100
        else:
            perc = (float(temp) - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)
            perc = perc * perc
            fan_setting = perc * 100

        if self.last_fan_setting != fan_setting:
            diff = fan_setting - self.last_fan_setting
            print "Setting fan to %d %%" % fan_setting
            self.set_fan(fan_setting)
            self.last_fan_setting = fan_setting

ctrl = TempController()
ctrl.scan_sensors()

def handle_exit():
    ctrl.set_fan(100)
atexit.register(handle_exit)

while True:
    ctrl.process_temps()
    time.sleep(POLL_INTERVAL / 1000.0)
