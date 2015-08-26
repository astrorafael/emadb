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
            server.Server.__init__(self)
            self.buildFrom(configfile)

        def buildFrom(self, configfile):
		'''Buld children objects from configuration file'''

		if not (configfile != None and os.path.exists(configfile)):
			log.error("No configuration is given. Exiting ...")
			return

		log.info("Loading configuration from %s" % configfile)
		config = parser.ConfigParser()
		config.optionxform = str
		config.read(configfile)

		# DBWritter object 
		self.dbwritter = dbwritter.DBWritter(self, config)
				
		# MQTT Driver object 
		self.mqttclient = mqttclient.MQTTClient(self, config)

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
