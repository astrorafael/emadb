# -*- coding: utf-8 -*-

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

import sys
import os
import json
import logging
import datetime
import sqlite3

# ----------------
# Module Constants
# ----------------

UNKNOWN = 'Unknown'

# -----------------------
# Module Global Variables
# -----------------------

log = logging.getLogger('schema')
connection = None

# ------------------------
# Module Utility Functions
# ------------------------

def julian_day(date):
    """Returns the Julian day number of a date at noon."""
    a = (14 - date.month)//12
    y = date.year + 4800 - a
    m = date.month + 12*a - 3
    return date.day + ((153*m + 2)//5) + 365*y + y//4 - y//100 + y//400 - 32045

def fromJSON(file_path):
    '''Read pre-populated JSON data from a file'''
    lines = []
    if not os.path.exists(file_path):
        log.error("No JSON file found in %s.", file_path)

    with open(file_path,'r') as fd:
        for line in fd:
            if not line.startswith('#'):
                lines.append(line)
    return  json.loads('\n'.join(lines))


# ============================================================================ #
#                               DATE TABLE (DIMENSION)
# ============================================================================ #
     
class Date(object):

    ONE         = datetime.timedelta(days=1)

    def __init__(self, conn, date_fmt, year_start, year_end):
        '''Create and Populate the SQLite Date Table'''
        self.__cursor  = conn.cursor()
        self.__conn  = conn
        self.__fmt   = date_fmt
        self.__start = datetime.date(year_start,1,1)
        self.__end   = datetime.date(year_end,12,31)

    def generate(self, replace):
        self.table()
        self.populate(replace)
        self.__conn.commit()

    def table(self):
        '''Create the SQLite Date Table'''
        log.info("Creating Date Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS Date
            (
            date_id        INTEGER PRIMARY KEY, 
            sql_date       TEXT, 
            date           TEXT,
            day            INTEGER,
            day_year       INTEGER,
            julian_day     REAL,
            weekday        TEXT,
            weekday_abbr   TEXT,
            weekday_num    INTEGER,
            month_num      INTEGER,
            month          TEXT,
            month_abbr     TEXT,
            year           INTEGER
            );
            """
        )


    def populate(self, replace):
        '''Populate the SQLite Date Table'''
        dates = self.rows()
        if replace:
            log.info("Replacing Date Table data")
            self.__cursor.executemany(
                "INSERT OR REPLACE INTO Date VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                dates)
        else:
            log.info("Populating Date Table if empty")
            self.__cursor.executemany(
                "INSERT OR IGNORE INTO Date VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                dates)

    # --------------
    # Helper methods
    # --------------

    def row(self, date):
        '''Generates a row of Date information'''
        return (
            date.year*10000+date.month*100+date.day, # Key
            str(date),            # SQLite date string
            date.strftime(self.__fmt),  # date string
            date.day,             # day of month
            date.strftime("%j"),  # day of year
            julian_day(date)+0.5,     # At midnight (+ or - ?????)
            date.strftime("%A"),      # weekday name
            date.strftime("%a"),      # abbreviated weekday name
            int(date.strftime("%w")), # weekday number (0=Sunday)
            date.month,               # Month Number
            date.strftime("%B"),      # Month Name
            date.strftime("%b"),      # Month Abbr. Name
            date.year,                # Year
        )


    def rows(self):
        '''Generate a list of rows to inject into the table'''
        date = self.__start
        dateList = [
            (
                -1,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN, 
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
            )
        ]
        while date <= self.__end:
            dateList.append(self.row(date))
            date = date + Date.ONE
        return dateList

# ============================================================================ #
#                               TIME OF DAY TABLE (DIMENSION)
# ============================================================================ #

class TimeOfDay(object):
    
    ONE         = datetime.timedelta(minutes=1)
    START_TIME  = datetime.datetime(year=1900,month=1,day=1,hour=0,minute=0)
    END_TIME    = datetime.datetime(year=1900,month=1,day=1,hour=23,minute=59)

    def __init__(self, conn):
        '''Create and Populate the SQlite Time of Day Table'''
        self.__cursor  = conn.cursor()
        self.__conn  = conn


    def generate(self, replace):
        self.table()
        self.populate(replace)
        self.__conn.commit()


    def table(self):
        '''Create the SQLite Time of Day table'''
        log.info("Creating Time Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS Time
            (
            time_id        INTEGER PRIMARY KEY, 
            time           TEXT,
            hour           INTEGER,
            minute         INTEGER,
            day_fraction   REAL
            );
            """
        )


    def populate(self, replace):
        '''Populate the SQLite Time Table'''
        times = self.rows()
        if replace:
            log.info("Replacing Time Table data")
            self.__cursor.executemany(
                "INSERT OR REPLACE INTO Time VALUES(?,?,?,?,?)", times)
        else:
            log.info("Populating Time Table if empty")
            self.__cursor.executemany(
                "INSERT OR IGNORE INTO Time VALUES(?,?,?,?,?)", times)

    # --------------
    # Helper methods
    # --------------

    def row(self, time):
        '''Generates a row of Time of day information'''
        return (
            time.hour*100+time.minute, # Key
            time.strftime("%H:%M"),    # SQLite time string
            time.hour,            # hour
            time.minute,          # minute
            (time.hour*60+time.minute) / (24*60.0), # fraction of day
        )


    def rows(self):
        '''Generate a list of rows to inject into the table'''
        time = TimeOfDay.START_TIME
        # Starts with the Unknown value
        timeList = [
            (
                -1,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
            )
        ]
        while time <= TimeOfDay.END_TIME:
            timeList.append(self.row(time))
            time = time + TimeOfDay.ONE
        return timeList


# ============================================================================ #
#                               STATION TABLE (DIMENSION)
# ============================================================================ #

class Station(object):

    FILE = 'stations.json'

    def __init__(self, conn, json_dir):
        '''Create and populate the SQLite Station Table'''
        self.__cursor  = conn.cursor()
        self.__conn  = conn
        self.__json_dir = json_dir


    def generate(self, replace):
        self.table()
        self.populate(replace)
        self.__conn.commit()


    def table(self):
        '''Create the SQLite Station table'''
        log.info("Creating Station Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS Station
            (
            station_id     INTEGER PRIMARY KEY, 
            mqtt_id        TEXT,
            name           TEXT,
            owner          TEXT,
            location       TEXT,
            province       TEXT,
            longitude      REAL,
            longitude_text TEXT,
            latitude       REAL,
            latitude_text  TEXT,
            elevation      REAL
            );
            """
        )


    def populate(self, replace):
        '''Populate the SQLite Station Table'''
        stations = self.rows()
        if replace:
            log.info("Replacing Station Table data")
            self.__cursor.executemany(
                "INSERT OR REPLACE INTO Station VALUES(?,?,?,?,?,?,?,?,?,?,?)", 
                stations)
        else:
            log.info("Populating Station Table if empty")
            self.__cursor.executemany(
                "INSERT OR IGNORE INTO Station VALUES(?,?,?,?,?,?,?,?,?,?,?)", 
                stations)

    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject in SQLite API'''
        return fromJSON( os.path.join(self.__json_dir, Station.FILE))


# ============================================================================ #
#                           MEASUREMENT TYPE TABLE (DIMENSION)
# ============================================================================ #

class MeasurementType(object):
    
    def __init__(self, conn):
        '''Create and populate the SQLite Measurement Table'''
        self.__cursor  = conn.cursor()
        self.__conn  = conn


    def generate(self, replace):
        self.table()
        self.populate(replace)
        self.__conn.commit()


    def table(self):
        '''Create the SQLite Measurement Type table'''
        log.info("Creating Type Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS Type
            (
            type_id        INTEGER PRIMARY KEY, 
            type           TEXT
            );
            """
        )


    def populate(self, replace):
        '''Populate the SQLite Measurement Type Table'''
        meas_types = self.rows()
        if replace:
            log.info("Replacing Type Table data")
            self.__cursor.executemany(
                "INSERT OR REPLACE INTO Type VALUES(?,?)",
                meas_types)
        else:
            log.info("Populating Type Table if empty")
            self.__cursor.executemany(
                "INSERT OR IGNORE INTO Type VALUES(?,?)", 
                meas_types)


    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list (Tuple) of rows to inject in SQLite API'''
        return (
            ( -1, UNKNOWN   ),
            (  1, "Minima"  ),
            (  2, "Maxima"  ),
            (  3, "Samples" ),
            (  4, "Averages" ),
        )

# ============================================================================ #
#                               UNITS TABLE (DIMENSION)
# ============================================================================ #

class Units(object):

    FILE = 'units.json'
    
    def __init__(self, conn, json_dir):
        '''Create and populate the SQLite Units Table'''
        self.__cursor  = conn.cursor()
        self.__conn    = conn
        self.__json_dir = json_dir


    def generate(self, replace):
        self.table()
        self.populate(replace)
        self.__conn.commit()


    def table(self):
        '''Create the SQLite Units table'''
        log.info("Creating Units Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS Units
            (
            units_id           INTEGER PRIMARY KEY, 
            roof_relay         TEXT,
            aux_relay          TEXT,
            voltage_units      TEXT,
            wet_units          TEXT,
            cloudy_units       TEXT,
            cal_pressure_units TEXT,
            abs_pressure_units TEXT,
            rain_units         TEXT,
            irradiation_units  TEXT,
            magnitude_units    TEXT,
            frequency_units    TEXT,
            temperature_units  TEXT,
            rel_humidity_units TEXT,
            dew_point_units    TEXT,
            wind_speed_units   TEXT,
            wind_direction_units TEXT,
            lag_units          TEXT
            );
            """
        )


    def populate(self, replace):
        '''Populate the SQLite Units Table'''
        units = self.rows()
        if replace:
            log.info("Replacing Units Table data")
            self.__cursor.executemany(
                "INSERT OR REPLACE INTO Units VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                units)
        else:
            log.info("Populating Units Table if empty")
            self.__cursor.executemany(
                "INSERT OR IGNORE INTO Units VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                units)

    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject in SQLite API'''
        return fromJSON( os.path.join(self.__json_dir, Units.FILE))

# ============================================================================ #
#                               MINMAX TABLE (PERIODIC SNAPSHOT FACT)
# ============================================================================ #

class MinMaxHistory(object):
    
    def __init__(self, conn):
        '''Create the SQLite MinMax Table'''
        self.__cursor  = conn.cursor()
        self.__conn  = conn


    def generate(self):
        self.table()
        self.__conn.commit()


    def table(self):
        '''Create the SQLite MinMaxHistory table'''
        log.info("Creating MinMaxHistory Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS MinMaxHistory
            (
            date_id            INTEGER NOT NULL REFERENCES Date(date_id), 
            time_id            INTEGER NOT NULL REFERENCES Time(time_id), 
            station_id         INTEGER NOT NULL REFERENCES Station(station_id),
            type_id            INTEGER NOT NULL REFERENCES Type(type_id),
            units_id           INTEGER NOT NULL REFERENCES Units(units_id),
            voltage            REAL,
            wet                REAL,
            cloudy             REAL,
            cal_pressure       REAL,
            abs_pressure       REAL,
            rain               REAL,
            irradiation        REAL,
            vis_magnitude      REAL,
            frequency          REAL,
            temperature        REAL,
            rel_humidity       REAL,
            dew_point          REAL,
            wind_speed         REAL,
            wind_direction     INTEGER,
            timestamp          TEXT,
            PRIMARY KEY (date_id, time_id, station_id, type_id)
            );
            """
        )


# ============================================================================ #
#                   REAL TIME SAMPLES TABLE (PERIODIC SNAPSHOT FACT)
# ============================================================================ #

class RealTimeSamples(object):
    
    def __init__(self, conn):
        '''Create the SQLite RealTimeSamples Table'''
        self.__cursor  = conn.cursor()
        self.__conn  = conn


    def generate(self):
        self.table()
        self.__conn.commit()


    def table(self):
        '''Create the SQLite Units table'''
        log.info("Creating RealTimeSamples Table if not exists")
        self.__cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS RealTimeSamples
            (
            date_id            INTEGER NOT NULL REFERENCES Date(date_id), 
            time_id            INTEGER NOT NULL REFERENCES Time(time_id), 
            station_id         INTEGER NOT NULL REFERENCES Station(station_id),
            units_id           INTEGER NOT NULL REFERENCES Units(units_id),
            voltage            REAL,
            wet                REAL,
            cloudy             REAL,
            cal_pressure       REAL,
            abs_pressure       REAL,
            rain               REAL,
            irradiation        REAL,
            vis_magnitude      REAL,
            frequency          REAL,
            temperature        REAL,
            rel_humidity       REAL,
            dew_point          REAL,
            wind_speed         REAL,
            wind_direction     INTEGER,
            timestamp          TEXT,
            lag1               INTEGER,
            lag2               INTEGER,
            PRIMARY KEY (date_id, time_id, station_id)
            );
            """
        )


def generate(connection, json_dir, date_fmt, year_start, year_end, 
             replace=False):

    '''Schema Generation. The main function'''
    Date(connection, date_fmt, year_start, year_end).generate(replace)
    TimeOfDay(connection).generate(replace)
    Station(connection,json_dir).generate(replace)
    MeasurementType(connection).generate(replace)
    Units(connection,json_dir).generate(replace)
    MinMaxHistory(connection).generate()
    RealTimeSamples(connection).generate()

if __name__ == "__main__":
    from server import logger

    logger.logToConsole()
    if not os.path.exists(sys.argv[1]):
        log.error("No SQLite3 Database file found in %s. Exiting ...",
                  sys.argv[1])
        sys.exit(1)
		
    try:
        connection = sqlite3.connect(sys.argv[1])
        generate(connection, 2015, 2025, 'config', replace=True)
    except sqlite3.Error as e:
        if connection:
            connection.rollback()
            log.error("Error %s:", e.args[0])
            sys.exit(1)
    finally:
        if connection:
            connection.close() 
