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
# The Lazy class is meant to be subclassed and contains all the logic
# to handle a cyclic counter. When this counter reaches 0 it triggers
# a callback.


from   abc import ABCMeta, abstractmethod

from . import Server 

class Lazy(object):
   '''
   Abstract class for all objects implementing a work() method
   to be used within the select() system call 
   when this system call times out.
   '''

   __metaclass__ = ABCMeta     # Only Python 2.7

   def __init__(self, period=1.0):
      self.__count = 0
      self.__limit = int(round(period/Server.TIMEOUT))


   def reset(self):
      self.__count = 0


   def setPeriod(self, period):
      self.__limit = int(round(period/Server.TIMEOUT))


   def mustWork(self):
      '''
      Increments counter modulo N.
      Returns True if counter wraps around.
      '''
      self.__count = (self.__count + 1) % self.__limit
      return  (self.__count == 0)

   @abstractmethod
   def work(self):
      '''
      Work procedure for lazy objects.
      To be subclassed and overriden
      '''
      pass

