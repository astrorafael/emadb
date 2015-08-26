#!/bin/bash
# EMA setup script

# Only needed for standalone deployment
# I use Ansible, instead

# Preresuisites python2.7 and setuptools

echo
echo "Installing EMADB Package..."
echo

python setup.py install

# Add config files 
echo "Copying emadb config files ..."
if [ ! -d "/etc/emadb" ]; then
    mkdir /etc/emadb 2>/dev/null 1>/dev/null
    echo "Creating directory /etc/emadb ..."
fi

for file in config stations.json units.json
do
    echo "Copying $file into /etc/emadb ..."
    cp -vf config/$file /etc/emadb/
    chmod 0644 /etc/emadb/$file
done

# Add service/daemon script if it does not exists
echo "Installing service script..."
cp -vf emad.init.sh /etc/init.d/emadb
chmod 0755 /etc/init.d/emadb

# Add service defaults file if it does not exist
if [ ! -f "/etc/default/emadb" ]; then
    echo "Copying defaults for emadb service script ..."
    cp -vf default /etc/default/emadb
fi

# Adding utlity scripts
echo "Copying emadb into /usr/local/bin ..."
cp -vf scripts/emadb.sh  /usr/local/bin/emadb
chmod 0755 /usr/local/bin/emadb

echo "Copying emadbloader into /usr/local/bin ..."
cp -vf scripts/emadbloader.py  /usr/local/bin/emadbloader
chmod 0755 /usr/local/bin/emadbloader

# Display EMADB usages
echo
echo "EMADB successfully installed"
echo "* To start EMADB daemon in the foreground\t: sudo emadb"
echo
echo "* To start EMADB Daemon background\t: sudo service emadb start"
echo "* To start EMADB Daemon at boot\t: sudo update-rc.d emadb defaults"
