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
import math

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

from emaproto import STRFTIME, magnitude, decodeFreq

log = logging.getLogger('dbwritter')

DATABASE_LOCKED = "database is locked"

UNKNOWN_STATION_ID = -1
UNKNOWN_MEAS_ID    = -1
UNKNOWN_UNITS_ID   = -1
UNKNOWN_DATE_ID    = -1
UNKNOWN_TIME_ID    = -1

TYP_SAMPLES = 'Samples'
TYP_MIN     = 'Minima'
TYP_MAX     = 'Maxima'
TYP_UNK     = 'Unknown'
TYP_MINMAX  = "MinMax"
TYP_AVER    = "Averages"

RLY_OPEN   = 'Open'
RLY_CLOSED = 'Closed'

# ===============================
# Extract and Transform Functions
# ===============================


def roundDateTime(ts):
   '''Round a timestamp to the nearest minute'''
   tsround = ts + datetime.timedelta(minutes=0.5)
   time_id = tsround.hour*100   + tsround.minute
   date_id = tsround.year*10000 + tsround.month*100 + tsround.day
   return date_id, time_id, ts

def xtDateTime(tstamp):
   '''Extract and transform Date & Time from (HH:MM:SS DD/MM/YYYY)'''
   ts = datetime.datetime.strptime(tstamp, STRFTIME) 
   return roundDateTime(ts)

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

def xtWetLevel(message):
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

def xtRain(message):
   '''Extract and transform Rain Level'''
   return float(message[SPCB:SPCE]) / 10

def xtIrradiation(message):
   '''Extract and transform Solar Irradiantion Level'''
   return float(message[SPYB:SPYE]) / 10

def xtFrequency(message):
   '''Extracts Frequency information'''
   return decodeFreq(message[SPHB:SPHE])

def xtMagVisual(message):
   '''Extract and Transform into Visual maginitued per arcsec 2'''
   return magnitude(xtFrequency(message))
   
def xtTemperature(message):
   '''Extract and transform Temperature'''
   return  float(message[SATB:SATE]) / 10

def xtHumidity(message):
   '''Extract and transform Relative Humidity'''
   return float(message[SRHB:SRHE]) / 10 

def xtDewPoint(message):
   '''Extract and transform Dew Point'''
   return float(message[SDPB:SDPE]) / 10

def xtWindSpeed10m(message):
   '''Extract and transform Wind Speed average during 10 min.'''
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
      log.debug("MinMaxHistory: updating table")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO MinMaxHistory VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.debug("MinMaxHistory: overlapping rows")  
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.critical("MinMaxHistory: %d rows starting from %s cound not be written: %s",
                   len(rows),
                   rows[0][0:4],
                   DATABASE_LOCKED
                )
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rowcount = self.rowcount()
      commited = rowcount -  self.__rowcount
      self.__rowcount = rowcount
      log.info("MinMaxHistory: commited rows (%d/%d)", commited, len(rows))
      return  commited


   def row(self, date_id, time_id, station_id, tstamp,  message):
      '''Produces one minmax row to be inserted into the database'''

      # Get values from cache
      units_id = self.__relay.get((xtRoofRelay(message),xtAuxRelay(message)), -11)
      type_id  = self.__type.get(xtMeasType(message), -1)

      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         type_id,               # type_id
         units_id,              # units_id
         xtVoltage(message),    # voltage
         xtWetLevel(message),   # wet
         xtCloudLevel(message), # cloudy
         xtCalPressure(message),   # cal_pressure
         xtAbsPressure(message),   # abs_pressure
         xtRain(message),          # rain
         xtIrradiation(message),   # irradiation
         xtMagVisual(message),     # vis_magnitude
         xtFrequency(message),     # frequency
         xtTemperature(message),   # temperature
         xtHumidity(message),      # rel_humidity
         xtDewPoint(message),      # dew_point
         xtWindSpeed(message),     # wind_speed
         xtWindSpeed10m(message),  # wind_speed10m
         xtWindDirection(message), # wind_direction
         tstamp,                   # timestamp
         )



# =====================
# AveragesHistory Class
# =====================


