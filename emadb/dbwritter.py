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
# The DB Writter that performs the ETL process to a SQLite Database
#
# ======================================================================

import logging
import sqlite3
import schema
import re
import os
import datetime
import operator

from server import Lazy, Server

# Relays
from emaproto  import SRRB, SARB
# Anemometer
from emaproto  import SAAB, SAAE, SACB, SACE, SWDB, SWDE
# Barometer
from emaproto  import SABB, SABE, SCBB, SCBE
# Cloud Sensor
from emaproto  import SCLB, SCLE
# Pluviometer
from emaproto  import SPCB, SPCE, SPAB, SPAE
# Pyranometer
from emaproto  import SPYB, SPYE
# Photometer
from emaproto  import SPHB, SPHE
# Rain detector
from emaproto  import SRAB, SRAE
# Thermometer
from emaproto  import SATB, SATE, SRHB, SRHE, SDPB, SDPE
# Voltmeter
from emaproto  import SPSB, SPSE
# Message Types
from emaproto  import SMTB, SMTE, MTCUR, MTHIS, MTISO, MTMIN, MTMAX

log = logging.getLogger('dbwritter')

# ===============================
# Extract and Transform Functions
# ===============================

def xtDateTime(tstamp):
   '''Extract and transform Date & Time from (HH:MM:SS DD/MM/YYYY)'''
   # Parse and perform rounding to the nearest minute
   ts = datetime.datetime.strptime(tstamp, "(%H:%M:%S %d/%m/%Y)") + \
        datetime.timedelta(minutes=0.5)
   time_id = ts.hour*100 + ts.minute
   date_id = ts.year*10000 + ts.month*100 + ts.day
   return date_id, time_id, ts

def xtMeasType(message):
   '''Extract and transform Measurement Type'''
   t =  message[SMTB:SMTE]
   if t == MTCUR:
      msgtype = 'Samples'
   elif t == MTMIN:
      msgtype = 'Minima'
   elif t == MTMAX:
      msgtype = 'Maxima'
   else:
      msgtype = 'Unknown'
   return msgtype

def xtRoofRelay(message):
   '''Extract and transform Roof Relay Status'''
   c = message[SRRB]
   return 'Closed' if c == 'C' else 'Open'

def xtAuxRelay(message):
   '''Extract and transform Aux Relay Status'''
   c = message[SARB]
   return 'Open' if c == 'E' or c == 'e' else 'Closed'

def xtVoltage(message):
   '''Extract and transform Voltage'''
   return float(message[SPSB:SPSE]) / 10

def xtRainProbability(message):
   '''Extract and transform Rain Probability'''
   return float(message[SRAB:SRAE]) / 10

def xtCloudLevel(message):
   '''Extract and transform Cloud Level'''
   return float(message[SCLB:SCLE]) / 10

def xtCalPressure(message):
   '''Extract and transform Calibrated Pressure at sea level'''
   return  float(message[SCBB:SCBE]) / 10

def xtAbsPressure(message):
   '''Extract and transform Absolute Pressure'''
   return  float(message[SABB:SABE]) / 10

def xtRainLevel(message):
   '''Extract and transform Rain Level'''
   return float(message[SPCB:SPCE]) / 10

def xtIrradiation(message):
   '''Extract and transform Solar Irradiantion Level'''
   return float(message[SPYB:SPYE]) / 10

def xtMagnitude(message):
   '''Extract and Transform into Visual maginitued per arcsec 2'''
   exp  = int(message[SPHB]) - 3      
   mant = int(message[SPHB+1:SPHE])
   # We need the formulae to compute visual magnitude from Hz
   # For the time being, we return Hz.
   return mant*pow(10, exp)

def xtTemperature(message):
   '''Extract and transform Temperature'''
   return  float(message[SATB:SATE]) / 10

def xtHumidity(message):
   '''Extract and transform Relative Humidity'''
   return float(message[SRHB:SRHE]) / 10 

def xtDewPoint(message):
   '''Extract and transform Dew Point'''
   return float(message[SDPB:SDPE]) / 10

def xtWindSpeed10(message):
   '''Extract and transform Wind Speed moving average during 10 min.'''
   return float(message[SAAB:SAAE])

def xtWindSpeed(message):
   '''Extract and transform Wind Speed'''
   return float(message[SACB:SACE]) / 10

def xtWindDirection(message):
   '''Extract and transform Wind Direction'''
   return int(message[SWDB:SWDE])


# ===================
# MinMaxHistory Class
# ===================

