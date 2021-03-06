# A. REPORTING

## A.1. Dimensional Modelling


## A.2 The data model


The RealTimeSamples table is an aid for possible (more or less) real time monitoring of EMA weather stations.

Real time status messages are stored in this table. If the service runs in the background long enough, this table will be periodically purged approximately at 00:00:00 UTC to delete last days samples. 

## Data Model

The data model follows the [dimensional modelling approach by Ralph Kimball]
(https://en.wikipedia.org/wiki/Dimensional_modeling).

### Dimension Tables

* `Date` : preloaded for 10 years)
* `Time` : preloaded, minute resolution)
* `Station`: registered weather stations where to collect data
* `Type` : measurement types (`Minima`, `Maxima`, `Samples`, 'Averages', MinMax' )
* `Units`: an assorted collection of unit labels for reports

The Ùnits` table is what Dr. Kimball denotes as a *junk dimension*.

### Fact Tables

* `MinMaxHistory` : fact table contaning hourly minima and maxima measurements ffrom EMA weather stations.

* `RealTimeSamples` : fact table containing current EMA status messages.


## A.3 Sample queries

## A.4 data mode listing


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

            
            CREATE TABLE IF NOT EXISTS Time
            (
            time_id        INTEGER PRIMARY KEY, 
            time           TEXT,
            hour           INTEGER,
            minute         INTEGER,
            day_fraction   REAL
            );
            
            
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


	    CREATE TABLE IF NOT EXISTS Type
            (
            type_id        INTEGER PRIMARY KEY, 
            type           TEXT
            );

	    CREATE TABLE IF NOT EXISTS Units
            (
            units_id             INTEGER PRIMARY KEY, 
            roof_relay           TEXT,
            aux_relay            TEXT,
            voltage_units        TEXT,
            wet_units            TEXT,
            cloudy_units         TEXT,
            cal_pressure_units   TEXT,
            abs_pressure_units   TEXT,
            rain_units           TEXT,
            irradiation_units    TEXT,
            magnitude_units      TEXT,
            frequency_units      TEXT,
            temperature_units    TEXT,
            rel_humidity_units   TEXT,
            dew_point_units      TEXT,
            wind_speed_units     TEXT,
            wind_speed10m_units  TEXT,
            wind_direction_units TEXT
            );

  
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
            wind_speed10m      REAL,
            wind_direction     INTEGER,
            timestamp          TEXT,
            PRIMARY KEY (date_id, time_id, station_id, type_id)
            );



	    CREATE TABLE IF NOT EXISTS RealTimeSamples
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
            wind_speed10m      REAL,
            wind_direction     INTEGER,
            timestamp          TEXT,
            PRIMARY KEY (date_id, time_id, station_id, type_id)
            );
  
 
	    CREATE TABLE IF NOT EXISTS AveragesHistory
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
            wind_speed10m      REAL,
            wind_direction     INTEGER,
            timestamp          TEXT,
            PRIMARY KEY (date_id, time_id, station_id)
            );


            CREATE TABLE IF NOT EXISTS HistoryStats
            (
            date_id            INTEGER NOT NULL REFERENCES Date(date_id), 
            time_id            INTEGER NOT NULL REFERENCES Time(time_id), 
            station_id         INTEGER NOT NULL REFERENCES Station(station_id),
            type_id            INTEGER NOT NULL REFERENCES Type(type_id),
            records_submitted  INTEGER,
            records_committed  INTEGER,
            timestamp          TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date_id, time_id, station_id, type_id)
            );
   

	    CREATE TABLE IF NOT EXISTS RealTimeStats
            (
            date_id            INTEGER NOT NULL REFERENCES Date(date_id), 
            time_id            INTEGER NOT NULL REFERENCES Time(time_id), 
            station_id         INTEGER NOT NULL REFERENCES Station(station_id),
            type_id            INTEGER NOT NULL REFERENCES Type(type_id),
            timestamp          TEXT,
            window_size        INTEGER,
            num_samples        INTEGER,
            num_bytes          INTEGER,
            lag                INTEGER,
            PRIMARY KEY (date_id, time_id, station_id, type_id)
            );