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


# ========================== DESIGN NOTES ==============================
# Rsposibilities:
# 1) To create the root logger object, at initialization time
# 2) to create a console formatter and a file formatter
# to be used as options when the server is started
# 3) Add a verbose log level method on the fly
#
# ======================================================================

import logging
import os

from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

sysLogInfo = None
sysLogError = None

if os.name == "nt":
	import servicemanager
	sysLogInfo = servicemanager.LogInfoMsg
	sysLogError = servicemanager.LogErrorMsg
else:
	import syslog
	sysLogInfo = syslog.syslog
	sysLogError = syslog.syslog

	
# ----------------------
# Adding a VERBOSE Level
# ----------------------

# Register new level
VERBOSE = 5
logging.addLevelName(VERBOSE,"VERBOSE")

# Add new method to logging.Logger class on the fly
def verbose(self, *opts):
    self.log(VERBOSE, *opts)
logging.Logger.verbose = verbose

# ------------
# File formats
# ------------

CONSOLE_FORMAT = '[%(levelname)7s] %(name)9s - %(message)s'
FILE_FORMAT    = '%(asctime)s [%(levelname)7s] - %(name)9s %(message)s'

ROOT = logging.getLogger()
ROOT.setLevel(logging.INFO)

# ------------------
# Exported Functions
# ------------------

def logToConsole():
    formatter = logging.Formatter(fmt=CONSOLE_FORMAT)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    ROOT.addHandler(consoleHandler)


def logToFile(filename, by_size, max_size):
    formatter   = logging.Formatter(fmt=FILE_FORMAT)
    if by_size:
        fileHandler = RotatingFileHandler(filename,
                                          maxBytes=max_size,
                                          backupCount=7)
    else:
        # daily rotation at midnight, keep 7 backups
        fileHandler = TimedRotatingFileHandler(filename,
                                           when='midnight',
                                           interval=1,
                                           backupCount=7)
    fileHandler.setFormatter(formatter)
    ROOT.addHandler(fileHandler)

