# EMADB

Linux service to collect measurements pubished by EMA via MQTT.
EMA stands for [Cristobal Garcia's EMA Weather Station](http://www.observatorioremoto.com/emav2/meteoen.htm)

Description
-----------

**emadb** is a software package that collects measurements from one or several
EMA wheather stations into a SQLite Database. 

Reporting applicatons may query the database to generate repots and graphs
using historic data. You can also monitor current station status

Three data sources are available:

+ Per hour minima and maxima values (historic data)
+ 5 min. individual samples (historic data) (NOT YET IMPLEMENTED)
+ individual samples (real time, 1 min. aprox)

**Warning**: Time handled by EMA is UTC, not local time.

## Installation & Configuration

### Linux installation (Debian)

Simply type:

  `sudo ./setup.sh`

All executables are copied to /usr/local/bin

Type `sudo emadb` to start the service in foreground with console output

An available startup service script for debian-based systems is provided. 
Type `sudo service emad start` to start it
Type `sudo update-rc.d emad defaults` to install it at boot time

### EMA Server Configuation

By default, file `/etc/emadb/config` provdes the configuration options needed.
This file is self explanatory. In special, the database file name and location is specified in this file.

### Reloadable Parameters

The emadb service supports on-line reconfiguration on a limited subset of parameters.
This means that you will not loose incoming data while changing these parameters.
The list is listed below:

    [GENERIC]
    # If true, the EMADB server will hold incoming MQTT messages instead of 
    # writting them to the SQL database
    # Useful to perform online database maintenance
    on_hold = no
    # component log level (DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET)
    generic_log = INFO

    [DBASE]
    # Full Database Path File Name
    dbase_file = emahistory.db
    # Directory where JSON data is located
    dbase_json_dir = config
    # Period for periodic task execution [minutes]
    dbase_period = 1
    # Limit years (included) for the Date dimension (from Jan 1 to Dec 12)
    dbase_year_start = 2015
    dbase_year_end   = 2035
    # component log level (VERBOSE, DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET)
    dbase_log = DEBUG

    [MQTT]
    # MQTT topics to subscribe
    # reconfigurable by reload
    mqtt_topics= EMA/+/history/minmax,EMA/+/current/status
    # component log level (VERBOSE, DEBUG, INFO, WARNING, ERROR, CRITICAL, NONSET)
    mqtt_log = INFO

### Logging

Log file is usually placed under `/var/log/emad.log`. 
Default log level is INFO. It generates very litte logging at this level
File is rotated by the application itself. Two strategies are supported:

+ Daily rotations at midnight. Useful if the service runs for a long time
+ Size-based rotation. Useful if service is starte/stopped several times during the day.

## Operation

### Service start/stop/restart/reload

In Linux, this is done using the well-known init.d script with parameters:

    sudo service emadb status
    sudo service emadb start
    sudo service emadb restart
    sudo service emadb reload
    sudo service emadb stop
    
The `service emadb restart` will stop and start the process, loosing the MQTT & database connections.

The `service emadb reload` will keep the MQTT connection intact.

### On hold mode

The service can be set to an *on_hold* mode where incoming messages are enqueued in RAM
instead of being written to the SQLite file. This can be useful to perform various database maintenance activities, whcih can include:

* Data Migration & clean up
* VACUUM
* etc.

To do so, set the `on_hold` flag in the config file to yes and reload

### Updating the registered stations list ##

emadb will only insert incoming MQTT data if the EMA station is previously registered in the database.While you can update the database itself using SQL commands, the preferred approach is to edit the master dimension JSON files, usually stored in the `/etc/emadb` directory.

Edit the files using your favorite editor. Beware, JSON is picky with the syntax.

To **append** new data in these files, simply reload or restart the service.
To **modify** existing data (i.e. changing longitude, latitude of existing stations), use the emadbload utility.

Type `sudo emadbload -h` to see the command line arguments

### Real Time Data 

The RealTimeSamples table is an aid for possible (more or less) real time monitoring of EMA weather stations.

Real time status messages are stored in this table. If the service runs in the background long enough, this table will be periodically purged approximately at 00:00:00 UTC to delete last days samples. 

## Data Model

The data model follows the [dimensional modelling approach by Ralph Kimball]
(https://en.wikipedia.org/wiki/Dimensional_modeling)

### Dimension Tables

* `Date` : preloaded for 10 years)
* `Time` : preloaded, minute resolution)
* `Station`: registered weather stations where to collect data
* `Type` : measurement types (`Minima`, `Maxima`, `Samples` )
* `Units`: an assorted collection of unit labels for reports

The Ùnits` table is what Dr. Kimball denotes as a *junk dimension*.

### Fact Tables

* `MinMaxHistory` : fact table contaning hourly minima and maxima measurements ffrom EMA weather stations.

* `RealTimeSamples` : fact table containing current EMA status messages

### DDL

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


            CREATE TABLE IF NOT EXISTS Units
            (
            units_id                INTEGER PRIMARY KEY, 
            roof_relay              TEXT,
            aux_relay               TEXT,
            voltage                 TEXT,
            rain_probability        TEXT,
            clouds_level            TEXT,
            cal_pressure            TEXT,
            abs_pressure            TEXT,
            rain_level              TEXT,
            irradiantion            TEXT,
            visual_magnitude        TEXT,
            instrumental_magnitude  TEXT,
            temperature             TEXT,
            relative_humidity       TEXT,
            dew_point               TEXT,
            wind_speed              TEXT,
            wind_direction          TEXT,
            lag                     TEXT
            );
  
            CREATE TABLE IF NOT EXISTS MinMaxHistory
            (
            date_id                 INTEGER NOT NULL REFERENCES Date(date_id), 
            time_id                 INTEGER NOT NULL REFERENCES Time(time_id), 
            station_id          INTEGER NOT NULL REFERENCES Station(station_id),
            type_id                 INTEGER NOT NULL REFERENCES Type(type_id),
            units_id                INTEGER NOT NULL REFERENCES Units(units_id),
            voltage                 REAL,
            rain_probability        REAL,
            clouds_level            REAL,
            cal_pressure            REAL,
            abs_pressure            REAL,
            rain_level              REAL,
            irradiantion            REAL,
            visual_magnitude        REAL,
            instrumental_magnitude  REAL,
            temperature             REAL,
            relative_humidity       REAL,
            dew_point               REAL,
            wind_speed              REAL,
            wind_direction          INTEGER,
            PRIMARY KEY (date_id, time_id, station_id, type_id)
            );

            CREATE TABLE IF NOT EXISTS RealTimeSamples
            (
            date_id                 INTEGER NOT NULL REFERENCES Date(date_id), 
            time_id                 INTEGER NOT NULL REFERENCES Time(time_id), 
            station_id          INTEGER NOT NULL REFERENCES Station(station_id),
            units_id                INTEGER NOT NULL REFERENCES Units(units_id),
            voltage                 REAL,
            rain_probability        REAL,
            clouds_level            REAL,
            cal_pressure            REAL,
            abs_pressure            REAL,
            rain_level              REAL,
            irradiantion            REAL,
            visual_magnitude        REAL,
            instrumental_magnitude  REAL,
            temperature             REAL,
            relative_humidity       REAL,
            dew_point               REAL,
            wind_speed              REAL,
            wind_direction          INTEGER,
            lag                     INTEGER,
            PRIMARY KEY (date_id, time_id, station_id)
            );
  
 