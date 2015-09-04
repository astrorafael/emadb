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

from  abc import ABCMeta, abstractmethod

from . import Server

class Alarmable(object):
   '''
   Superclass for all objects implementing a OnTimeoutDo() method
   to be used within the select() system call when this system call times out.
   Efficient but not accurate implememtation valid for a few seconds 
   '''

   __metaclass__ = ABCMeta     # Only Python 2.7

   def __init__(self, timeout=1.0):
      self.__count = 0
      self.__limit = int(round(timeout/Server.TIMEOUT))

   def resetAlarm(self):
      self.__count = 0

   def setTimeout(self, timeout):
      self.__limit = int(round(timeout/Server.TIMEOUT))

   def timeout(self):
      '''
      Increments counter modulo N.
      Returns True if counter wraps around.
      '''
      self.__count = (self.__count + 1) % self.__limit
      return  (self.__count == 0)

   @abstractmethod
   def onTimeoutDo(self):
      '''
      To be subclassed and overriden
      '''
      pass

# =============================================================================

class Alarmable2(object):
   '''
   Abstract class for all objects implementing a OnTimeoutDo() method
   to be used within the select() system call when this system call times out.
   Accurate implememtation valid for sevtral hours using timestamps. 
   '''

   __metaclass__ = ABCMeta     # Only Python 2.7

   def __init__(self, timeout=1):
      self.__delta   = datetime.timedelta(seconds=timeout)
      self.__tsFinal = datetime.datetime.utcnow() + self.__delta

   def resetAlarm(self):
      self.__tsFinal    = datetime.datetime.utcnow() + self.__delta

   def setTimeout(self, timeout):
      self.__delta = datetime.timedelta(seconds=timeout)

   def timeout(self):
      '''
      Returns True if timeout elapsed.
      '''
      return datetime.datetime.utcnow() >= self.__tsFinal   

   @abstractmethod
   def onTimeoutDo(self):
      '''
      To be subclassed and overriden
      '''
      pass
