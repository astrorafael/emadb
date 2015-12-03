import os
from setuptools import setup, Extension
import versioneer

# Default description in markdown
long_description = open('README.md').read()
 
# Converts from makrdown to rst using pandoc
# and its python binding.
# Docunetation is uploaded in PyPi when registering
# by issuing `python setup.py register`

try:
    import subprocess
    import pandoc
 
    process = subprocess.Popen(
        ['which pandoc'],
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True
    )
 
    pandoc_path = process.communicate()[0]
    pandoc_path = pandoc_path.strip('\n')
 
    pandoc.core.PANDOC_PATH = pandoc_path
 
    doc = pandoc.Document()
    doc.markdown = long_description
 
    long_description = doc.rst
 
except:
    pass
   


classifiers = [
    'Environment :: No Input/Output (Daemon)',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows :: Windows XP',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: SQL',
    'Topic :: Scientific/Engineering :: Astronomy',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'Development Status :: 4 - Beta',
]

if os.name == "posix":

  setup(name             = 'emadb',
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = 'Rafael Gonzalez',
        author_email     = 'astrorafael@yahoo.es',
        description      = 'A package to collect measurements published by EMA using MQTT and a SQlite database',
        long_description = long_description,
        license          = 'MIT',
        keywords         = 'EMA Database Meteorology Astronomy Python RaspberryPi',
        url              = 'http://github.com/astrorafael/emadb/',
        classifiers      = classifiers,
        packages         = ["emadb","emadb.server"],
        install_requires = ['paho-mqtt'],
        data_files       = [ 
          ('/etc/init.d' ,   ['init.d/emadb']),
          ('/etc/default',   ['default/emadb']),
          ('/etc/emadb',     ['config/config']),
          ('/usr/local/bin', ['scripts/emadb', 'scripts/emadbload']),
          ]
        )

elif os.name == "nt":

  import sys
  import shlex

  setup(name             = 'emadb',
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = 'Rafael Gonzalez',
        author_email     = 'astrorafael@yahoo.es',
        description      = 'A package to collect measurements published by EMA using MQTT and a SQlite database',
        long_description = long_description,
        license          = 'MIT',
        keywords         = 'EMA Database Meteorology Astronomy Python RaspberryPi',
        url              = 'http://github.com/astrorafael/emadb/',
        classifiers      = classifiers,
        packages         = ["emadb","emadb.server"],
        install_requires = ['paho-mqtt'],
        data_files       = [ 
          (r'C:\emadb\dbase' ,   ['dbase/placeholder.txt']),
          (r'C:\emadb\log',      ['log/placeholder.txt']),
          (r'C:\emadb\config',   ['config/config.ini']),
          ]
        )

  args = shlex.split( "python -m emadb --startup auto install")
  subprocess.call(args)

else:
  pass
