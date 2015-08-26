#!/bin/env python
# -*- coding: utf-8 -*-
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

import sys
import os
import logging
import sqlite3
import emadb.logger
import emadb.schema

emadb.logger.logToConsole()
log = logging.getLogger('schema')
connection = None

if not os.path.exists(sys.argv[1]):
    log.error("No SQLite3 Database file found in %s. Exiting ...",
              sys.argv[1])
    sys.exit(1)
		
try:
    connection = sqlite3.connect(sys.argv[1])
    emadb.schema.generate(connection, 'config', replace=True)

except sqlite3.Error as e:
    if connection:
        connection.rollback()
        log.error("Error %s:", e.args[0])
        sys.exit(1)
finally:
    if connection:
        connection.close() 
