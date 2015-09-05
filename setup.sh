#!/bin/bash
# EMA setup script

# Only needed for standalone deployment
# I use Ansible, instead

# Prerequisites python2.7 and setuptools

echo
echo "------------------------"
echo "Installing EMADB Package"
echo "------------------------"

python setup.py install

# ----------------------------
# Copy scripts
# can be overriden every time
# just like the python modules
# ----------------------------

echo
echo "---------------"
echo "Copying scripts"
echo "---------------"

# daemon in foreground utility
cp -vf scripts/emadb.sh  /usr/local/bin/emadb
chmod 0755 /usr/local/bin/emadb

# emadb loader
cp -vf scripts/emadbload.py  /usr/local/bin/emadbload
chmod 0755 /usr/local/bin/emadbload

# init.d service script
cp -vf emadb.init.sh /etc/init.d/emadb
chmod 0755 /etc/init.d/emadb

# --------------------------------------------------
# Copy config files only once
# (be polite with with your existing configurations)
# --------------------------------------------------


echo
echo "--------------------------"
echo "Copying emadb config files"
echo "--------------------------"


if [ ! -d "/var/dbase" ]; then
    echo "creating /var/dbase as the default database directory"
    mkdir /var/dbase 2>/dev/null 1>/dev/null
fi

# python config file and JSON files

if [ ! -d "/etc/emadb" ]; then
    echo "creating /etc/emadb as the default config directory"
    mkdir /etc/emadb 2>/dev/null 1>/dev/null
fi

for file in config stations.json units.json
do
    if [ ! -f "/etc/emadb/$file" ]; then
	cp -vf config/$file /etc/emadb/
	chmod 0644 /etc/emadb/$file
    else
	echo "skipping /etc/emadb/$file"
    fi
done

# service defaults file

if [ ! -f "/etc/default/emadb" ]; then
    cp -vf default /etc/default/emadb
else
    echo "skipping /etc/default/emadb"
fi


# Display EMADB usages
echo
echo "============================"
echo "EMADB successfully installed"
echo "============================"
