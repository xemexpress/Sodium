from sys import argv
from financials import FinReportHandler

# Format:
#   python sodium.py [-S] [-t] [-m] [-C] [--directory=DIRECTORY] [--retry=MAX] SYMBOL
#
# Options:
#   -S              Skip download process, usually because files have been downloaded.
#   -t              Extract pages containing table(s) and merge for data analysis.
#   -m              Merge downloaded financial reports for further studies.
#   -C              Clean up downloaded financial reports.
#
# Params:
#   --directory     The download directory.
#   --retry         Number of retries made when failed to download the pdf from HKEX

if __name__ == '__main__':
  def get_param(name, options):
    prefix = 3 + len(name)
    provided = [opt[prefix:] for opt in options if '--{}'.format(name) in opt]
    return provided[0] if provided else None

  options = [arg for arg in argv if arg.startswith('-')]
  argv = [arg for arg in argv if arg not in options]

  symbol = argv[1]
  skipDownload = '-S' in options
  needTables = '-t' in options
  needMergeFiles = '-m' in options
  needCleanUp = '-C' in options
  downloadDirectory = get_param('directory', options)
  retryMax = get_param('retry', options)

  retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else 3)

  handler = FinReportHandler(downloadDirectory)
  handler.get(symbol, skipDownload, retryMax)

  if needTables:
    handler.extract_tables('表')

  if needMergeFiles:
    handler.merge_files()

  if needCleanUp:
    handler.clean_up()

  print('Exit')
