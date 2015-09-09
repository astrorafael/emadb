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

# ========================== DESIGN NOTES ==============================
#
# This object is the global server implementing the EMA DB service
#
# ======================================================================

import logging
import server
import mqttclient
import dbwritter
import os
import errno
import sys

from server      import Server, logToFile, logToConsole
from default     import VERSION_STRING, CONFIG_FILE

# Only Python 2
import ConfigParser


log = logging.getLogger('emadb')


class EMADBServer(Server):
        
    def __init__(self, options, **kargs):
        self.parseCmdLine(options)
        server.Server.__init__(self, **kargs)
        self.__queue = {
            'minmax':  [] ,
            'status':  [] ,
            'samples': [] ,
        }
        self.__parser = ConfigParser.ConfigParser()
        self.__parser.optionxform = str
        self.__parser.read(self.__cfgfile)
        self.parseConfigFile()
        
        # DBWritter object 
        self.dbwritter = dbwritter.DBWritter(self, self.__parser)
        # MQTT Driver object 
        self.mqttclient = mqttclient.MQTTClient(self, self.__parser)


    def parseCmdLine(self, opts):
        '''Parses the comand line looking for the config file path 
        and optionally console output'''
        if opts.console:
            logToConsole()
        self.__cfgfile = opts.config or CONFIG_FILE
        if not (os.path.exists(self.__cfgfile)):
            log.error("No configuration file found: %s", self.__cfgfile)
            raise IOError(errno.ENOENT,"No such file or directory ",
                          self.__cfgfile)


    def parseConfigFile(self):
        '''Parses the config file looking for its own options'''
        log.setLevel(self.__parser.get("GENERIC", "generic_log"))
        toFile = self.__parser.getboolean("GENERIC","log_to_file")
        if(toFile):
            filename = self.__parser.get("GENERIC","log_file")
            policy = self.__parser.get("GENERIC","log_policy")
            max_size = self.__parser.getint("GENERIC","log_max_size")
            by_size = policy == "size" if True else False
            logToFile(filename, by_size, max_size)

        logging.getLogger().info("Starting %s, %s",
                                 VERSION_STRING, self.FLAVOUR)
        log.info("Loaded configuration from %s", self.__cfgfile)


    def reload(self):
        '''To be called *only* on SIGHUP or similar reload method'''
        log.info("=======================")
        log.info("RELOADING CONFIGURATION")
        log.info("=======================")
        self.__parser.read(self.__cfgfile)
        log.setLevel(self.__parser.get("GENERIC", "generic_log"))
        self.mqttclient.reload()
        self.dbwritter.reload()
        log.info("===============")
        log.info("RELOAD COMPLETE")
        log.info("===============")


    def pause(self):
        '''
        Pauses the server 
        '''
        log.info("on hold = %s", self.paused)
 
    def resume(self):
        '''
        Resumes the server 
        '''
        log.info("on hold = %s", self.paused)
        self.flush()
 
      
    # --------------
    # Queue Handing
    # -------------

    def flush(self):
        '''Flushes queues, sending messages to destination'''
        while len(self.__queue['minmax']):
            item = self.__queue['minmax'].pop(0)
            self.dbwritter.processMinMax(item[0], item[1])
        while len(self.__queue['status']):
            item = self.__queue['status'].pop(0)
            self.dbwritter.processCurrentStatus(item[0], item[1], item[2])
        while len(self.__queue['samples']):
            item = self.__queue['samples'].pop(0)
            self.dbwritter.processSamples(item[0], item[1])

    def onMinMaxMessage(self, mqtt_id, payload):
        self.__queue['minmax'].append((mqtt_id, payload))
        if self.paused:
            log.warning("Holding %d minmax messages on queue",
                        len(self.__queue['minmax']))
            return
        while len(self.__queue['minmax']):
            item = self.__queue['minmax'].pop(0)
            self.dbwritter.processMinMax(item[0], item[1])

    def onCurrentStatusMessage(self, mqtt_id, payload, recv_tstamp):
        self.__queue['status'].append((mqtt_id, payload, recv_tstamp))
        if self.paused:
            log.warning("Holding %d status messages on queue",
                        len(self.__queue['status']))
            return
        while len(self.__queue['status']):
            item = self.__queue['status'].pop(0)
            self.dbwritter.processCurrentStatus(item[0], item[1], item[2])

    def onSamplesMessage(self, mqtt_id, payload):
        self.__queue['samples'].append((mqtt_id, payload))
        if self.paused:
            log.warning("Holding %d sample messages on queue", 
                        len(self._queue['samples']))
            return
        while len(self.__queue['samples']):
            item = self.__queue['samples'].pop(0)
            self.dbwritter.processSamples(item[0], item[1])
                
    # --------------
    # Server Control
    # --------------

    def stop(self):
        log.info("Shutting down EMA server")
        logging.shutdown()



