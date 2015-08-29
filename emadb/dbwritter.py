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

TYP_SAMPLES = 'Samples'
TYP_MIN     = 'Minima'
TYP_MAX     = 'Maxima'
TYP_UNK     = 'Unknown'

def xtMeasType(message):
   '''Extract and transform Measurement Type'''
   t =  message[SMTB:SMTE]
   if t == MTCUR:
      msgtype = TYP_SAMPLE
   elif t == MTMIN:
      msgtype = TYP_MIN
   elif t == MTMAX:
      msgtype = TYP_MAX
   else:
      msgtype = TYP_UNK
   return msgtype

RLY_OPEN   = 'Open'
RLY_CLOSED = 'Closed'

def xtRoofRelay(message):
   '''Extract and transform Roof Relay Status'''
   c = message[SRRB]
   return RLY_CLOSED if c == 'C' else RLY_OPEN

def xtAuxRelay(message):
   '''Extract and transform Aux Relay Status'''
   c = message[SARB]
   return RLY_OPEN if c == 'E' or c == 'e' else RLY_CLOSED

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

def xtMagInstrument(message):
   '''Extract and Transform into Instrumental Magnitude in Hz'''
   exp  = int(message[SPHB]) - 3      
   mant = int(message[SPHB+1:SPHE])
   return mant*pow(10, exp)

def xtMagVisual(message):
   '''Extract and Transform into Visual maginitued per arcsec 2'''
   instrmag = xtMagInstrument(message)
   # We need the formulae to compute visual magnitude from Hz
   # For the time being, we return Hz.
   return 0.0
   
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

   def __init__(self, paren):
      self.__paren = paren


   def reload(self, conn):            
      '''Reconfigures itself after a reload'''
      self.__conn     = conn
      self.__cursor   = self.__conn.cursor()
      self.__rowcount = self.rowcount()
      paren = self.__paren      # shortcut
      # Build units cache
      self.__relay = {
         (RLY_CLOSED,RLY_CLOSED): paren.lkUnits(roof=RLY_CLOSED,aux=RLY_CLOSED),
         (RLY_CLOSED,RLY_OPEN):   paren.lkUnits(roof=RLY_CLOSED, aux=RLY_OPEN),
         (RLY_OPEN,RLY_CLOSED):   paren.lkUnits(roof=RLY_OPEN, aux=RLY_CLOSED),
         (RLY_OPEN,RLY_OPEN):     paren.lkUnits(roof=RLY_OPEN, aux=RLY_OPEN),
      }
      # Build type cache
      self.__type = {
         TYP_MIN:  paren.lkType(TYP_MIN),
         TYP_MAX:  paren.lkType(TYP_MAX),
      }      

   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM MinMaxHistory")
      return self.__cursor.fetchone()[0]

   def insert(self, rows):
      '''Update the MinMaxHistory Fact Table'''
      log.info("Update MinMaxHistory Table data")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO MinMaxHistory VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.warn("Overlapping rows")  
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rc = self.rowcount()
      log.info("minmax commited rows (%d/%d)", rc - self.__rowcount, len(rows))
      self.__rowcount = rc

   def row(self, date_id, time_id, station_id, message):
      '''Produces one minmax row to be inserted into the database'''

      # Get values from cache
      units_id = self.__relay.get((xtRoofRelay(message),xtAuxRelay(message)), 0)
      type_id  = self.__type.get(xtMeasType(message), 0)

      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         type_id,               # type_id
         units_id,                            # units_id
         xtVoltage(message),                  # voltage
         xtRainProbability(message),          # rain_probability
         xtCloudLevel(message),               # clouds_level
         xtCalPressure(message),              # cal_pressure
         xtAbsPressure(message),              # abs_pressure
         xtRainLevel(message),                # rain_level
         xtIrradiation(message),              # irradiation
         xtMagVisual(message),                # visual_magnitude
         xtMagInstrument(message),            # instrumental_magnitude
         xtTemperature(message),              # temperature
         xtHumidity(message),                 # humidity
         xtDewPoint(message),                 # dew_point
         xtWindSpeed(message),                # wind_speed
         xtWindDirection(message),            # wind_direction
         )


# =====================
# RealTimeSamples Class
# =====================

