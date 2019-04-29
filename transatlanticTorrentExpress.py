#!/usr/bin/python3
import os, sys
from subprocess import check_output, Popen, PIPE
from configparser import ConfigParser

# Local files
from logger import logger

def getConfig():
  logger.info('Reading config')
  pwd = os.path.dirname(os.path.abspath(__file__))
  path = os.path.join(pwd, 'config.ini')

  if not os.path.isfile(path):
    print('Please fill out and rename config file. Check README for more info.')
    exit(0)

  config = ConfigParser()
  config.read(path)

  logger.info('Sections parsed: {}'.format(config.sections()))
  return config


def getFiles(path, host=None, user=None):
  if (host and user):
    cmd = 'ssh {}@{} ls {}'.format(user, host, path)
  else:
    cmd = 'ls {}'.format(path)

  contents = check_output(cmd, shell=True)

  if (contents):
    contents = contents.decode('utf-8').split('\n')
    contents = list(filter(lambda x: len(x) > 0, contents))

  return contents

def filesNotShared(local, remote):
  c = set(local) - set(remote)
  if c == set():
    return False
  
  return list(c)

def transferFiles(files, localPath, remotePath, host=None, user=None):
  transferedFiles = []

  for file in files:
    logger.info('Moving file: {}'.format(file))
    file = os.path.join(localPath, file)

    if (host and user):
      cmd = "rsync -rz '{}' {}@{}:{}".format(file, user, host, remotePath)
    else:
      cmd = "rsync -rz '{}' {}".format(file, remotePath)

    rsyncProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = rsyncProcess.communicate()

    if stderr:
      logger.error('Rsync error: {}'.format(stderr))

    logger.info('Rsync output: {}'.format(stdout))
    transferedFiles.append(file)

  return transferedFiles

def removeFromDeluge(execScript, files):
  execPython = '/usr/bin/python2'

  for file in files:
    file = file.split('/')[-1]

    logger.info('Removing {} from deluge'.format(file))
    cmd = "{} {} rm '{}'".format(execPython, execScript, file)

    delugeProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = delugeProcess.communicate()

    if stderr:
      logger.error('Deluge error: {}'.format(stderr))

    logger.info('Deluge output: {}'.format(stdout))
    logger.info('Successfully removed: {}'.format(file))

def main():
  config = getConfig()
  host = config['SSH']['host']
  user = config['SSH']['user']
  remotePath = config['FILES']['remote']
  localPath = config['FILES']['local']
  delugeScript = config['DELUGE']['script']

  remoteFiles = getFiles(remotePath, host, user)
  logger.info('Remote files found: {}'.format(remoteFiles))
  # print('Remote found: {}'.format(remoteFiles))
  
  localFiles = getFiles(localPath)
  # print('Local files: {}'.format(localFiles))
  logger.info('Local files found: {}'.format(localFiles))

  newFiles = filesNotShared(localFiles, remoteFiles)
  if (newFiles):
    logger.info('New files: {}'.format(newFiles))
    logger.info('Existing files: {}'.format(list(set(remoteFiles).intersection(localFiles))))

    transferedFiles = transferFiles(newFiles, localPath, remotePath, host, user)
    removeFromDeluge(delugeScript, transferedFiles)


  else:
    print('No new files found')

if __name__ == '__main__':
  main()
