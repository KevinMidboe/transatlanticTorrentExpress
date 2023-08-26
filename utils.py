#!/bin/usr/python3
import os
from configparser import RawConfigParser, NoOptionError

pwd = os.path.dirname(os.path.abspath(__file__))

AVG_SPEED_FILE = '.avgspeed.txt'
VIDEO_EXTENSIONS = ('.3g2', '.3gp', '.3gp2', '.3gpp', '.60d', '.ajp', '.asf', '.asx', '.avchd', '.avi', '.bik',
                    '.bix', '.box', '.cam', '.dat', '.divx', '.dmf', '.dv', '.dvr-ms', '.evo', '.flc', '.fli',
                    '.flic', '.flv', '.flx', '.gvi', '.gvp', '.h264', '.m1v', '.m2p', '.m2v', '.m4e',
                    '.m4v', '.mjp', '.mjpeg', '.mjpg', '.mkv', '.moov', '.mov', '.movhd', '.movie', '.movx', '.mp4',
                    '.mpe', '.mpeg', '.mpg', '.mpv', '.mpv2', '.mxf', '.nsv', '.nut', '.ogg', '.ogm' '.ogv', '.omf',
                    '.ps', '.qt', '.ram', '.rm', '.rmvb', '.swf', '.ts', '.vfw', '.vid', '.video', '.viv', '.vivo',
                    '.vob', '.vro', '.wm', '.wmv', '.wmx', '.wrap', '.wvx', '.wx', '.x264', '.xvid')

class NoneOptionConfigParser(RawConfigParser):
  def get(self, section, option):
    try:
      return RawConfigParser.get(self, section, option)
    except NoOptionError:
      return None

def getConfig():
  # logger.debug('Reading config')
  pwd = os.path.dirname(os.path.abspath(__file__))
  path = os.path.join(pwd, 'config.ini')

  if not os.path.isfile(path):
    print('Please fill out and rename config file. Check README for more info.')
    exit(0)

  config = NoneOptionConfigParser()
  config.read(path)

  # logger.debug('Sections parsed: {}'.format(config.sections()))
  return config

def writeAvgSpeedToDisk(speed):
  path = os.path.join(pwd, AVG_SPEED_FILE)

  with open(path, 'w') as f:
    f.write(str(int(speed)))
    f.close()

def readAvgSpeedFromDisk():
  path = os.path.join(pwd, AVG_SPEED_FILE)

  with open(path, 'r') as f:
    data = f.readline()
    f.close()

  speed = None
  try:
    speed = int(data)
  except:
    pass

  return speed