class AveragesHistory(object):

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


   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM AveragesHistory")
      return self.__cursor.fetchone()[0]


   def insert(self, rows):
      '''Update the AveragesHistory Fact Table'''
      log.debug("AveragesHistory: updating table")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO AveragesHistory VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.debug("AveragesHistory: overlapping rows")  
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.critical("AveragesHistory: %d rows starting from %s cound not be written: %s",
                   len(rows),
                   rows[0][0:4],
                   DATABASE_LOCKED
                )
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rowcount = self.rowcount()
      commited = rowcount -  self.__rowcount
      self.__rowcount = rowcount
      log.info("AveragesHistory: commited rows (%d/%d)", commited, len(rows))
      return  commited


   def row(self, date_id, time_id, station_id, tstamp,  message):
      '''Produces one averages history row to be inserted into the database'''

      # Get values from cache
      units_id = self.__relay.get((xtRoofRelay(message),xtAuxRelay(message)), -11)

      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         units_id,              # units_id
         xtVoltage(message),    # voltage
         xtWetLevel(message),   # wet
         xtCloudLevel(message), # cloudy
         xtCalPressure(message),   # cal_pressure
         xtAbsPressure(message),   # abs_pressure
         xtRain(message),          # rain
         xtIrradiation(message),   # irradiation
         xtMagVisual(message),     # vis_magnitude
         xtFrequency(message),     # frequency
         xtTemperature(message),   # temperature
         xtHumidity(message),      # rel_humidity
         xtDewPoint(message),      # dew_point
         xtWindSpeed(message),     # wind_speed
         xtWindSpeed10m(message),  # wind_speed10m
         xtWindDirection(message), # wind_direction
         tstamp,                   # timestamp
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
      # Build type cache
      self.__type = {
         TYP_SAMPLES: paren.lkType(TYP_SAMPLES),
         TYP_AVER:    paren.lkType(TYP_AVER),
      }      


   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM RealTimeSamples")
      return self.__cursor.fetchone()[0]


   def insert(self, rows):
      '''Update the RealTimeSamples Fact Table'''
      log.debug("RealTimeSamples: updating table")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO RealTimeSamples VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.warn("RealTimeSamples: overlapping rows")
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.critical("RealTimeSamples: %d rows starting from %s cound not be written: %s",
                   len(rows),
                   rows[0][0:3],
                   DATABASE_LOCKED
                )  
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rowcount = self.rowcount()
      commited = rowcount -  self.__rowcount
      self.__rowcount = rowcount
      log.debug("RealTimeSamples: commited rows (%d/%d)", commited, len(rows))
      return  commited


   def row(self, date_id, time_id, station_id, meas_type, tstamp, message):
      '''Produces one real time row to be inserted into the database'''

      # get units from cache
      units_id = self.__relay.get((xtRoofRelay(message),xtAuxRelay(message)),-1)
      type_id = self.__type.get(meas_type, -1)

      return (
         date_id,               # date_id
         time_id,               # time_id
         station_id,            # station_id
         type_id,               # type_id
         units_id,              # units_id
         xtVoltage(message),    # voltage
         xtWetLevel(message),   # wet
         xtCloudLevel(message), # cloudy
         xtCalPressure(message),   # cal_pressure
         xtAbsPressure(message),   # abs_pressure
         xtRain(message),          # rain
         xtIrradiation(message),   # irradiation
         xtMagVisual(message),     # vis_magnitude
         xtFrequency(message),     # frequency
         xtTemperature(message),   # temperature
         xtHumidity(message),      # rel_humidity
         xtDewPoint(message),      # dew_point
         xtWindSpeed(message),     # wind_speed
         xtWindSpeed10m(message),  # wind_speed10m
         xtWindDirection(message), # wind_direction
         tstamp,                   # timestamp
      )


   def delete(self, date_id):
      '''Delete samples older than a given date_id'''
      log.debug("Delete RealTimeSamples Table data older than %d", date_id)
      try:
         self.__cursor.execute(
            "DELETE FROM RealTimeSamples WHERE date_id < ?", (date_id,))
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.error("Table could not be purged: %s",DATABASE_LOCKED)
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rowcount = self.rowcount()
      commited = rowcount -  self.__rowcount
      self.__rowcount = rowcount
      log.debug("RealTimeSamples: deleted %d rows", commited)
      return  commited


# ===================
# HistoryStats Class
# ===================


