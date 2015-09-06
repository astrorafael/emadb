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
# This is a tiny aynchronous framework based on the well known select() 
# system call. Not onl it implements input/output activity callbacks but
# also one-shot alarm callbacks and periodic callbacks 
# (aka 'work procedures')
#
# select() timeout vaule is 1 second by default,a value not to coarse
# nor too fine.
#
# I could have made this framework more generic by registering callback 
# functions instead of object instances. Bound methods would work as 
# well, but I have not have the need to use isolated functions.
#
# The Lazy class is meant to be subclassed and contains all the logic
# to handle a cyclic counter. When this counter reaches 0 it triggers
# a callback.
#
# The Alarmable class is meant to be subclassed and contains all the 
# logic to handle a counter and triigering a callback when the counter 
# reaches 0. The Server object automatically unregisters the alarmable 
# object before the callback to ensure that it is never called again.
#
# Time in Lazy and Alarmable objects shoudl be expressed in terms of
# counter cycles, using the Server.TIMEOUT constant as the reference
# like so:   N = int(round(T/Server.TIMEOUT))
#
# We use ABCMeta metaclass and @abstractmethod decorator, to enforce
# enforcing some methods to be implemented in subclasses.
#
# In v2.0, we add a reload method, TBD how to call it from Windows
#
# ======================================================================

import os
import errno
import select
import logging

import win32api
import win32con
import win32event
import win32service

import logger

log = logging.getLogger('server')


