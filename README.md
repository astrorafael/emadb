EMADB
=====

Linux service to collect measurements pubished by EMA via MQTT.
EMA stands for [Cristobal Garcia's EMA Weather Station](http://www.observatorioremoto.com/emav2/meteoen.htm)

Description
-----------

**emadb** is a software package that collects measurements from one or several
EMA wheather stations into a SQLite Database. 

Reporting applicatons may query the database to generate repots and graphs
using historic data.

Two data sources are available:
1. Per hour minima and maxima values
2. 5 min. individual samples

Instalation & Configuration
---------------------------

Simply type:

  `sudo ./setup.sh`

All executables are copied to /usr/local/bin

Type `sudo emadb -k` to start the service on foreground with console output

An available startup service script for debian-based systems is provided. 
Type `sudo service emad start` to start it
Type `sudo update-rc.d emad defaults` to install it at boot time

### EMA Server Configuation ###

By default, file `/etc/emadb/config` provdes the configuration options needed.
This file is self explanatory.
In special, the database file name and location is specified in the config file.

### Logging ###

Log file is placed under `/var/log/emad.log`. 
Default log level is INFO. It generates very litte logging at this level
File is rotated by the application itself. Two strategies are supported:
- Daily rotations at midnight. Useful if the service runs for a long time
- Size-based rotation. Usefull if service is starte/stopped several times during the day.

## Updating the preloaded data ##

Stations and Unit data is preloaded from JSON files in the `/etc/emadb` directory.

Edit the files, adding new ids, labels and data (specially for the stations)
Then execute `emadbload <database path>` to update these tables.

Data Model
----------

The data model follows the [dimensional modelling approach by Ralph Kimball]
(https://en.wikipedia.org/wiki/Dimensional_modeling)

## Dimensions

 * `Date` : preloaded for 10 years)
 * `Time` : preloaded, minute resolution)
 * `Station`: registered weather stations where to collect data
 * `Type` : measurement types (`Minima`, `Maxima`, `Samples` )
 * `Units`: an assorted collection of unit labels for reports

## Facts

* `MinMaxHistory` : fact table contaning hourly minima and maxima measurements ffrom EMA weather stations.


