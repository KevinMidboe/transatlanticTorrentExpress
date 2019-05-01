#!/bin/usr/python3

import logging
import os
import json
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
    self.port = kwargs.get('port') or 9200
    self.date = datetime.date.today()
    self.sessionID = uuid.uuid4()

    logging.StreamHandler.__init__(self)

  def emit(self, record):
    self.format(record)

    indexURL = 'http://{}:{}/transatlantic_torrent_express-{}/_doc'.format(self.host, self.port, self.date.strftime('%Y.%m.%d'))
    doc = {
      'severity': record.levelname,
      'message': record.message,
      '@timestamp': int(record.created*1000),
      'sessionID': str(self.sessionID)
    }

    if hasattr(record, 'es'):
      for param in record.es.values():
        if ': {}'.format(param) in record.message:
          doc['message'] = record.message.replace(': {}'.format(str(param)), '')

      doc = {**record.es, **doc}

    payload = json.dumps(doc).encode('utf8')
    req = urllib.request.Request(indexURL, data=payload,
                                 headers={'content-type': 'application/json'})
    response = urllib.request.urlopen(req)
    response = response.read().decode('utf8')
    return response

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
eh = ESHandler(host=esHost, port=esPort)
eh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)8s | %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.addHandler(eh)
logger = ElasticFieldParameterAdapter(logger)