class Server(object):

   TIMEOUT = 1
   FLAVOUR = "Windows Service"

   instance = None

   def __init__(self, parent=None, stop_event=None, reload_event=None, 
                pause_event=None, resume_event=None):
      self.__paused = False
      self.__parent = parent
      self.__robj   = []
      self.__wobj   = []
      self.__alobj  = []
      self.__lazy   = []
      self.__events = [
         stop_event   or win32event.CreateEvent(None, 0, 0, None),
         reload_event or win32event.CreateEvent(None, 0, 0, None),
         pause_event  or win32event.CreateEvent(None, 0, 0, None),
         resume_event or win32event.CreateEvent(None, 0, 0, None),
      ]
         
   # -------------------------------
   # Event I/O registering interface
   # -------------------------------

   def addReadable(self, obj):
      '''
      Adds a readable object implementing the following methods:
      fileno()
      onInput()
      '''
      # Returns AttributeError exception if not
      callable(getattr(obj,'fileno'))
      callable(getattr(obj,'onInput'))
      self.__robj.append(obj)


   def delReadable(self, obj):
      '''Removes readable object from the list, 
      thus avoiding onInput() callback'''
      self.__robj.pop(self.__robj.index(obj))


   def addWritable(self, obj):
      '''
      Adds a readable object implementing the following methods:
      fileno()
      onOutput()
      '''
      # Returns AttributeError exception if not
      callable(getattr(obj,'fileno'))
      callable(getattr(obj,'onOutput'))
      self.__robj.append(obj)


   def delWritable(self, obj):
      '''Removes writable object from the list, 
      thus avoiding onOutput() callback'''
      self.__wobj.pop(self.__wobj.index(obj))

   # -------------------------------
   # Alarmable registering interface
   # -------------------------------

   def addAlarmable(self, obj):
      '''
      Adds an object implementing the timeout()and onTimeoutDo() method
      onTimeoutDo() is invoked only once, then it is automatically removed.
      '''

      # Returns AttributeError exception if not
      callable(getattr(obj,'timeout'))
      callable(getattr(obj,'onTimeoutDo'))
      self.__alobj.append(obj)


   def delAlarmable(self, obj):
      '''Removes alarmable object from the list, 
      thus avoiding onTimeoutDo() callback'''
      self.__alobj.pop(self.__alobj.index(obj))


   # --------------------------
   # Lazy registering interface
   # --------------------------

   def addLazy(self, obj):
      '''
      Adds an object implementing the work() and mustWork() methods 
      ( i.e. instances of Lazy).
      '''
      # Returns AttributeError exception if not
      callable(getattr(obj,'work'))
      callable(getattr(obj,'mustWork'))
      self.__lazy.append(obj)
   
   # ---------------------------------------------------
   # Reload interface, triggered by reload cumstom Event
   # ---------------------------------------------------
   
   def reload(self):
      '''
      reloads configuration and reconfigures on-line
      '''
      pass

   # --------------------------------------------------------
   # Pause /resume interface, triggered by SIGUSR1, SUGUSR2
   # --------------------------------------------------------

   @property
   def paused(self):
      return self.__paused

   def pause(self):
      '''
      Pause server activity. To be overriden by child classes
      '''
      pass

   def resume(self):
      '''
      Continue server activity. To be overriden by child classes.
      '''
      pass

   def handlePause(self):
      if self.__paused:
         return
      self.__paused = True
      self.pause()
      if self.__parent:
         self.__parent.ReportServiceStatus(win32service.SERVICE_PAUSED)


   def handleResume(self):
      if not self.__paused:
         return
      self.__paused = False
      self.resume()
      if self.__parent:
         self.__parent.ReportServiceStatus(win32service.SERVICE_RUNNING)

   # ----------------------
   # stop internal interface
   # ----------------------

   def handleStop(self):
      '''The application will call stop upon exiting the main loop'''
      if self.__parent:
         self.__parent.ReportServiceStatus(win32service.SERVICE_STOPPED)
      raise KeyboardInterrupt()


   def stop(self):
      '''
      Performs server clean up activity before exiting.
      To be subclassed if needed
      '''
      pass

   # ---------
   # main loop
   # ---------

   def SetTimeout(self, newT):
      '''Set the select() timeout'''
      Server.TIMEOUT = newT


   def handleWindowsEvents(self, timeout):
      '''Handle windows service events, 
      timeout in milliseconds
      Returns timeout flag'''
      rc = win32event.WaitForMultipleObjects(self.__events, False, timeout)
      if rc == win32event.WAIT_OBJECT_0:
         self.handleStop()
      elif rc == win32event.WAIT_OBJECT_0+1:
         self.reload()
         return False
      elif rc == win32event.WAIT_OBJECT_0+2:
         self.handlePause()
         return False
      elif rc == win32event.WAIT_OBJECT_0+3:
         self.handleResume()
         return False
      elif rc == win32event.WAIT_TIMEOUT:
         return True
      raise WindowsError()
       
       
   def waitForActivity(self, interval):
      '''Wait for activity. Return list of changed objects and
      a next step flag (True = next step is needed)'''
      # This is a Windows specific quirk: It returns error
      # if the select() sets are empty.
      if len(self.__robj) == 0 and len(self.__wobj) == 0:
         return [], [], self.handleWindowsEvents(interval*1000)

      self.handleWindowsEvents(interval*250)
      nread, nwrite, _ = select.select(self.__robj, self.__wobj, [],
                                       interval*0.750)
      return nread, nwrite, True



   def processHandlers( self, nreadables, nwritables):
      '''Invoke activity handlers'''
      io_activity = False 
      if nreadables:
         io_activity = True
         for readable in nreadables:
            readable.onInput()
            
      if nwritables:
         io_activity = True
         for writable in nwritables:
            readable.onOutput()

      if not io_activity:                   
         # Execute alarms first
         utcnow = datetime.datetime.utcnow()
         for alarm in self.__alobj:
            if alarm.timeout(utcnow):
               self.delAlarmable(alarm)
               alarm.onTimeoutDo()

         # Executes recurring work procedures last
         for lazy in self.__lazy:
            if lazy.mustWork():
               lazy.work()


   def step(self, timeout):
      '''
      Single step run, invoking I/O handlers or timeout handlers
      '''
      nr, nw, flag = self.waitForActivity(timeout)
      if flag:
         self.processHandlers(nr, nw)


   def run(self):
      '''
      Endless loop invoking step() until an Exception is caught.
      '''
      while True:
         try:
            self.step(Server.TIMEOUT)
         except KeyboardInterrupt:
            log.warning("Server.run() aborted by user request")
            break
         except Exception as e:
            logger.sysLogError(str(e))
            log.exception(e)
            break
         



