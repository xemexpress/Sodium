from sys import argv
from report_downloader import PDFHandler

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
  mergeFiles = True if '-m' in options else False
  cleanUp = True if '-c' in options else False
  downloadDirectory = getOption('directory', options)

  handler = PDFHandler(downloadDirectory)
  handler.get(symbol, mergeFiles=mergeFiles, cleanUp=cleanUp)
