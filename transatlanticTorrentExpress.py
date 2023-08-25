#!/usr/bin/python3
import os, sys, math
import shutil
from subprocess import check_output, Popen, PIPE
from datetime import timedelta
from time import time

try:
  from delugeClient import Deluge
except Exception:
  print('Download delugeClient package using: pip3 install delugeClient-kevin')
  sys.exit(1)

from logger import logger
from utils import getConfig, readAvgSpeedFromDisk, writeAvgSpeedToDisk, VIDEO_EXTENSIONS

LAST_TRANSFER_SPEED=readAvgSpeedFromDisk()
TRANSFER_SPEED_UNIT="Mb/s"
LAST_FILE_TRANSFER_SPEED=None


def parseFileListResponse(filesString):
  if filesString == None:
    return []

  files = filesString.decode('utf-8').split('\n')
  return list(filter(lambda x: len(x) > 0, files)) # remove any empty newline from list


def filesNotShared(remote, local):
  c = set(remote.files) - set(local.files)
  files = list(c)
  if len(files) == 0:
    return False

  return list(filter(lambda file: not local.findFile(file), files))


class File():
  def __init__(self, file, system):
    self.name = file
    self.system = system
    self.size = self.fileSize()
    self.sizeInBytes = self.fileSizeInBytes()

  def fileSize(self):
    filePath = self.system.buildFilePath(self)
    cmd = "du -hs '{}'".format(filePath)

    if self.system.remote:
      cmd = 'ssh {}@{} {}'.format(self.system.user, self.system.path, cmd)
    
    diskusageOutput = check_output(cmd, shell=True)

    diskusageOutput = diskusageOutput.decode('utf-8').split('\t')
    return diskusageOutput[0] + 'B'

  def fileSizeInBytes(self, blockSize=1024):
    fileSizeBytes = blockSize

    try:
      if self.size[-2] == 'G':
        fileSizeBytes = float(self.size[:-2]) * 1024 * 1024 * 1024
      elif self.size[-2] == 'M':
        fileSizeBytes = float(self.size[:-2]) * 1024 * 1024
      elif self.size[-2] == 'K':
        fileSizeBytes = float(self.size[:-2]) * 1024
    except:
      logger.error('Filesize to float. Filesize:', es={'output': self.size})
      return

    return fileSizeBytes

  @property
  def telemetry(self):
    return {
      'filename': self.name,
      'filesize': self.size,
      'bytes': self.sizeInBytes
    }

  def __str__(self):
    return str(self.name)

  def __repr__(self):
    return repr(self.name)


class System():
  def __init__(self, path, host=None, user=None):
    self.path = path
    self.files = []
    self.host = host
    self.user = user
    self.remote = host or user

  def getFiles(self):
    logger.debug('Getting files from path', es={'path': self.path})

    cmd = "ls '{}'".format(self.path)
    if self.remote:
      cmd = 'ssh {}@{} {}'.format(self.user, self.host, cmd)

    contents = check_output(cmd, shell=True)
    files = parseFileListResponse(contents)
    for file in files:
      self.files.append(File(file, self))

    logger.debug('Files found', es={'files': self.files})
    return self.files

  def findFile(self, file):
    cmd = "find {} -type f -name '{}'".format(self.path, file.name)
    if self.remote:
      cmd = 'ssh {}@{} {}'.format(self.user, self.path, cmd)

    fileMatch = check_output(cmd, shell=True)
    return fileMatch != b''

  def buildFilePath(self, file):
    return os.path.join(self.path, file.name)

  def rsyncFilePath(self, file):
    filePath = self.buildFilePath(file)

    if not self.remote:
      return "'{}'".format(filePath)

    return "{}@{}:'{}'".format(self.user, self.host, filePath)


