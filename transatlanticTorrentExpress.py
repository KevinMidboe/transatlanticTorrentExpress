#!/usr/bin/python3
import os, sys
from subprocess import check_output, Popen, PIPE

# Local files
from logger import logger
from utils import getConfig, readAvgSpeedFromDisk, writeAvgSpeedToDisk

ESTIMATED_TRANSFER_SPEED=readAvgSpeedFromDisk()
TRANSFER_SPEED_UNIT="Mb/s"
LAST_FILE_TRANSFER_SPEED=None

def fileSizeByPath(path):
    filename = path.split('/')[-1]
    config = getConfig()
    host = config['SSH']['host']
    user = config['SSH']['user']
    remotePath = config['FILES']['remote']

    diskUsageCmd = 'du -hs'
    if (remotePath in path):
      cmd = 'ssh {}@{} {} "\'{}\'"'.format(user, host, diskUsageCmd, path)
    else:
      cmd = '{} "{}"'.format(diskUsageCmd, path)

    diskusageOutput = check_output(cmd, shell=True)

    diskusageOutput = diskusageOutput.decode('utf-8').split('\t')
    return diskusageOutput[0] + 'B'

def fileSizeInBytes(fileSize, blockSize=1024):
  try:
    if fileSize[-2] == 'G':
      fileSizeInBytes = float(fileSize[:-2]) * 1024 * 1024 * 1024
    elif fileSize[-2] == 'M':
      fileSizeInBytes = float(fileSize[:-2]) * 1024 * 1024
    elif fileSize[-2] == 'K':
      fileSizeInBytes = float(fileSize[:-2]) * 1024
  except:
    logger.error('Filesize to float. Filesize:', es={'output': fileSize})
    return

  return fileSizeInBytes

def estimateFileTransferTime(fileSize, filename):
    global ESTIMATED_TRANSFER_SPEED,TRANSFER_SPEED_UNIT,LAST_FILE_TRANSFER_SPEED

    fileSizeBytes = fileSizeInBytes(fileSize)
    if fileSizeBytes == None:
      logger.info('Unable to calculate transfer time for file', es={'filename': filename})
      return

    if (LAST_FILE_TRANSFER_SPEED):
      estimatedTransferSpeed = LAST_FILE_TRANSFER_SPEED
    else:
      estimatedTransferSpeed = ESTIMATED_TRANSFER_SPEED
      logger.debug('Guessing transfer speed with static speed variable', es={'transferSpeed': ESTIMATED_TRANSFER_SPEED,
                                                                            'transferSpeedUnit': TRANSFER_SPEED_UNIT})

    elapsedTimeInSeconds = (fileSizeBytes / 1000 / 1000 * 8) / estimatedTransferSpeed
    estimatedTransferTime = str(timedelta(seconds=elapsedTimeInSeconds)).split('.')[0]

    # trying to find the speed we average transfer at
    logger.info('Estimated transfer time'.format(estimatedTransferTime), es={'filename': filename,
                                                                             'filesize': fileSize,
                                                                             'bytes': fileSizeBytes,
                                                                             'seconds': elapsedTimeInSeconds,
                                                                             'transferTime': estimatedTransferTime,
                                                                             'transferSpeed': estimatedTransferSpeed,
                                                                             'transferSpeedUnit': TRANSFER_SPEED_UNIT})
    return estimatedTransferSpeed

def getFiles(path, host=None, user=None):
  logger.info('Getting filenames from path: {}'.format(path), es={'path': path})
  if (host and user):
    cmd = "ssh {}@{} ls '{}'".format(user, host, path)
  else:
    cmd = "ls '{}'".format(path)

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
    if file in getFiles(remotePath, host, user):
      logger.info('File already exists at remote path. Skipping.')
      continue
    logger.info('Moving file: {}'.format(file), es={'filename': file})

    file = os.path.join(localPath, file)

    if (host and user):
      cmd = "rsync -rz '{}' {}@{}:{}".format(file, user, host, remotePath)
    else:
      cmd = "rsync -rz '{}' {}".format(file, remotePath)

    rsyncProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = rsyncProcess.communicate()

    if stderr:
      logger.error('Rsync error: {}'.format(stderr))

    logger.debug('Rsync output: {}'.format(stdout))
    transferedFiles.append(file)

  return transferedFiles

def removeFromDeluge(execScript, files):
  execPython = '/usr/bin/python2'

  for file in files:
    file = file.split('/')[-1]

    logger.info('Removing {} from deluge'.format(file), es={"filename": file})
    cmd = "{} {} rm '{}'".format(execPython, execScript, file)

    delugeProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    stdout, stderr = delugeProcess.communicate()

    if stderr:
      logger.error('Deluge error: {}'.format(stderr))

    logger.debug('Deluge output: {}'.format(stdout))
    logger.info('Successfully removed: {}'.format(file), es={'filename': file})

def main():
  config = getConfig()
  host = config['SSH']['host']
  user = config['SSH']['user']
  remotePath = config['FILES']['remote']
  localPath = config['FILES']['local']
  delugeScript = config['DELUGE']['script']

  remoteFiles = getFiles(remotePath, host, user)
  if len(remoteFiles) > 0:
    logger.info('Remote files found: {}'.format(remoteFiles), es={'files': remoteFiles})
  else:
    logger.info('No remote files found')
  # print('Remote found: {}'.format(remoteFiles))
  
  localFiles = getFiles(localPath)
  # print('Local files: {}'.format(localFiles))
  if len(localFiles) > 0:
    logger.info('Local files found: {}'.format(localFiles), es={'files': localFiles})
  else:
    logger.info('No local files found')

  newFiles = filesNotShared(localFiles, remoteFiles)
  if (newFiles):
    logger.info('New files: {}'.format(newFiles), es={'files': newFiles})
    exisitingFiles = list(set(remoteFiles).intersection(localFiles))
    logger.info('Existing files: {}'.format(exisitingFiles), es={'files': exisitingFiles})

    transferedFiles = transferFiles(newFiles, localPath, remotePath, host, user)
    removeFromDeluge(delugeScript, transferedFiles)


  else:
    # print('No new files found to travel on the great transatlantic express')
    logger.info('No new files found to travel on the great transatlantic express')

if __name__ == '__main__':
  main()
