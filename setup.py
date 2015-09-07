from setuptools import setup, Extension
import versioneer

classifiers = [
    'Environment :: No Input/Output (Daemon)',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows :: Windows XP',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: SQL'
    'Topic :: Scientific/Engineering :: Astronomy'
'    Topic :: Scientific/Engineering :: Atmospheric Science'
    'Development Status :: 4 - Beta',
]



setup(name             = 'emadb',
      version          = versioneer.get_version(),
      cmdclass         = versioneer.get_cmdclass(),
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
