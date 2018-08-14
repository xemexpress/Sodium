from sys import argv
from financials import FinReportHandler

# Format: python test.py [-m] [-c] [--directory=DIRECTORY] SYMBOL
#   -m    Merge downloaded files
#   -c    Clean up downloaded files

if __name__ == '__main__':
  def getOption(name, options):
    prefix = 3 + len(name)
    provided = [opt[prefix:] for opt in options if '--{}'.format(name) in opt]
    return provided[0] if provided else None

  options = [arg for arg in argv if arg.startswith('-')]
  argv = [arg for arg in argv if arg not in options]

  symbol = argv[1]
  mergeFiles = '-m' in options
  cleanUp = '-c' in options
  downloadDirectory = getOption('directory', options)

  handler = FinReportHandler(downloadDirectory)
  handler.get(symbol, mergeFiles=mergeFiles, cleanUp=cleanUp)
