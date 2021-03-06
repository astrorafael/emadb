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


#
# Constants belinging the EMA Protocol v2, for portability issues
# EMA protocol is sometimes revised
#

LAG = 2

# OFFSETS IN GEHERAL STATUS MESSAGE
# 'end' constants are 1 character past the given field , 
# to directly use in string slicing with [:]

SRRB = 1                        # Status Roof Relay Begin
SRRE = SRRB + 1                 # Status Roof Relay End

SARB = 2                        # Status Aux Relay Begin
SARE = SARB + 1                 # Status Aux Relay End

SPSB = 3                        # Status Power Supply Begin
SPSE = SPSB + LAG + 1           # Status Power Supply End

SRAB = 5 + LAG			# Status Rain Detector Begin
SRAE = SRAB + 3                 # Status Rain Detector End

SCLB = 9 + LAG			# Status Cloud sensor Begin
SCLE = SCLB + 3                 # Status Cloud Sensor Emd

SCBB = 13 + LAG          # Status Calibrated Barometric pressure Begin
SCBE = SCBB + 5          # Status Calibrated Barometric oressure End

SABB = 19 + LAG            # Status Absolute Barometric pressure Begin
SABE = SABB + 5            # Status Absolute Barometric pressuer End

SPCB = 25 + LAG               # Status Pluviometer Current value Begin
SPCE = SPCB +  4              # Status Pluviometer Current value End

SPAB = 30 + LAG           # Status Pluviometer Accumulated value Begin
SPAE = SPAB + 4           # Status Pluviometer Accumulated value End

SPYB = 35 + LAG			# Status Pyrometer Begin
SPYE = SPYB + 3                 # Status Pyrometer End

SPHB = 39 + LAG			# Status Photometer Begin
SPHE = SPHB + 5                 # Status Photometer End

SATB = 45 + LAG			# Status Ambient Temperature Begin
SATE = SATB + 4                 # Status Ambient Temperature End

SRHB = 50 + LAG			# Status Relative Humidity Begin
SRHE = SRHB + 3                 # Status Relative Humidity End

SDPB = 54 + LAG			# Status Dew Point Begin
SDPE = SDPB + 4                 # Status Dew Point End

SAAB = 64 + LAG			# Status Anemometer Accumlated value Begin
SAAE = SAAB + 3              # Status Anemometer Accumulated value End

SACB = 68 + LAG			# Status Anemometer Current wind Begin
SACE = SACB + 4                 # Status Anemometer Curent wind End

SWDB = 73 + LAG			# Status Wind Direction Begin
SWDE = SWDB + 3                 # Status Wind direction End

SMTB = 77 + LAG			# Status Message Type Begin
SMTE = SMTB + 1                 # Status Message Type End

# Status Message Types
MTCUR = 'a'			# Current values status message type
MTHIS = 't'			# 24h historic values message type
MTISO = '0'			# 24h isolated historic values message type
MTMIN = 'm'			# daily minima message type
MTMAX = 'M'			# daily maxima message type
MTPRO = 'p'                     # Average of N cuurent messages (type=a)


# Timestamp format, the EMA way
STRFTIME = "(%H:%M:%S %d/%m/%Y)"

import math

def encodeFreq(hertz):
    '''Encode frequency in Hertz into EMA format field'''
    hertz *= 1000               # to milihertz
    exp = 0
    while hertz > 9999:
        hertz /= 10
        exp += 1
    return "%d%04d" % (exp, hertz)
        
def decodeFreq(enc):
    '''
    Decode a EMMMM frequency EMA format fragment. 
    Returns frequency in Hertz
    '''
    exp = int(enc[0])-3
    mant = int(enc[1:5])
    return mant*math.pow(10, exp)
        
# --------------------------------------------------------------------
# Visual magnitude computed by the following C function
# --------------------------------------------------------------------
# float HzToMag(float HzTSL ) 
# {
#  float mv;
#     mv = HzTSL/230.0;             // Iradiancia en (uW/cm2)/10
#     if (mv>0){
#        mv = mv * 0.000001;       //irradiancia en W/cm2
#        mv = -1*(log10(mv)/log10(2.5));    //log en base 2.5
#        if (mv < 0) mv = 24;
#     }
#     else mv = 24;
#
#     return mv;
#}
# --------------------------------------------------------------------


K_INV_LOG10_2_5 = 1.0/math.log10(2.5)
K_INV_230      = (1.0/230)

# When everithing goes wrong
MAG_CLIP_VALUE = 24

def magnitude(frequency):
   '''Extract and Transform into Visual maginitued per arcsec 2'''
   mv = frequency * K_INV_230 * 1.0e-6
   if mv > 0.0:
      mv = -1.0 * math.log10(mv) * K_INV_LOG10_2_5
      mv = MAG_CLIP_VALUE if mv < 0.0 else mv
   else:
      mv = MAG_CLIP_VALUE
   return round(mv,1)
