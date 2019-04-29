#!/usr/bin/python3
import os, sys
from subprocess import check_output, Popen, PIPE
from configparser import ConfigParser
print('test')

def getConfig():
  print('Reading config')
  config = ConfigParser()
  pwd = os.path.dirname(os.path.abspath(__file__))
  path = os.path.join(pwd, 'config.ini')
  config.read(path)

  print('Sections parsed: {}'.format(config.sections()))
  return config


def getFiles(path, host=None, user=None):
  print('Checking path: {}'.format(path))

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
    file = os.path.join(localPath, file)

    if (host and user):
      cmd = "rsync -rz '{}' {}@{}:{}".format(file, user, host, remotePath)
    else:
      cmd = "rsync -rz '{}' {}".format(file, remotePath)

    rsyncProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = rsyncProcess.communicate()

    if stderr:
      print('Unable', stderr)

    print(stdout)
    transferedFiles.append(file)

  return transferedFiles

def removeFromDeluge(execScript, files):
  execPython = '/usr/bin/python2'

  for file in files:
    print('Removing {} from deluge'.format(file))
    cmd = "{} {} rm '{}'".format(execPython, execScript, file)

    delugeProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = delugeProcess.communicate()

    if stderr:
      print('Deluge unable', stderr)

    print('Successfully removed: ', file)

def main():
  config = getConfig()
  host = config['SSH']['host']
  user = config['SSH']['user']
  remotePath = config['FILES']['remote']
  localPath = config['FILES']['local']
  delugeScript = config['DELUGE']['script']

  remoteFiles = getFiles(remotePath, host, user)
  # print('Remote found: {}'.format(remoteFiles))
  
  localFiles = getFiles(localPath)
  # print('Local files: {}'.format(localFiles))

  newFiles = filesNotShared(localFiles, remoteFiles)
  if (newFiles):
    print('New files: {}'.format(newFiles))
    print('Existing files: {}'.format(list(set(remoteFiles).intersection(localFiles))))

    transferedFiles = transferFiles(newFiles, localPath, remotePath, host, user)
    removeFromDeluge(delugeScript, transferedFiles)


  else:
    print('No new files found')

if __name__ == '__main__':
  main()
