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
# MQTT Subscriber object specific to EMA weather stations
# Delivers the three kind of messages expected to its parent server
# which will delegate them to the back-end dbwritter object
# ======================================================================

import logging
log = logging.getLogger('mqtt')

from mqttsubscriber import MQTTGenericSubscriber

class MQTTClient(MQTTGenericSubscriber):

   def __init__(self, srv, parser):
      MQTTGenericSubscriber.__init__(self, srv, parser)

   def onMessage(self, msg, tstamp):
      log.debug("Received message on topic = %s, QoS = %d, retain = %s",
                msg.topic, msg.qos, msg.retain)
      id = msg.topic.split('/')[1]
      if msg.topic.endswith("history/minmax"):
         self.srv.onMinMaxMessage(id, msg.payload)
      elif msg.topic.endswith("history/samples"):
         self.srv.onSamplesMessage(id, msg.payload)
      elif msg.topic.endswith("current/status"):
         self.srv.onCurrentStatusMessage(id, msg.payload, tstamp)
      elif msg.topic.endswith("average/status"):
         self.srv.onAverageStatusMessage(id, msg.payload, tstamp)
      else:
         log.warn("message received on unexpected topic %s", msg.topic)