class Transport():
  def __init__(self, files, satelliteSystem, localSystem, downloadClient):
    self.files = files
    self.transferedFiles = []
    self.satelliteSystem = satelliteSystem
    self.localSystem = localSystem
    self.avgTransferSpeed = LAST_TRANSFER_SPEED # in MegaBits / Mb
    self.downloadClient = downloadClient

  def setTransferSpeed(self, file, elapsedTransferTime):
    elapsedTransferTime = math.ceil(elapsedTransferTime)
    transferSpeed = math.ceil(file.sizeInBytes / 1000 / 1000 * 8 / elapsedTransferTime)

    transferTime = str(timedelta(seconds=elapsedTransferTime))

    esData = {
      'filename': file.name,
      'filesize': file.size,
      'bytes': file.sizeInBytes,
      'transferTime': transferTime,
      'transferSpeed': transferSpeed,
      'transferSpeedUnit': TRANSFER_SPEED_UNIT,
      'seconds': elapsedTransferTime
    }
    logger.info('Transfer finished', es=esData)

    self.avgTransferSpeed = (transferSpeed + self.avgTransferSpeed) / 2 if self.avgTransferSpeed else transferSpeed
    writeAvgSpeedToDisk(self.avgTransferSpeed)

  def ensureLocalParentFolder(self, file):
    folderName, fileExtension = os.path.splitext(file.name)
    if fileExtension not in VIDEO_EXTENSIONS:
      return False

    try:
      folderedLocalPath = os.path.join(self.localSystem.path, folderName)
      os.makedirs(folderedLocalPath)
      logger.info("Created local parent folder for folder-less file", es=file.telemetry)
      return folderName
    except FileExistsError:
      logger.warning("Error creating local parent folder, already exists", es=file.telemetry)
      return folderName
    except Exception as error:
      msg = str(error)
      logger.error("Unexpected error while creating local folder", es={**file.telemetry, 'error': msg})
      logger.error(msg)

  def estimateFileTransferTime(self, file):
    fileSizeInMegabit = file.sizeInBytes / 1000 / 1000 * 8
    estimatedTransferTimeInSeconds = math.floor(fileSizeInMegabit / self.avgTransferSpeed)
    estimatedTransferTime = str(timedelta(seconds=estimatedTransferTimeInSeconds))

    telemetry = {
      **file.telemetry,
      'seconds': estimatedTransferTimeInSeconds,
      'transferTime': estimatedTransferTime,
      'transferSpeed': self.avgTransferSpeed,
      'transferSpeedUnit': TRANSFER_SPEED_UNIT
    }
    logger.info('Estimate transfer speed', es=telemetry)

  def start(self):
    for file in self.files:
      try:
        localFolder = self.localSystem.path
        newParentFolder = self.ensureLocalParentFolder(file)

        if newParentFolder:
          localFolder = os.path.join(localFolder, newParentFolder)

        transferStartTime = time()
        logger.info('Transfer starting', es=file.telemetry)
        if self.avgTransferSpeed is not None:
          self.estimateFileTransferTime(file)

        cmd = "rsync -ra {} '{}'".format(self.satelliteSystem.rsyncFilePath(file), localFolder)
        rsyncProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        stdout, stderr = rsyncProcess.communicate()
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')

        if stderr:
          print(stderr)
          logger.error('Rsync error', es={**file.telemetry, 'error':stderr})
          continue

        if len(stdout):
          logger.debug('Rsync output', es={**file.telemetry, 'output': stdout})

        elapsedTransferTime = time() - transferStartTime
        self.setTransferSpeed(file, elapsedTransferTime)

        if self.downloadClient.enabled is True:
          self.downloadClient.remove(file)

      except Exception as err:
        logger.error('Unexpected error when transfering file', es={**file.telemetry, 'error': str(err)})
        continue


class DownloadClient():
  def __init__(self, enabled=True):
    try:
      self.enabled = enabled
      self.deluge = None

      if enabled is True:
        self.deluge = Deluge()
    except Exception as err:
      logger.error("Unexpected error from deluge", es={**file.telemetry, 'error': str(err)})

  def remove(self, file):
    logger.info('Removing file from deluge', es=file.telemetry)

    try:
      response = self.deluge.removeByName(file.name, True)
      if response is not None:
        logger.info('Successfully removed file from deluge', es=file.telemetry)
        return
      
      raise Exception('Deluge item not found')

    except Exception as err:
      logger.error('Unexpected deluge error', es={**file.telemetry, 'error': str(err)})


def main():
  config = getConfig()
  host = config['SATELLITE']['host']
  user = config['SATELLITE']['user']
  remotePath = config['SATELLITE']['path']
  remove = config['SATELLITE']['remove']
  localPath = config['LOCAL']['path']

  satelliteSystem = System(remotePath, host, user)
  localSystem = System(localPath)
  downloadClient = DownloadClient(remove)

  satelliteSystem.getFiles()
  localSystem.getFiles()

  if len(satelliteSystem.files) == 0:
    logger.debug('No remote files found')
    return

  newFiles = filesNotShared(satelliteSystem, localSystem)
  if not newFiles:
    logger.debug('No new files found to travel on the great transatlantic express')
    return

  logger.info('New files found to travel transatlantic express', es={'files': newFiles})
  transport = Transport(newFiles, satelliteSystem, localSystem, downloadClient)
  transport.start()

if __name__ == '__main__':
  main()
