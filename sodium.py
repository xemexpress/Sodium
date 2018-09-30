from sys import argv
from finDataScraper import Fin10JQKA, FinHKEX
from finReportHandler import FinReportHandler

description = """
NAME
      sodium - a helper to automate the visualisation of financial data of listed companies.

SYNOPSIS:
      python sodium.py help
      python sodium.py [ -S ] [ -t | -T ] [ -n ] [ -m ] [ -C ] [ --directory=DIRECTORY ] [ --retryMax=MAX ] SYMBOL
      python sodium.py scrape --apiUrl=API_URL --token=TOKEN --source=SOURCE --content=CONTENT [ --retryMax=MAX ]
                              SYMBOL | [ --fromSymbol=SYMBOL ] ALL

OPTIONS:
                    (Download mode)
      -S            Skip download process, usually because files have been downloaded.
      -t            Extract pages containing table(s) and merge for data analysis.
      -T            Provide a consolidated version of -t
      -n            Extract notes.
      -m            Merge downloaded financial reports for further studies.
      -C            Clean up downloaded financial reports.

PARAMS:
                    (Common)
      --retryMax    Number of retries made when failed to download the pdf from HKEX. Default: 3

                    (Download mode)
      --directory   The download directory. Default: downloaded

                    (Scraping mode)
      --source      Source of data
      --content     Content to scrape
      --apiUrl      API url for sending requests
      --token       Authorization token
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
    apiUrl = get_param('apiUrl', options)
    token = get_param('token', options)
    source = get_param('source', options)
    content = get_param('content', options)
    retryMax = get_param('retryMax', options)

    retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else default['retryMax'])

    targetSources = ['10JQKA', 'HKEX']
    if source not in targetSources:
      print('WARNING:')
      print('\tSource should be provided, choosing from targetSources({}).'.format(', '.join(targetSources)))
      exit()
    
    if content not in ['both', 'company', 'financials']:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tContent to scrape should be provided.', '\n'*2)
      exit()

    if apiUrl in [None, ''] or token in [None, '']:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tApiUrl and token should be provided for sending POST requests.', '\n'*2)
      exit()

    if len(argv) < 3:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tTarget should be provided.', '\n'*2)
      exit()
    else:
      symbol = argv[2]
      fromSymbol = get_param('fromSymbol', options) if symbol == 'ALL' else None

    if source == '10JQKA':
      scraper = Fin10JQKA(apiUrl, token, retryMax, symbol, fromSymbol)
    elif source == 'HKEX':
      scraper = FinHKEX(apiUrl, token, retryMax, symbol, fromSymbol)

    scraper.process()
  else:
    symbol = argv[1]
    skipDownload = '-S' in options
    needTables = '-t' in options or '-T' in options
    needNotes = '-n' in options
    needMergeFiles = '-m' in options
    needCleanUp = '-C' in options
    downloadDirectory = get_param('directory', options)
    retryMax = get_param('retryMax', options)

    downloadDirectory = downloadDirectory if downloadDirectory not in [None, ''] else default['downloadDirectory']
    retryMax = int(retryMax if retryMax is not None and retryMax.isdigit() else default['retryMax'])

    handler = FinReportHandler(downloadDirectory)
    handler.get(symbol, skipDownload, retryMax)

    if needTables:
      consolidated = '-T' in options
      handler.extract_tables(wanted='表', unwanted='附註', onlyFirstThree=consolidated)

    if needNotes:
      handler.extract_notes(wanted='附註')

    if needMergeFiles:
      handler.merge_files()

    if needCleanUp:
      handler.clean_up()

    print('Exit')
