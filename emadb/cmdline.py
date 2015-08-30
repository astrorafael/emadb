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
import logger

import default

def parser():
    '''Create the command line interface parser'''
    _parser = argparse.ArgumentParser(prog='emadb')
    _parser.add_argument('--version', action='version', version='%s' % default.VERSION_STRING)
    _parser.add_argument('-k' , '--console', action='store_true', help='log to console')
    _parser.add_argument('-f' , '--foreground', action='store_true', help='run in foreground (Windows only)')
    _parser.add_argument('-c' , '--config', type=str, action='store', metavar='<config file>', help='detailed configuration file')
    group = _parser.add_mutually_exclusive_group()
    group.add_argument(' install',  type=str, nargs='?', help='install windows service')
    group.add_argument(' start',  type=str, nargs='?', help='start windows service')
    group.add_argument(' stop',  type=str, nargs='?', help='start windows service')
    group.add_argument(' remove',  type=str, nargs='?', help='remove windows service')
    
    return _parser