class MinMaxHistory(object):

   def __init__(self, conn):
      self.__conn     = conn
      self.__cursor   = self.__conn.cursor()
      self.__rowcount = self.rowcount()
      log.debug("MinMaxHistory object created")

   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM MinMaxHistory")
      return self.__cursor.fetchone()[0]

   def insert(self, rows):
      '''Update the MinMaxHistory Fact Table'''
      log.info("Update MinMaxHistory Table data")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO MinMaxHistory VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.warn("Overlapping rows")  
      except sqlite3.Error, e:
         log.error(e)
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rc = self.rowcount()
      log.info("commited Rows (%d/%d)", rc - self.__rowcount, len(rows))
      self.__rowcount = rc

   def row(self, date_id, time_id, station_id, message, paren):
      '''Produces one row to be inserted into the database'''
      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         paren.lkType(xtMeasType(message)),   # type_id
         paren.lkUnits(xtRoofRelay(message)), # roof_relay_id
         paren.lkUnits(xtAuxRelay(message)),  # aux_relay_id
         xtVoltage(message),                  # voltage
         paren.lkUnits('V'),                  # voltage_units_id
         xtRainProbability(message),          # rain_probability
         paren.lkUnits('%'),                  # rain_proability_units_id
         xtCloudLevel(message),               # clouds_level
         paren.lkUnits('%'),                  # clouds_level_units_id
         xtCalPressure(message),              # cal_pressure
         paren.lkUnits('HPa'),                # call_pressure_units_id
         xtAbsPressure(message),              # abs_pressure
         paren.lkUnits('HPa'),                # abs_pressure_units_id
         xtRainLevel(message),                # rain_level
         paren.lkUnits('mm'),                 # rain_level_units_id
         xtIrradiation(message),              # irradiation
         paren.lkUnits('%'),                  # irradiation_units_id
         xtMagnitude(message),                # magnitude
         paren.lkUnits('Hz'),                 # magnitude_units_id
         xtTemperature(message),              # temperature
         paren.lkUnits('deg C'),              # temperature_units_id
         xtHumidity(message),                 # humidity
         paren.lkUnits('%'),                  # humidity_units_id
         xtDewPoint(message),                 # dew_point
         paren.lkUnits('deg C'),              # dew_point_units_id
         xtWindSpeed(message),                # wind_speed
         paren.lkUnits('Km/h'),               # wind_speed_units_id
         xtWindDirection(message),            # wind_direction
         paren.lkUnits('degrees'),            # wind_direction_units_id
         )


# =====================
# RealTimeSamples Class
# =====================

class RealTimeSamples(object):

   def __init__(self, conn):
      self.__conn     = conn
      self.__cursor   = self.__conn.cursor()
      self.__rowcount = self.rowcount()
      log.debug("RealTimeSamples object created")

   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM RealTimeSamples")
      return self.__cursor.fetchone()[0]

   def insert(self, rows):
      '''Update the RealTimeSamples Fact Table'''
      log.info("Update RealTimeSamples Table data")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO RealTimeSamples VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.warn("Overlapping rows")  
      except sqlite3.Error, e:
         log.error(e)
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rc = self.rowcount()
      log.info("commited Rows (%d/%d)", rc - self.__rowcount, len(rows))
      self.__rowcount = rc

   def row(self, date_id, time_id, station_id, lag, message, paren):
      '''Produces one row to be inserted into the database'''
      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         paren.lkUnits(xtRoofRelay(message)), # roof_relay_id
         paren.lkUnits(xtAuxRelay(message)),  # aux_relay_id
         xtVoltage(message),                 # voltage
         paren.lkUnits('V'),                  # voltage_units_id
         xtRainProbability(message),         # rain_probability
         paren.lkUnits('%'),                  # rain_proability_units_id
         xtCloudLevel(message),              # clouds_level
         paren.lkUnits('%'),                  # clouds_level_units_id
         xtCalPressure(message),             # cal_pressure
         paren.lkUnits('HPa'),                # call_pressure_units_id
         xtAbsPressure(message),             # abs_pressure
         paren.lkUnits('HPa'),                # abs_pressure_units_id
         xtRainLevel(message),               # rain_level
         paren.lkUnits('mm'),                 # rain_level_units_id
         xtIrradiation(message),             # irradiation
         paren.lkUnits('%'),                  # irradiation_units_id
         xtMagnitude(message),               # magnitude
         paren.lkUnits('Hz'),                 # magnitude_units_id
         xtTemperature(message),             # temperature
         paren.lkUnits('deg C'),              # temperature_units_id
         xtHumidity(message),                # humidity
         paren.lkUnits('%'),                  # humidity_units_id
         xtDewPoint(message),                # dew_point
         paren.lkUnits('deg C'),              # dew_point_units_id
         xtWindSpeed(message),               # wind_speed
         paren.lkUnits('Km/h'),               # wind_speed_units_id
         xtWindDirection(message),           # wind_direction
         paren.lkUnits('degrees'),            # wind_direction_units_id
         lag,                                # lag
         paren.lkUnits('sec'),                # lag_units_id
         )


