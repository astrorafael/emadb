# ----------------------------------------------------------------------
# Copyright (c) 2015 Rafael Gonzalez.
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

import win32event
import win32api
import win32con
import win32evtlogutil

import win32serviceutil
import servicemanager  
import win32service

# Custom Widnows service control in the range of [128-255]
SERVICE_CONTROL_RELOAD = 128
SERVICE_NAME = "emadb"

# Get access to the Service Control Manager
hscm = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)

# Open the desired service with
hs = win32serviceutil.SmartOpenService(hscm, SERVICE_NAME, win32service.SERVICE_ALL_ACCESS)

# Send the custom control
win32service.ControlService(hs, SERVICE_CONTROL_RELOAD)

# Close the service (probably not necessary)
win32service.CloseServiceHandle(hs)



    