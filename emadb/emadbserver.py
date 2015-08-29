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

# Only Python 2
import ConfigParser as parser


log = logging.getLogger('emadb')

class EMADBServer(server.Server):
        
    def __init__(self, configfile=None):
        if not (configfile != None and os.path.exists(configfile)):
            log.error("No configuration is given. Exiting ...")
            return
        log.info("Loading configuration from %s" % configfile)

        server.Server.__init__(self)
        self.__queue = {
            'minmax':  [] ,
            'status':  [] ,
            'samples': [] ,
        }
        self.__stopped = False
        self.__configfile = configfile
        self.__parser = parser.ConfigParser()
        self.__parser.optionxform = str
        self.__parser.read(configfile)
        log.setLevel(self.__parser.get("GENERIC", "generic_log"))
        self.hold(self.__parser.getboolean("GENERIC", "on_hold"))
        # DBWritter object 
        self.dbwritter = dbwritter.DBWritter(self, self.__parser)
        # MQTT Driver object 
        self.mqttclient = mqttclient.MQTTClient(self, self.__parser)

    def reload(self):
        '''To be called *only* on SIGHUP or similar reload method'''
        log.info("=======================")
        log.info("RELOADING CONFIGURATION")
        log.info("=======================")
        self.__parser.read(self.__configfile)
        log.setLevel(self.__parser.get("GENERIC", "generic_log"))
        self.hold(self.__parser.getboolean("GENERIC", "on_hold"))
        self.mqttclient.reload()
        self.dbwritter.reload()
        log.info("===============")
        log.info("RELOAD COMPLETE")
        log.info("===============")


    # --------------
    # Queue Handing
    # -------------

    def hold(self, stopped):
        '''Stop/Resume enqueing messages from the queue'''
        log.info("on hold = %s", stopped)
        if self.__stopped and not stopped:
            log.info("flushing queues")
            self.flush()
        self.__stopped = stopped


    def flush(self):
        '''Flushes queues, sending messages to destination'''
        while len(self.__queue['minmax']):
            item = self.__queue['minmax'].pop(0)
            self.dbwritter.processMinMax(item[0], item[1])
        while len(self.__queue['status']):
            item = self.__queue['status'].pop(0)
            self.dbwritter.processStatus(item[0], item[1])
        while len(self.__queue['samples']):
            item = self.__queue['samples'].pop(0)
            self.dbwritter.processSamples(item[0], item[1])

    def onMinMaxMessage(self, mqtt_id, payload):
        self.__queue['minmax'].append((mqtt_id, payload))
        if self.__stopped:
            log.warning("Holding %d minmax messages on queue",
                        len(self.__queue['minmax']))
            return
        while len(self.__queue['minmax']):
            item = self.__queue['minmax'].pop(0)
            self.dbwritter.processMinMax(item[0], item[1])

    def onStatusMessage(self, mqtt_id, payload):
        self.__queue['status'].append((mqtt_id, payload))
        if self.__stopped:
            log.warning("Holding %d status messages on queue",
                        len(self.__queue['status']))
            return
        while len(self.__queue['status']):
            item = self.__queue['status'].pop(0)
            self.dbwritter.processStatus(item[0], item[1])

    def onSamplesMessage(self, mqtt_id, payload):
        self.__queue['samples'].append((mqtt_id, payload))
        if self.__stopped:
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

if __name__ == "__main__":
    import logger
    logger.logToConsole()
    server = EMADBServer('../config')
    server.run()
    server.stop()