class HistoryStats(object):

   def __init__(self, paren):
      self.__paren = paren

   def reload(self, conn):            
      '''Reconfigures itself after a reload'''
      self.__conn     = conn
      self.__cursor   = self.__conn.cursor()
      paren = self.__paren      # shortcut
      # Build type cache
      self.__type = {
         TYP_MINMAX: paren.lkType(TYP_MINMAX),
         TYP_AVER:   paren.lkType(TYP_AVER),
      }      


   def insert(self, rows):
      '''Update the HistoryStats Fact Table'''
      log.debug("HistoryStats: updating table")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO HistoryStats VALUES(?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.debug("HistoryStats: duplicate detected, probably a retained message")
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.critical("HistoryStats: %d rows cound not be written: %s",
                   len(rows),DATABASE_LOCKED)
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated


   def rows(self, station_id, meastype, submitted, commited):
      '''Produces one history stats record to be inserted into the database'''
      # Get values from cache
      type_id  = self.__type.get(meastype, -1)
      date_id, time_id, ts = roundDateTime(datetime.datetime.utcnow())
      timestamp = ts.strftime("%Y-%m-%d %H:%M:%S")
      return (
         (
            date_id,               # date_id
            time_id,               # time_id
            station_id,            # station_id
            type_id,               # type_id
            submitted,             # submitted rows
            commited,              # commited rows
            timestamp,             # timestamp
         ),
      )




# ===================
# RealTimeStats Class
# ===================


class RealTimeStats(object):

   def __init__(self, paren):
      self.__paren = paren

   def reload(self, conn):            
      '''Reconfigures itself after a reload'''
      self.__conn     = conn
      self.__cursor   = self.__conn.cursor()
      paren = self.__paren      # shortcut
      # Build type cache
      self.__type = {
         TYP_SAMPLES: paren.lkType(TYP_SAMPLES),
         TYP_AVER:    paren.lkType(TYP_AVER),
      }      


   def rowcount(self):
      '''Find out the current row count'''
      self.__cursor.execute("SELECT count(*) FROM RealTimeStats")
      return self.__cursor.fetchone()[0]

   def insert(self, rows):
      '''Update the RealTimeStats Fact Table'''
      log.debug("RealTimeStats: updating table")
      try:
         self.__cursor.executemany(
            "INSERT OR FAIL INTO RealTimeStats VALUES(?,?,?,?,?,?,?,?,?)", 
            rows)
      except sqlite3.IntegrityError, e:
         log.debug("RealTimeStats: duplicate detected")
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.critical("RealTimeStats: %d rows cound not be written: %s",
                   len(rows), DATABASE_LOCKED)
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated


   def rows(self, date_id, time_id, station_id, meas_type, tstamp, 
            window_size, nsamples, num_bytes, lag):
      '''Produces one history stats record to be inserted into the database'''
      # Get values from cache
      type_id  = self.__type.get(meas_type, -1)
      return (
         (
            date_id,               # date_id
            time_id,               # time_id
            station_id,            # station_id
            type_id,               # type_id
            tstamp,                # timestamp
            window_size,           # window_size
            nsamples,              # num_samples
            num_bytes,             # num_bytes
            lag,                   # lag
         ),
      )

   def delete(self, date_id):
      '''Delete samples older than a given date_id'''
      log.debug("Delete RealTimeStats Table data older than %d", date_id)
      try:
         self.__cursor.execute(
            "DELETE FROM RealTimeStats WHERE date_id < ?", (date_id,))
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.error("Table could not be purged: %s",DATABASE_LOCKED)
      except sqlite3.Error, e:
         log.error(e)
         self.__conn.rollback()
         raise
      self.__conn.commit()   # commit anyway what was really updated
      rowcount = self.rowcount()
      commited = rowcount -  self.__rowcount
      self.__rowcount = rowcount
      log.debug("RealTimeSamples: deleted %d rows", commited)
      return  commited

# ==========
# Main Class
# ==========

class DBWritter(Lazy):

   N_RT_WRITES = 60

   def __init__(self, srv, parser):
      Lazy.__init__(self, 60)
      self.srv        = srv
      self.period     = 1
      self.__rtwrites = 0
      self.__parser   = parser
      self.__file     = None
      self.__conn     = None
      self.minmax     = MinMaxHistory(self)
      self.realtime   = RealTimeSamples(self)
      self.aver5min   = AveragesHistory(self)
      self.histats    = HistoryStats(self)
      self.rtstats    = RealTimeStats(self)
      srv.addLazy(self)
      self.reload()
      log.info("DBWritter object created")


   def reload(self):
      '''Reload config data and reconfigure itself'''
      parser      = self.__parser
      lvl         = parser.get("DBASE", "dbase_log")
      dbfile      = parser.get("DBASE", "dbase_file")
      json_dir    = parser.get("DBASE", "dbase_json_dir")
      period      = parser.getint("DBASE", "dbase_period")
      date_fmt    = parser.get("DBASE", "dbase_date_fmt")
      year_start  = parser.getint("DBASE", "dbase_year_start")
      year_end    = parser.getint("DBASE", "dbase_year_end")
      purge_flag  = parser.getboolean("DBASE", "dbase_purge")
      stats_flag  = parser.getboolean("DBASE", "dbase_stats")
      self.__purge = purge_flag
      self.__stats = stats_flag
      log.setLevel(lvl)
      self.period = period
      self.setPeriod(60*period)
      try:
         if self.__conn is not None and self.__file != dbfile:
            self.__conn.close()
            self.__conn = None
         if self.__conn is None:
            log.debug("opening database %s", dbfile)
            self.__conn    = sqlite3.connect(dbfile)
         else:
            log.debug("reusing database connection to %s", dbfile)
         self.__cursor  = self.__conn.cursor()
         self.__file    = dbfile
         schema.generate(self.__conn,
                         json_dir,
                         date_fmt,
                         year_start,
                         year_end,
                         replace=False)
      except sqlite3.OperationalError, e:
         self.__conn.rollback()
         if e.args[0] != DATABASE_LOCKED:
            raise
         log.critical("Dimension Table could not be populated: %s",
                   DATABASE_LOCKED
                )
      except sqlite3.Error as e:
         log.error("Error %s:", e.args[0])
         if self.__conn:
            self.__conn.rollback()
         raise
      self.minmax.reload(self.__conn)
      self.aver5min.reload(self.__conn)
      self.realtime.reload(self.__conn)
      self.histats.reload(self.__conn)
      self.rtstats.reload(self.__conn)
      log.debug("Reload complete")
      

   # =======
   # ETL API
   # =======

   # -------------------------------
   # Process Hourly MinMax bulk dump
   # -------------------------------

   def processMinMax(self, mqtt_id, payload):
      '''extract MinMax History data and load into its table'''
      log.debug("Received minmax history message from station %s", mqtt_id)
      station_id = self.lkStation(mqtt_id)
      if station_id == UNKNOWN_STATION_ID:
         log.warn("Ignoring minmax message from unregistered station %s", 
                  mqtt_id)
         return
      rows = []
      message = payload.split('\n')
      msglen = len(message)
      for i in range(0 , msglen/3):
         date_id, time_id, t0 = xtDateTime(message[3*i+2])
         tsmp = t0.strftime("%Y-%m-%d %H:%M:%S")
         r = self.minmax.row(date_id, time_id, station_id, tsmp, message[3*i])
         rows.append(r)
         r = self.minmax.row(date_id, time_id, station_id, tsmp, message[3*i+1])
         rows.append(r)
      # It seemd there is no need to sort the dates
      # non-overlapping data do get written anyway 
      #rows = sorted(rows, key=operator.itemgetter(0,1), reverse=True)
      commited = self.minmax.insert(rows)
      if self.__stats:
         # Insert record into the statistics table
         self.histats.insert(
            self.histats.rows(station_id, TYP_MINMAX, len(rows), commited)
         )


   # -------------------------------
   # Process Current Status Messages
   # -------------------------------

   def processCurrentStatus(self, mqtt_id, payload, t1):
      '''Extract real time EMA status message and store it into its table
      t1 is the timestamp at the mqtt on_message callback.
      '''
      station_id = self.lkStation(mqtt_id)
      if station_id == UNKNOWN_STATION_ID:
         log.warn("Ignoring status message from unregistered station %s", 
                  mqtt_id)
         return
      message = payload.split('\n')
      if len(message) != 2:
         log.error("Wrong current status message from station %s", mqtt_id)
         return
      date_id, time_id, t0 = xtDateTime(message[1])

      tstamp = t0.strftime("%Y-%m-%d %H:%M:%S")
      log.debug("Received current status message from station %s", mqtt_id)

      type_m = TYP_SAMPLES
      row = self.realtime.row(date_id, time_id, station_id, type_m, tstamp, 
                              message[0])
      self.__rtwrites += self.realtime.insert((row,))
      if (self.__rtwrites % DBWritter.N_RT_WRITES) == 1:
         log.info("RealTimeSamples rows written so far: %d" % self.__rtwrites)

      # Compute and store statistics
      # lag = measured lag MQTT[local] -  RPi[remote]
      # the timestamp reference is RPi[remote]
      if self.__stats:
         lag  = int(round((t1 - t0).total_seconds()))
         nbytes = len(payload)
         num_samples = 1
         window_size = 0           # by definition (1 sample)
         self.rtstats.insert(
            self.rtstats.rows(date_id, time_id, station_id, type_m, tstamp, 
                              window_size, num_samples, nbytes, lag)
         )


   # -------------------------------
   # Process Average Status Messages
   # -------------------------------

   def processAverageStatus(self, mqtt_id, payload, t1):
      '''Extract real time EMA status message and store it into its table
      t1 is the timestamp at the mqtt on_message callback.
      '''
      station_id = self.lkStation(mqtt_id)
      if station_id == UNKNOWN_STATION_ID:
         log.warn("Ignoring status message from unregistered station %s", 
                  mqtt_id)
         return
      message = payload.split('\n')
      if len(message) != 4:
         log.error("Wrong average status message from station %s", mqtt_id)
         return
      date_id, time_id, t0 = xtDateTime(message[1])

      tstamp = t0.strftime("%Y-%m-%d %H:%M:%S")
      log.debug("Received average status message from station %s", mqtt_id)

      type_m = TYP_AVER
      row = self.realtime.row(date_id, time_id, station_id, type_m, tstamp, 
                              message[0])
      self.__rtwrites += self.realtime.insert((row,))
      if (self.__rtwrites % DBWritter.N_RT_WRITES) == 1:
         log.info("RealTimeSamples rows written so far: %d" % self.__rtwrites)

      # Compute and store statistics
      # lag = measured lag MQTT[local] -  RPi[remote]
      # the timestamp reference is RPi[remote]
      if self.__stats:
         _, _, tOldest = xtDateTime(message[2])
         num_samples = int(message[3][1:-1])
         lag  = int(round((t1 - t0).total_seconds()))
         nbytes = len(payload)
         window_size = (t0 - tOldest).total_seconds()
         self.rtstats.insert(
            self.rtstats.rows(date_id, time_id, station_id, type_m, tstamp, 
                              window_size, num_samples, nbytes, lag)
         )


   # ---------------------------------
   # Process 5 min. averaged Bulk Dump
   # ----------------------------------

   def processAveragesHistory(self, mqtt_id, payload):
      log.debug("Received averages history message from station %s", mqtt_id)
      station_id = self.lkStation(mqtt_id)
      if station_id == UNKNOWN_STATION_ID:
         log.warn("Ignoring averags history message from unregistered station %s", 
                  mqtt_id)
         return
      rows = []
      message = payload.split('\n')
      msglen = len(message)
      for i in range(0 , msglen/2):
         date_id, time_id, t0 = xtDateTime(message[2*i+1])
         tsmp = t0.strftime("%Y-%m-%d %H:%M:%S")
         r = self.aver5min.row(date_id, time_id, station_id, tsmp, message[2*i])
         rows.append(r)
      commited = self.aver5min.insert(rows)
      if self.__stats:
         # Insert record into the statistics table
         self.histats.insert(
            self.histats.rows(station_id, TYP_AVER, len(rows), commited)
         )



   # ----------------------------
   # Implement The Lazy interface 
   # ----------------------------

   def work(self):
      '''
      Called periodically from a Server object.
      Write blocking behaviour.
      '''
      log.debug("work()")
      if self.__purge:
         date_id = self.datePurgeFrom()
         if date_id:
            self.realtime.delete(date_id)
            self.rtstats.delete(date_id)

   # ------------------------------------
   # Dimensions SQL Lookup helper methods
   # ------------------------------------

   def lkType(self, meas_type):
      '''return meas_id key from meas_type'''
      self.__cursor.execute("SELECT type_id FROM Type WHERE type=?",
                            (meas_type,))
      meas_id = self.__cursor.fetchone() or (UNKNOWN_MEAS_ID,)
      log.verbose("lkType(%s) => %s", meas_type, meas_id)
      return meas_id[0]


   def lkStation(self, mqtt_id):
      '''return station_id key from mqtt_id'''
      self.__cursor.execute("SELECT station_id FROM Station WHERE mqtt_id=?",
                            (mqtt_id,))
      station_id = self.__cursor.fetchone() or (UNKNOWN_STATION_ID,)
      log.verbose("lkStation(%s) => %s", mqtt_id, station_id)
      return station_id[0]


   def lkUnits(self, roof, aux):
      '''return units_id key from units'''
      self.__cursor.execute("SELECT units_id FROM Units WHERE roof_relay=? AND aux_relay=?",
                            (roof, aux))
      units_id = self.__cursor.fetchone() or (UNKNOWN_UNITS_ID,)
      log.verbose("lkUnits(roof=%s,aux=%s) => %s", roof, aux, units_id)
      return units_id[0]

   # -------------------------------
   # Facts SQL Loader helper methods
   # -------------------------------

   def datePurgeFrom(self):
      '''Return date to purge from'''
      now      = datetime.datetime.utcnow()
      midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
      delta    = datetime.timedelta(minutes=2*self.period)
      if now - midnight < delta:
         return now.year*10000 + now.month*100 +now.day
      else:
         return None
