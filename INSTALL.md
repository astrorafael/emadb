# A. INSTALLATION

## A.1. Requirements

The following components should be installed first:

 * python 2.7.x (tested on Ubunti python 2.7.6 & Windows XP python 2.7.10)
 * [Python PAHO MQTT module](https://pypi.python.org/pypi/paho-mqtt/1.1), downloadable via pip (Linux/Windows)
 * [Python for Windows Extensions](http://sourceforge.net/projects/pywin32/). Must choose python27 builds. (tested on build 219, for python27 windows 32bits)

The Windows python 2.7 distro comes with the pip utility included. Open a CMD window and type:

    pip install paho-mqtt
    
## A.2 Linux installation (Debian)

### A.2.1 Installation
1. Download the zip or tar.gz from GitHub
2. Uncompress in a temporary folder
3. Simply type:

  `sudo ./setup.sh`


* All executables are copied to `/usr/local/bin`
* The database is located at `/etc/dabse/emahistory.db` by default
* The log file is located at `/var/log/emadb.log`

### A.2.2 Start up Verification

Type `sudo emadb` to start the service in foreground with console output.

Type `sudo service emad start` to start it as a backgroud service.
Type `sudo update-rc.d emad defaults` to start it at boot time.

## A.3. Windows installation

### A.3.1 Installation

1. Download the zip or tar.gz from GitHub
2. Uncompress it into `C:\emadb`
3. Open a `CMD.exe` console
4. Inside this new created folder type:

 `sudo .\setup.bat`

* The executables (.bat files) are located in the same folder `C:\emadb`
* The database is located at `C:\emadb\dbase` by default. It is strongly recommeded that you leave it there.
* The log file is located at `C:\emadb\log\emadb.log`

### A.3.2 Start up and Verification

In the same CMD console, type`.\emadb.bat`to start it in forground and verify that it works.

Type .\start_service.bat to start it as a Windows Service.

# B. CONFIGURATION

There is a small configuration file for this service:

* `/etc/emadb/config` (Linux)
* `/etc/emadb/config.ini` (Windows)

This file is self explanatory. 
In special, the database file name and location is specified in this file.

## B.1. Reloadable Parameters

The emadb service supports on-line reconfiguration on a limited subset of parameters.
This means that you will not loose incoming data while changing these parameters.
The list is listed below:

    [GENERIC]
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
    dbase_year_end   = 2025
    # Auto Purge RealTimeSamples table every day (at midnight UTC)
    # or let it grow
    dbase_purge = no

    # component log level (VERBOSE, DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET)
    dbase_log = DEBUG

    [MQTT]
    # MQTT topics to subscribe
    # reconfigurable by reload
    mqtt_topics= EMA/+/history/minmax,EMA/+/current/status
    # component log level (VERBOSE, DEBUG, INFO, WARNING, ERROR, CRITICAL, NONSET)
    mqtt_log = INFO

### B.2. Logging

Log file is usually placed under `/var/log/emad.log` in Linux or `C:\emadb\log` on Windows. 
Default log level is `INFO`. It generates very litte logging at this level.
File is rotated by the application itself. Two strategies are supported:

+ Daily rotations at midnight. Useful if the service runs for a long time.
+ Size-based rotation. Useful if service is starte/stopped several times during the day.


### B.3 Updating the registered stations list

**emadb will only insert incoming MQTT data if the EMA station is previously registered in the database**. While you can update the database itself using SQL commands, the preferred approach is to edit the master dimension JSON files, usually stored in the `/etc/emadb` directory (Linux) or `C:\emadb\config` (Windows).

Edit the files using your favorite editor. Beware, JSON is picky with the syntax.

* To **append** new data in these files, simply reload or restart the service.
* To **modify** existing data (i.e. changing longitude, latitude of existing stations), use the emadbload utility.

	* *Linux:* Type `sudo emadbload -h` to see the command line arguments.
	* *Windows:* Double-click to execute on the `C:\emadb\scrips\emadbload.py` file

# C. OPERATION

## C.1 Server Start/Stop/Restart

### C.1.1 Linux

* Service status: `sudo service emadb status`
* Start Service:  `sudo service emadb start`
* Stop Service:   `sudo service emadb stop`
* Restart Service: `sudo service emadb restart`. A service restart kills the process and then starts a new one

    sudo service emadb reload

### C.2.2 Windows

The start/stop/restart/pause operations can be performed with the Windows service GUI tool
**If the config.ini file is not located in the usual locatioon, you must supply its path to the tool as extra arguments**

From the command line:

* Start Service:  Click on the `start_service.bat` file
* Stop Service:   Click on the `stop_service.bat` file
* Restart Service: `????`. A server restart kills the process and then starts a new one

## C.2 Server Pause

The server can be put in *pause mode*, in which will be still receiving incoming MQTT messages but will be internally enquued and not written to the database. This is usefull to perform delicate operations on the database without loss of data. Examples:

* Compact the database usoing the SQLite VACUUM pragma
* Migrating data from tables.
* etc.

### C.2.1 Linux

To pause the server, type: `sudo service emadb pause` and watch the log file output wit `tail -f /var/log/emadb.log`

To resume normal operation type again the same command and observe the same log file.

### C.2.2 Windows

## C.3 Service reload

During a reloadn the service is not stopped and re-reads the new values form the configuration file and apply the changes. In general, all aspects not related to maintaining the current connection to the MQTT broker can be relaoded. The full list is sescribed in the section B above.

* *Linux:* The `service emadb reload` will keep the MQTT connection intact. 
* *Windows:* There is no GUI button in the service tool for a reload. You must execute an auxiliar script `C:\emadb\scripts\winreload.py` by double-clicking on it. 

In both cases, watch the log file to ensure this is done.

  
 