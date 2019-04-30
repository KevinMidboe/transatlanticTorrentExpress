#!/bin/usr/python3
import os
from configparser import ConfigParser

def getConfig():
  # logger.debug('Reading config')
  pwd = os.path.dirname(os.path.abspath(__file__))
  path = os.path.join(pwd, 'config.ini')

  if not os.path.isfile(path):
    print('Please fill out and rename config file. Check README for more info.')
    exit(0)

  config = ConfigParser()
  config.read(path)

  # logger.debug('Sections parsed: {}'.format(config.sections()))
  return config