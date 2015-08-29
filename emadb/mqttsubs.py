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
# A generic MQTT subscriber client to be used by my tiny server framework
# Must be subclassed a least do customize the onMessage() method.
#
# This class inherits from Lazy to periodically execute a work() procedure
# responsible for:
# 1. Managing connection to MQTT Broker. No disconnections are ever requested.
# 2. Managing subscriptions.
# 3. Delivering data to backend objects like databases
# 
# The work() procedure executes twice as fast as 
# the keepalive timeout specidied to the client MQTT library.
#
# ======================================================================

import logging
import paho.mqtt.client as mqtt
import socket
from   abc import ABCMeta, abstractmethod

from server import Lazy, Server
import utils

# MQTT Connection Status
NOT_CONNECTED = 0
CONNECTING    = 1
CONNECTED     = 2
FAILED        = 3
DISCONNECTING = 4

# Default QoS
QOS = 1

	
log = logging.getLogger('mqtt')


# Callback when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
   userdata.onConnect(flags, rc)

def on_disconnect(client, userdata, rc):
   userdata.onDisconnect(rc)

# Callback when a PUBLISH message is received from the server.
# The default message callback
def on_message(client, userdata, msg):
    userdata.onMessage(msg)

# Callback subscriptions
def on_subscribe(client, userdata, mid, granted_qos):
    userdata.onSubscribe(mid, granted_qos)

def on_unsubscribe(client, userdata, mid):
    userdata.onUnsubscribe(mid)

class MQTTGenericSubscriber(Lazy):

   def __init__(self, srv, parser):
      Lazy.__init__(self, 60)
      self.parser   = parser
      self.srv        = srv
      self.state    = NOT_CONNECTED
      self.topics   = []
      srv.addLazy(self)
      # We do not allow to reconfigure an existing connection
      # to a broker as we would loose incoming data
      self.id       = parser.get("MQTT", "mqtt_id")
      self.host     = parser.get("MQTT", "mqtt_host")
      self.port     = parser.getint("MQTT", "mqtt_port")
      self.mqtt     = mqtt.Client(client_id=self.id+'@'+ socket.gethostname(), 
                                  userdata=self)
      self.mqtt.on_connect     = on_connect
      self.mqtt.on_disconnect  = on_disconnect
      self.mqtt.on_message     = on_message
      self.mqtt.on_subscribe   = on_subscribe
      self.mqtt.on_unsubscribe = on_unsubscribe
      self.reload()
      log.info("MQTT client created")


      # we only allow to reconfigure the topic list and keepalive period
   def reload(self):
      '''Reloads and reconfigures itself'''
      parser = self.parser    # shortcut
      lvl             = parser.get("MQTT", "mqtt_log")
      log.setLevel(lvl)
      self.period   = parser.getint("MQTT", "mqtt_period")
      self.setPeriod(self.period /  2 )
      topics          = utils.chop(parser.get("MQTT", "mqtt_topics"),',')
      self.newtopics = [ (topic, QOS) for topic in topics ] 
      if self.state == CONNECTED:
         self.subscribe()
      log.debug("Reload complete")

   # ----------------------------------------
   # Implement MQTT Callbacks
   # -----------------------------------------

   def onConnect(self, flags, rc):
     '''Send the initial event and set last will on unexpected diconnection'''
     if rc == 0:
       self.state = CONNECTED
       log.info("Connected successfully") 
       self.subscribe()
     else:
       self.state = FAILED
       log.error("Connection failed, rc =%d", rc)


   def onDisconnect(self, rc):
     log.warning("Unexpected disconnection, rc =%d", rc)
     self.state  = NOT_CONNECTED
     self.topics = []
     try:
       self.srv.delReadable(self)
     except ValueError as e:
       log.warning("Recovered from mqtt library 'double disconnection' bug")


   @abstractmethod
   def onMessage(self, msg):
      '''
      Process incoming messages from subscribed topics.
      Typically will pass the message to a backend object via
      the parent server object
      '''
      pass


   def onSubscribe(self, mid, granted_qos):
     log.info("Subscriptions ok with MID = %s, granted QoS = %s",
               mid, granted_qos)


   def onUnsubscribe(self, mid):
     log.info("Unsubscribe ok with MID = %s", mid)

   # ---------------------------------
   # Implement the Event I/O Interface
   # ---------------------------------

   def onInput(self):
      '''
      Read from message buffer and notify handlers if message complete.
      Called from Server object
      '''
      self.mqtt.loop_read()
   
   def fileno(self):
      '''Implement this interface to be added in select() system call'''
      return self.mqtt.socket().fileno()

	
   # ----------------------------------------
   # Implement The Lazy interface
   # -----------------------------------------


   def work(self):
      '''
      Called periodically from a Server object.
      Write blocking behaviour.
      '''
      log.debug("work()")
	 
      if self.state == NOT_CONNECTED:
         self.connect()
      	 return
      self.mqtt.loop_misc()


   # --------------
   # Helper methods
   # --------------

   def subscribe(self):
      '''Subscribe smartly to a list of topics'''

      # Unsubscribe first if necessary
      topics = [ t[0] for t in (set(self.topics) - set(self.newtopics)) ]
      if len(topics):
         self.mqtt.unsubscribe(topics)
         log.info("Unsubscribing from topics %s", topics)
      else:
         log.info("no need to unsubscribe")

      # Now subscribe
      topics = [ t for t in (set(self.newtopics) - set(self.topics)) ]
      if len(topics):
         log.info("Subscribing to topics %s", topics) 
         self.mqtt.subscribe(topics)
      else:
         log.info("no need to subscribe")
      self.topics = self.newtopics


   def connect(self):
      '''
      Connect to MQTT Broker with parameters passed at creation time.
      Add MQTT library to the (external) EMA I/O event loop. 
      '''
      try:
         log.info("Connecting to MQTT Broker %s:%s", self.host, self.port)
         self.state = CONNECTING
         self.mqtt.connect(self.host, self.port, self.period)
         self.srv.addReadable(self)
      except IOError, e:	
         log.error("%s",e)
         if e.errno == 101:
            log.warning("Trying to connect on the next cycle")
            self.state = NOT_CONNECTED
         else:
            self.state = FAILED
            raise

