# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ----------------------------------------------------------------------

import os
import sys
import logging
import argparse
import errno

import win32service
import win32serviceutil
import win32api
import win32con
import win32event
import win32evtlogutil
import servicemanager  

import logger
import default
import cmdline

from server      import Server
from emadbserver import EMADBServer


log = logging.getLogger('winservice')

class WindowsService(win32serviceutil.ServiceFramework):
    """
    Windows service that launches several Internet monitoring tasks in background.
    """
    _svc_name_            = "emadb"
    _svc_display_name_ = "emadb - EMA database"
    _svc_description_    = "An MQTT Client for EMA weather stations that stores data into a SQLite database"

    
    def __init__(self, args):
        logger.sysLogInfo("Starting %s as a Windows service" % default.VERSION_STRING)
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.server = EMADBServer(cmdline.parser().parse_args(args=args))

        
    def SvcStop(self):
        '''Service Stop entry point'''
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        log.warn("Stopping  emadb service")
        logger.sysLogInfo("%s  - STOPPING" % self._svc_name_)

    
    def SvcDoRun(self):
        '''Service Run entry point'''
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, '')) 
        self.server.run()
        self.server.stop()
        
            
def ctrlHandler(ctrlType):
    return True

if not servicemanager.RunningAsService():   
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
    win32serviceutil.HandleCommandLine(WindowsService)
