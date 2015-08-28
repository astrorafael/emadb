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
# A MQTT class implementing a subscriber MQTT client for EMA data
# No disconnection requests are ever made.
#
# This class inherits from Lazy to periodically execute a work() procedure
# responsible for:
# 1. Managing connection to MQTT Broker
# 2. Managing subscriptions.
# 
# The work() procedure executes twice as fast as the keepalive 
# timeout specidied to the client MQTT library.
#
# ======================================================================

import logging
import paho.mqtt.client as mqtt
import socket


from server import Lazy, Server
import utils

# MQTT Connection Status
NOT_CONNECTED = 0
CONNECTING    = 1
CONNECTED     = 2
FAILED        = 3
DISCONNECTING = 4
	
log = logging.getLogger('mqtt')


# Callback when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
   userdata.on_connect(flags, rc)

def on_disconnect(client, userdata, rc):
   userdata.on_disconnect(rc)

# Callback when a PUBLISH message is received from the server.
# The default message callback
def on_message(client, userdata, msg):
    userdata.on_message(msg)

# Callback subscriptions
def on_subscribe(client, userdata, mid, granted_qos):
    userdata.on_subscribe(mid, granted_qos)

def on_unsubscribe(client, userdata, mid):
    userdata.on_unsubscribe(mid)

class MQTTClient(Lazy):

   QoS = 1                      # Accept duplicate messages

   def __init__(self, ema, parser):
      Lazy.__init__(self, 60)
      self.__parser   = parser
      self.ema        = ema
      self.__state    = NOT_CONNECTED
      ema.addLazy(self)
      # We do not allow to reconfigure an existing connection
      # to a broker as we would loose incoming data
      self.__id       = parser.get("MQTT", "mqtt_id")
      self.__host     = parser.get("MQTT", "mqtt_host")
      self.__port     = parser.getint("MQTT", "mqtt_port")
      self.__mqtt     =  mqtt.Client(client_id=self.__id+'@'+ socket.gethostname(), userdata=self)
      self.__mqtt.on_connect     = on_connect
      self.__mqtt.on_disconnect  = on_disconnect
      self.__mqtt.on_message     = on_message
      self.__mqtt.on_subscribe   = on_subscribe
      self.__mqtt.on_unsubscribe = on_unsubscribe
      self.reload()
      log.info("MQTT client created")

      # we only allow to reconfigure the topic list and keepalive period
   def reload(self):
      '''Reloads and reconfigures itself'''
      parser = self.__parser    # shortcut
      lvl             = parser.get("MQTT", "mqtt_log")
      log.setLevel(lvl)
      self.__period   = parser.getint("MQTT", "mqtt_period")
      topics          = utils.chop(parser.get("MQTT", "mqtt_topics"),',')
      self.__topics   = [ (topic, MQTTClient.QoS) for topic in topics ] 
      self.setPeriod(self.__period /  2 )
      if self.__state == CONNECTED:
         self.subscribe()
      log.info("Reload complete")

   # ----------------------------------------
   # Implement MQTT Callbacks
   # -----------------------------------------

   def on_connect(self, flags, rc):
     '''Send the initial event and set last will on unexpected diconnection'''
     if rc == 0:
       self.__state = CONNECTED
       log.info("Connected successfully") 
       self.subscribe()
     else:
       self.__state = FAILED
       log.error("Connection failed, rc =%d", rc)


   def on_disconnect(self, rc):
     log.warning("Unexpected disconnection, rc =%d", rc)
     self.__state  = NOT_CONNECTED
     try:
       self.ema.delReadable(self)
     except ValueError as e:
       log.warning("Recovered from mqtt library 'double disconnection' bug")


   def on_message(self, msg):
      '''Process incoming messages from subscribed topics'''
      log.debug("Received message on topic = %s, QoS = %d, retain = %s",
                msg.topic, msg.qos, msg.retain)
      id = msg.topic.split('/')[1]
      if msg.topic.endswith("history/minmax"):
         self.ema.onMinMaxMessage(id, msg.payload)
      elif msg.topic.endswith("history/samples"):
         self.ema.onSamplesMessage(id, msg.payload)
      elif msg.topic.endswith("current/status"):
         self.ema.onStatusMessage(id, msg.payload)
      else:
         log.warn("message received on unexpected topic %s", msg.topic)
         

   def on_subscribe(self, mid, granted_qos):
     log.info("Subscriptions ok with MID = %s, granted QoS = %s",
               mid, granted_qos)


   def on_unsubscribe(self, mid):
     log.info("Unsubscribe ok with MID = %s", mid)

   # ---------------------------------
   # Implement the Event I/O Interface
   # ---------------------------------

   def onInput(self):
      '''
      Read from message buffer and notify handlers if message complete.
      Called from Server object
      '''
      self.__mqtt.loop_read()
   
   def fileno(self):
      '''Implement this interface to be added in select() system call'''
      return self.__mqtt.socket().fileno()

	
   # ----------------------------------------
   # Implement The Lazy interface
   # -----------------------------------------


   def work(self):
      '''
      Called periodically from a Server object.
      Write blocking behaviour.
      '''
      log.debug("work()")
	 
      if self.__state == NOT_CONNECTED:
         self.connect()
      	 return
      self.__mqtt.loop_misc()


   # --------------
   # Helper methods
   # --------------

   def subscribe(self):
      '''Subscribe to a list of topics'''
      log.info("Subscribing to topics %s", self.__topics) 
      self.__mqtt.subscribe(self.__topics)

   def connect(self):
      '''
      Connect to MQTT Broker with parameters passed at creation time.
      Add MQTT library to the (external) EMA I/O event loop. 
      '''
      try:
         log.info("Connecting to MQTT Broker %s:%s", self.__host, self.__port)
         self.__state = CONNECTING
         self.__mqtt.connect(self.__host, self.__port, self.__period)
         self.ema.addReadable(self)
      except IOError, e:	
         log.error("%s",e)
         if e.errno == 101:
            log.warning("Trying to connect on the next cycle")
            self.__state = NOT_CONNECTED
         else:
            self.__state = FAILED
            raise

if __name__ == "__main__":
      pass
