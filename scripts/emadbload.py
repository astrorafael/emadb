#!/usr/bin/env python
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
import argparse
# Only Python 2
import ConfigParser


def parser():
	'''Create the command line interface options'''
	_parser = argparse.ArgumentParser()
	_parser.add_argument('-c', '--config-file', action='store', 
                             metavar='<config file>', 
                             default='/etc/emadb/config', 
                             help='path to emadb configuration file')
	return _parser

# Parse command line options
opt = parser().parse_args()
emadb.logger.logToConsole()
log = logging.getLogger('schema')
log.info("Loaded configuration from %s", opt.config_file)
connection = None

# Reads configuration file
config = ConfigParser.ConfigParser()
config.optionxform = str
config.read(opt.config_file)

dbfile      = config.get("DBASE", "dbase_file")
json_dir    = config.get("DBASE", "dbase_json_dir")
date_fmt    = config.get("DBASE", "dbase_date_fmt")
year_start  = config.getint("DBASE", "dbase_year_start")
year_end    = config.getint("DBASE", "dbase_year_end")

try:
    connection = sqlite3.connect(dbfile)
    emadb.schema.generate(connection, 
                          json_dir, 
                          date_fmt,
                          year_start, 
                          year_end,
                          replace=True)

except sqlite3.Error as e:
    if connection:
        connection.rollback()
        log.error("Error %s:", e.args[0])
        sys.exit(1)
finally:
    if connection:
        connection.close() 
