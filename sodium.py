from sys import argv
from finDataScraper import Fin10JQKA
from finReportScraper import FinReportHandler
from credentials import apiUrl, token, receiver_email, sender_email, sender_password

description = """
NAME
      sodium - a helper to automate the visualisation of financial data of listed companies.

SYNOPSIS:
      python sodium.py help
      python sodium.py [ -t | -T ] [ -m ] [ -C ] [ --directory=DIRECTORY ] [ --retryMax=MAX ]
                              SYMBOL | [ --fromSymbol=SYMBOL ] ALL
      python sodium.py scrape [ --retryMax=MAX ]
                              SYMBOL | [ --fromSymbol=SYMBOL ] ALL

OPTIONS:
                    (Download mode)
      -t            Extract pages containing table(s) and merge for data analysis.
      -T            Provide a consolidated version of -t
      -m            Merge downloaded financial reports for further studies.
      -C            Clean up downloaded financial reports.

PARAMS:
                    (Common)
      --retryMax    Number of retries made when failed to download the pdf from HKEX. Default: 3
      --fromSymbol  Starting symbol

                    (Download mode)
      --directory   The download directory. Default: downloaded
"""

if __name__ == '__main__':
  def get_param(name, options):
    prefix = 3 + len(name)
    provided = [opt[prefix:] for opt in options if '--{}'.format(name) in opt]
    return provided[0] if provided else None

  options = [arg for arg in argv if arg.startswith('-')]
  argv = [arg for arg in argv if arg not in options]

  default = {
    'retryMax': 7,
    'downloadDirectory': 'downloaded'
  }

  if 'help' in argv or len(argv) is 1:
    print(description)
  elif 'scrape' in argv:
    retryMax = get_param('retryMax', options)
    retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else default['retryMax'])

    if len(argv) < 3:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tTarget should be provided.', '\n'*2)
      exit()
    else:
      symbol = argv[2].upper()
      fromSymbol = get_param('fromSymbol', options) if symbol == 'ALL' else None

    scraper = Fin10JQKA(apiUrl, token, retryMax, symbol, fromSymbol)
    scraper.process()
  else:
    fromSymbol = get_param('fromSymbol', options) if argv[1].upper() == 'ALL' else None
    symbols = argv[1:] if fromSymbol is None else 'ALL'

    needConsolidatedTables = '-T' in options
    needTables = '-t' in options
    needMergeFiles = '-m' in options
    needCleanUp = '-C' in options
    downloadDirectory = get_param('directory', options)
    retryMax = get_param('retryMax', options)

    downloadDirectory = downloadDirectory if downloadDirectory not in [None, ''] else default['downloadDirectory']
    retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else default['retryMax'])

    for symbol in symbols:
      handler = FinReportHandler(downloadDirectory, retryMax, symbol, fromSymbol)
      handler.process(consolidatedTables=needConsolidatedTables, tables=needTables, mergeFiles=needMergeFiles, cleanUp=needCleanUp)

  print('Exit')