class RealTimeSamples(object):

   def __init__(self, paren):
      self.__paren    = paren


   def reload(self, conn):            
      '''Reconfigures itself after a reload'''
      self.__conn     = conn
      self.__cursor   = self.__conn.cursor()
      self.__rowcount = self.rowcount()
      paren = self.__paren      # shortcut
      # Build units cache
      self.__relay = {
         (RLY_CLOSED,RLY_CLOSED): paren.lkUnits(roof=RLY_CLOSED,aux=RLY_CLOSED),
         (RLY_CLOSED,RLY_OPEN):   paren.lkUnits(roof=RLY_CLOSED, aux=RLY_OPEN),
         (RLY_OPEN,RLY_CLOSED):   paren.lkUnits(roof=RLY_OPEN, aux=RLY_CLOSED),
         (RLY_OPEN,RLY_OPEN):     paren.lkUnits(roof=RLY_OPEN, aux=RLY_OPEN),
      }


   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM RealTimeSamples")
      return self.__cursor.fetchone()[0]

   def insert(self, rows):
      '''Update the RealTimeSamples Fact Table'''
      log.debug("Update RealTimeSamples Table data")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO RealTimeSamples VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.warn("Overlapping rows")  
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rc = self.rowcount()
      log.debug("samples commited rows (%d/%d)", rc - self.__rowcount, len(rows))
      self.__rowcount = rc

   def row(self, date_id, time_id, station_id, lag, message):
      '''Produces one real time row to be inserted into the database'''

      # get units from cache
      units_id = self.__relay.get((xtRoofRelay(message),xtAuxRelay(message)),0 )

      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         units_id,              # units_id
         xtVoltage(message),                  # voltage
         xtRainProbability(message),          # rain_probability
         xtCloudLevel(message),               # clouds_level
         xtCalPressure(message),              # cal_pressure
         xtAbsPressure(message),              # abs_pressure
         xtRainLevel(message),                # rain_level
         xtIrradiation(message),              # irradiation
         xtMagVisual(message),                # visual_magnitude
         xtMagInstrument(message),            # instrumental_magnitude
         xtTemperature(message),              # temperature
         xtHumidity(message),                 # humidity
         xtDewPoint(message),                 # dew_point
         xtWindSpeed(message),                # wind_speed
         xtWindDirection(message),            # wind_direction
         lag,                                 # lag
      )

   def purge(self):
      '''Purges database'''
      now = datetime.datetime.utcnow()
      midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
      delta = datetime.timedelta(minutes=2*self.__paren.period)
      if now - midnight < delta:
         self.delete(now.year*10000 + now.month*100 +now.day)

   def delete(self, date_id):
      '''Delete samples older than a given date_id'''
      log.debug("Delete RealTimeSamples Table data older than %d", date_id)
      try:
         self.__cursor.execute(
            "DELETE FROM RealTimeSamples WHERE date_id < ?", (date_id,))
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rc = self.rowcount()
      log.debug("samples deleted rows (%d)", self.__rowcount - rc)
      self.__rowcount = rc


# ==========
# Main Class
# ==========

class DBWritter(Lazy):

   N_RT_WRITES = 60

   def __init__(self, ema, parser):
      Lazy.__init__(self, 60)
      self.ema        = ema
      self.period     = 1
      self.__rtwrites = 0
      self.__parser   = parser
      self.__file     = None
      self.__conn     = None
      self.minmax     = MinMaxHistory(self)
      self.realtime   = RealTimeSamples(self)
      ema.addLazy(self)
      self.reload()
      log.info("DBWritter object created")

   def reload(self):
      '''Reload config data and reconfigure itself'''
      parser = self.__parser
      lvl      = parser.get("DBASE", "dbase_log")
      log.setLevel(lvl)
      dbfile    = parser.get("DBASE", "dbase_file")
      json_dir  = parser.get("DBASE", "dbase_json_dir")
      period    = parser.getint("DBASE", "dbase_period")
      self.period = period
      self.setPeriod(60*period)
      try:
         if self.__file != dbfile and self.__conn is not None:
            self.__conn.close()
         log.debug("opening database %s", dbfile)
         self.__conn    = sqlite3.connect(dbfile)
         self.__cursor  = self.__conn.cursor()
         self.__file    = dbfile
         schema.generate(self.__conn, json_dir, replace=False)
      except sqlite3.Error as e:
         log.error("Error %s:", e.args[0])
         if self.__conn:
            self.__conn.rollback()
         raise
      self.minmax.reload(self.__conn)
      self.realtime.reload(self.__conn)
      log.debug("Reload complete")
      

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
         r = self.minmax.row(date_id, time_id, station_id, message[3*i])
         rows.append(r)
         r = self.minmax.row(date_id, time_id, station_id, message[3*i+1])
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
      lag = int(round((t1 - t0).total_seconds()))
      log.debug( "t1 = %s, t0 = %s", t1, t0)
      log.debug("Received status message from station %s (lag = %d)",
                mqtt_id, lag)
      row = self.realtime.row(date_id, time_id, station_id, lag, message[0])
      self.realtime.insert((row,))
      self.__rtwrites += 1
      if (self.__rtwrites % DBWritter.N_RT_WRITES) == 1:
         log.info("RealTimeSamples rows written so far: %d" % self.__rtwrites)

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
      self.realtime.purge()

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


   def lkUnits(self, roof, aux):
      '''return units_id key from units'''
      self.__cursor.execute("SELECT units_id FROM Units WHERE roof_relay=? AND aux_relay=?",
                            (roof, aux))
      units_id = self.__cursor.fetchone() or (0,)
      log.verbose("lkUnits(roof=%s,aux=%s) => %s", roof, aux, units_id)
      return units_id[0]

   # -------------------------------
   # Facts SQL Loader helper methods
   # -------------------------------



if __name__ == "__main__":
      pass
