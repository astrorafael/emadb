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
import logging
import argparse

from logger      import logToConsole, logToFile
from default     import VERSION, VERSION_STRING, CONFIGFILE
from emadbserver import EMADBServer

def parser():
    '''Create the command line interface options'''
    _parser = argparse.ArgumentParser(prog='emadb')
    _parser.add_argument('--version', action='version', version='%s' % VERSION_STRING)
    _parser.add_argument('-l' , '--log-file', type=str, action='store', metavar='<log file>', help='log to file')
    _parser.add_argument('-k' , '--console', action='store_true', help='log to console')
    _parser.add_argument('-s' , '--by-size', action='store_true', help='rotate log by size. If no set, rotate every midnight')

    _parser.add_argument('-m' , '--max-size', type=int , default=1000000, help='logfile max size when rotating by size')

    _parser.add_argument('-c' , '--config', type=str, action='store', metavar='<config file>', help='detailed configuration file')
    return _parser


opts = parser().parse_args()
if opts.console:
    logToConsole()
    
if opts.log_file:
    logToFile(opts.log_file, opts.by_size, opts.max_size)


logging.getLogger().info("Starting %s" % VERSION_STRING)
server = EMADBServer(opts.config or CONFIGFILE)
server.run()    # Looping  until exception is caught
server.stop()
