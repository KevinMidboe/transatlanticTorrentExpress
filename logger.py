#!/bin/usr/python3

import logging
import os
import json
import math
import uuid
import datetime
import urllib.request

from utils import getConfig

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

class ESHandler(logging.Handler):
  def __init__(self, *args, **kwargs):
    self.host = kwargs.get('host')
    self.port = kwargs.get('port')
    self.ssl = kwargs.get('ssl') or False
    self.apiKey = kwargs.get('apiKey')
    self.date = datetime.date.today()
    self.sessionID = uuid.uuid4()
    self.pid = str(os.getpid())

    logging.StreamHandler.__init__(self)

  def emit(self, record):
    self.format(record)
    indexURL = 'http://{}/transatlantic_torrent_express/_doc'.format(self.host, self.date.strftime('%Y.%m'))
    headers = { 'Content-Type': 'application/json', 'User-Agent': 'transatlanticTorrentExpress/v0.1'}
    if self.ssl:
      indexURL = indexURL.replace('http', 'https')
    if self.port:
      indexURL = indexURL.replace(self.host, '{}:{}'.format(self.host, self.port))

    if self.apiKey:
      headers['Authorization'] = 'ApiKey {}'.format(self.apiKey)

    doc = {
      'severity': record.levelname,
      'message': record.message,
      '@timestamp': math.trunc(record.created*1000),
      'sessionID': str(self.sessionID),
      'pid': self.pid
    }

    if hasattr(record, 'es'):
      for key in record.es.keys():
        if key == 'files':
          record.es[key] = [ file.__repr__() for file in record.es[key] ]

      for param in record.es.values():
        if ': {}'.format(param) in record.message:
          doc['message'] = record.message.replace(': {}'.format(str(param)), '')

      doc = {**record.es, **doc}

    payload = json.dumps(doc).encode('utf8')
    req = urllib.request.Request(indexURL, data=payload, headers=headers)

    try:
        response = urllib.request.urlopen(req)
        response = response.read().decode('utf8')
        return response
    except urllib.error.HTTPError as e:
        print('Unable to reach elastic, error:', e)
        return

class ElasticFieldParameterAdapter(logging.LoggerAdapter):
  def __init__(self, logger, extra={}):
    super().__init__(logger, extra)

  def process(self, msg, kwargs):
    if kwargs == {}:
      return (msg, kwargs)
    extra = kwargs.get("extra", {})
    extra.update({"es": kwargs.pop("es", True)})
    kwargs["extra"] = extra
    return (msg, kwargs)

config = getConfig()
esHost = config['ELASTIC']['host']
esPort = config['ELASTIC']['port']
esSSL = config['ELASTIC']['ssl']
esApiKey = config['ELASTIC']['api_key']
esEnabled = config['ELASTIC']['enabled']
if esEnabled == 'True':
  eh = ESHandler(host=esHost, port=esPort, ssl=esSSL, apiKey=esApiKey)
  eh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)8s | %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
if esEnabled == 'True':
  logger.addHandler(eh)
logger = ElasticFieldParameterAdapter(logger)
