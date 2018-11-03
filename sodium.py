from sys import argv
from finDataScraper import Fin10JQKA
from finReportScraper import FinReportHandler
from credentials import apiUrl, token, receiver_email, sender_email, sender_password

description = """
NAME
      sodium - a helper to automate the visualisation of financial data of listed companies.

SYNOPSIS:
      python sodium.py help
      python sodium.py [ -S ] [ -t | -T ] [ -n ] [ -m ] [ -C ] [ --directory=DIRECTORY ] [ --retryMax=MAX ] SYMBOL
      python sodium.py scrape [ -a | --source=SOURCE ] [ --retryMax=MAX ]
                              SYMBOL | [ --fromSymbol=SYMBOL ] ALL

OPTIONS:
                    (Download mode)
      -t            Extract pages containing table(s) and merge for data analysis.
      -T            Provide a consolidated version of -t
      -n            Extract notes.
      -m            Merge downloaded financial reports for further studies.
      -C            Clean up downloaded financial reports.

                    (Scrape mode)
      -a            Adjust structural data

PARAMS:
                    (Common)
      --retryMax    Number of retries made when failed to download the pdf from HKEX. Default: 3

                    (Download mode)
      --directory   The download directory. Default: downloaded

                    (Scrape mode)
      --source      Source of data
      --fromSymbol  Starting symbol
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
    needAdjustments = '-a' in options
    source = get_param('source', options) if not needAdjustments else None
    retryMax = get_param('retryMax', options)

    retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else default['retryMax'])

    targetSources = ['10JQKA', 'HKEX']
    if source not in targetSources and not needAdjustments:
      print('WARNING:')
      print('\tSource should be provided, choosing from targetSources({}).'.format(', '.join(targetSources)))
      exit()

    if len(argv) < 3:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tTarget should be provided.', '\n'*2)
      exit()
    else:
      symbol = argv[2]
      fromSymbol = get_param('fromSymbol', options) if symbol == 'ALL' else None

    if needAdjustments:
      scraper = FinAdapter(apiUrl, token, retryMax, symbol, fromSymbol)
    elif source == '10JQKA':
      # Scrape financials
      scraper = Fin10JQKA(apiUrl, token, retryMax, symbol, fromSymbol)
    elif source == 'HKEX':
      # Scrape sharesOutstanding on the latest financials
      scraper = FinHKEX(apiUrl, token, retryMax, symbol, fromSymbol)
    
    scraper.process()
  else:
    symbol = argv[1]
    needConsolidatedTables = '-T' in options
    needTables = '-t' in options
    needNotes = '-n' in options
    needMergeFiles = '-m' in options
    needCleanUp = '-C' in options
    downloadDirectory = get_param('directory', options)
    retryMax = get_param('retryMax', options)

    downloadDirectory = downloadDirectory if downloadDirectory not in [None, ''] else default['downloadDirectory']
    retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else default['retryMax'])

    handler = FinReportHandler(downloadDirectory, retryMax, symbol)
    handler.process(consolidatedTables=needConsolidatedTables, tables=needTables, notes=needNotes, mergeFiles=needMergeFiles, cleanUp=needCleanUp)

    print('Exit')
