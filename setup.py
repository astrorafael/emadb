from setuptools import setup, Extension

classifiers = ['Development Status :: 3 - Alpha',
               'Operating System :: POSIX :: Linux',
               'Operating System :: Windows',
               'License :: OSI Approved :: MIT License',
               'Intended Audience :: Developers',
               'Programming Language :: Python :: 2.7',
               'Topic :: Astronomy',
               'Topic :: Meteorology',
               'Topic :: Raspberry Pi',
               'Development Status :: 4 - Beta',
               ]

setup(name             = 'EMADB',
      version          = '0.1.0',
      author           = 'Rafael Gonzalez',
      author_email     = 'astrorafael@yahoo.es',
      description      = 'A package to collect measurements published by EMA using MQTT and a SQlite database',
      long_description = open('README.md').read(),
      license          = 'MIT',
      keywords         = 'EMA Database Meteorology Astronomy Python RaspberryPi',
      url              = 'http://github.com/astrorafael/emadb/',
      classifiers      = classifiers,
      packages         = ["emadb","emadb.server"],
      )
