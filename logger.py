#!/bin/usr/python3

import logging
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'output.log')

logger = logging.getLogger('transatlanticTorrentExpress')
logger.setLevel(logging.DEBUG)

if not os.path.isfile(LOG_FILE):
  print('Log file does not exist yet, creating in project folder')
  f = open(LOG_FILE, 'w+')
  f.close()

fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s %(levelname)8s | %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