# ==========
# Main Class
# ==========

class DBWritter(Lazy):

   def __init__(self, ema, parser):
      lvl      = parser.get("DBASE", "dbase_log")
      log.setLevel(lvl)
      dbfile    = parser.get("DBASE", "dbase_file")
      json_dir  = parser.get("DBASE", "dbase_json_dir")
      period    = parser.getint("DBASE", "dbase_period")
      Lazy.__init__(self, period*60)
      self.ema        = ema
      self.__conn     = None
      self.__rows     = []      # acumulating status msg rows
      try:
         self.__conn    = sqlite3.connect(dbfile)
         self.__cursor  = self.__conn.cursor()
         schema.generate(self.__conn, json_dir, replace=False)
      except sqlite3.Error as e:
         log.error("Error %s:", e.args[0])
         if self.__conn:
            self.__conn.rollback()
         raise
      ema.addLazy(self)
      self.minmax = MinMaxHistory(self.__conn)
      self.realtime = RealTimeSamples(self.__conn)
      log.info("DBWritter object created")

   # -----------
   # ETL API
   # -----------

   def processMinMax(self, mqtt_id, payload):
      '''extract MinMax History data and load into its table'''
      log.debug("Received minmax message from station %s", mqtt_id)
      station_id = self.lkStation(mqtt_id)
      if station_id == 0:
         log.warn("Ignoring message from unregistered station")
         return
      rows = []
      message = payload.split('\n')
      for i in range(0 , len(message)/3):
         date_id, time_id, dummy = xtDateTime(message[3*i+2])
         r = self.minmax.row(date_id, time_id, station_id, message[3*i], self)
         rows.append(r)
         r = self.minmax.row(date_id, time_id, station_id, message[3*i+1], self)
         rows.append(r)
      # It seemd there is no need to sort the dates
      # non-overlapping data do get written anyway 
      #rows = sorted(rows, key=operator.itemgetter(0,1), reverse=True)

      self.minmax.insert(rows)


   def processStatus(self, mqtt_id, payload):
      '''Extract real time EMA status message and stor it into its table'''
      t1 = datetime.datetime.utcnow()
      station_id = self.lkStation(mqtt_id)
      if station_id == 0:
         log.warn("Ignoring message from unregistered station")
         return
      message = payload.split('\n')
      date_id, time_id, t0 = xtDateTime(message[1])
      lag = (t1 - t0).total_seconds()
      log.debug( "t1 = %s, t0 = %s", t1, t0)
      log.debug("Received status message from station %s (lag = %d)",
                mqtt_id, lag)
      r = self.realtime.row(date_id, time_id, station_id, lag, message[0], self)
      self.__rows.insert(0,r)   # more recent at the beginning


   def processSamples(self, mqtt_id, payload):
      log.debug("Received samples message from station %s", mqtt_id)


   # ----------------------------
   # Implement The Lazy interface 
   # ----------------------------

   def work(self):
      '''
      Called periodically from a Server object.
      Write blocking behaviour.
      '''
      log.debug("work()")
      self.realtime.insert(self.__rows)
      self.__rows = []

   # ------------------------------------
   # Dimensions SQL Lookup helper methods
   # ------------------------------------

   def lkType(self, meas_type):
      '''return meas_id key from meas_type'''
      self.__cursor.execute("SELECT type_id FROM Type WHERE type=?",
                            (meas_type,))
      meas_id = self.__cursor.fetchone() or (0,)
      log.verbose("lkType(%s) => %s", meas_type, meas_id)
      return meas_id[0]


   def lkStation(self, mqtt_id):
      '''return station_id key from mqtt_id'''
      self.__cursor.execute("SELECT station_id FROM Station WHERE mqtt_id=?",
                            (mqtt_id,))
      station_id = self.__cursor.fetchone() or (0,)
      log.verbose("lkStation(%s) => %s", mqtt_id, station_id)
      return station_id[0]


   def lkUnits(self, units):
      '''return units_id key from units'''
      self.__cursor.execute("SELECT units_id FROM Units WHERE units=?",
                            (units,))
      units_id = self.__cursor.fetchone() or (0,)
      log.verbose("lkUnits(%s) => %s", units, units_id)
      return units_id[0]

   # -------------------------------
   # Facts SQL Loader helper methods
   # -------------------------------



if __name__ == "__main__":
      pass
