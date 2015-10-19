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

import win32serviceutil
import win32event
import servicemanager  
import win32api

import win32service
import win32con
import win32evtlogutil


import default
import cmdline

from server      import logger
from emadbserver import EMADBServer
from .     import __version__

log = logging.getLogger('winservice')

# Custom Widnows service control in the range of [128-255]
SERVICE_CONTROL_RELOAD = 128

class WindowsService(win32serviceutil.ServiceFramework):
    """
    Windows service for the EMA database.
    """
    _svc_name_            = "emadb"
    _svc_display_name_    = "EMA database (%s)" % __version__ 
    _svc_description_    = "An MQTT Client for EMA weather stations that stores data into a SQLite database" 

    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop    = win32event.CreateEvent(None, 0, 0, None)
        self.reload  = win32event.CreateEvent(None, 0, 0, None)
        self.pause  = win32event.CreateEvent(None, 0, 0, None)
        self.resume = win32event.CreateEvent(None, 0, 0, None)
        self.server = EMADBServer(cmdline.parser().parse_args(args=args), 
                                  parent=self,
                                  stop_event=self.stop,  
                                  reload_event=self.reload, 
                                  pause_event=self.pause, 
                                  resume_event=self.resume)

    def SvcStop(self):
        '''Service Stop entry point'''
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        log.info("Stopping  %s Windows service", __version__ )
        logger.sysLogInfo("Stopping %s Windows service" % __version__ )
        win32event.SetEvent(self.stop)


    def SvcPause(self):
        '''Service Pause entry point'''
        self.ReportServiceStatus(win32service.SERVICE_PAUSE_PENDING)
        log.info("Pausing  %s Windows service", VERSION_STRING )
        logger.sysLogInfo("Pausing %s Windows service" % __version__ )
        win32event.SetEvent(self.pause)

        
    def SvcContinue(self):
        '''Service Continue entry point'''
        self.ReportServiceStatus(win32service.SERVICE_CONTINUE_PENDING)
        log.info("Resuming  %s Windows service", __version__  )
        logger.sysLogInfo("Resuming %s Windows service" % __version__ )
        win32event.SetEvent(self.resume)

        
    def SvcOtherEx(self, control, event_type, data):
        '''Implements a Reload functionality as a  service custom control'''
        if control == SERVICE_CONTROL_RELOAD:
            self.SvcDoReload()
        else:
            self.SvcOther(control)
            

    def SvcDoReload(self):
        logger.sysLogInfo("reloading emadb service")
        win32event.SetEvent(self.reload)


    def SvcDoRun(self):
        '''Service Run entry point'''
        logger.sysLogInfo("Starting %s Windows service" % __version__ )
        self.server.run()
        self.server.stop()
        logger.sysLogInfo("%s Windows service stopped" % __version__ )

    
def ctrlHandler(ctrlType):
    return True

if not servicemanager.RunningAsService():   
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
    win32serviceutil.HandleCommandLine(WindowsService)
