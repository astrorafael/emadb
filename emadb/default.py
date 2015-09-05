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
import os.path
import sys

# Default config constants for the EMA Client (command line interface)
# and Server
VERSION = '0.1.0'
VERSION_STRING = "emadb/%s/Python %d.%d" % (VERSION, 
                                         sys.version_info.major, 
                                         sys.version_info.minor)


# Default config file path
if os.name == "nt":
    CONFIG_FILE=os.path.join("C:\\", "emadb", "config", "config.ini")
else:
    CONFIG_FILE="/etc/emadb/config"


# Global Log Level for the Root Logger in EMA Client.
# Note that individual module log levels are handled in config file 
# Allowed Values => ("CRITICAL", ERROR", "WARN", "INFO", "DEBUG")
LOGLEVEL="ERROR"



