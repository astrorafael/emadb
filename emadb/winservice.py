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
from server          import Lazy
from emadbserver import EMADBServer
import cmdline

class WindowsService(win32serviceutil.ServiceFramework, Lazy):
	"""
	Windows service that launches several Internet monitoring tasks in background.
	"""
	_svc_name_            = "emadb"
	_svc_display_name_ = "emadb - EMA database"
	_svc_description_    = "An MQTT Client for EMA weather stations that stores data into a SQLite database"

	
	def __init__(self, args):
		logger.sysLogInfo("Starting %s as a Windows service" % default.VERSION_STRING)
		win32serviceutil.ServiceFramework.__init__(self, args)
		Lazy.__init__(self,1)
		self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
		self.server = EMADBServer(cmdline.parser().parse_args(args=args))
		self.server.addLazy(self)

		
	def work(self):
		"""Process Windows events and raises except if STOP SERVICE event is detected"""
		# Wait for service stop signal for that given amount of time
		rc = win32event.WaitForSingleObject(self.hWaitStop,  1*1000 )
		# Check to see if self.hWaitStop happened
		if rc == win32event.WAIT_OBJECT_0:
			# Stop signal encountered
			logger.sysLogInfo("%s  - STOPPED" % self._svc_name_)
			raise IOError(errno.EINTR,"Interrupted system call from Windows")
	
	def SvcStop(self):
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		win32event.SetEvent(self.hWaitStop)
		self.logger.warn("Stopping  emadb service")
		logger.sysLogInfo("%s  - STOPPED" % self._svc_name_)
	
	def SvcDoRun(self):
		servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,servicemanager.PYS_SERVICE_STARTED,(self._svc_name_, '')) 
		servicemanager.LogInfoMsg("RAFA RUN")
		while True:
			self.work()
		server.run()    # Looping  until exception is caught
		server.stop()
		
			
def ctrlHandler(ctrlType):
	return True

if not servicemanager.RunningAsService():	
	win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
	win32serviceutil.HandleCommandLine(WindowsService)
