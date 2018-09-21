from sys import argv
from finDataScraper import FinDataScraper
from finReportHandler import FinReportHandler

if __name__ == '__main__':
  def get_param(name, options):
    prefix = 3 + len(name)
    provided = [opt[prefix:] for opt in options if '--{}'.format(name) in opt]
    return provided[0] if provided else None

  options = [arg for arg in argv if arg.startswith('-')]
  argv = [arg for arg in argv if arg not in options]

  default = {
    'retryMax': 3,
    'downloadDirectory': 'downloaded'
  }

  if 'help' in argv or len(argv) is 1:
    description = """
NAME
      sodium - a helper to automate the visualisation of financial data of listed companies.

SYNOPSIS:
      python sodium.py help
      python sodium.py [ -S ] [ -t | -T ] [-n] [ -m ] [ -C ] [ --directory=DIRECTORY ] [ --retry=MAX ] SYMBOL
      python sodium.py scrape [--apiUrl] [--token] [ -p | -u ] SYMBOL

OPTIONS:
                    (Default mode)
      -S            Skip download process, usually because files have been downloaded.
      -t            Extract pages containing table(s) and merge for data analysis.
      -T            Provide a consolidated version of -t
      -n            Extract notes.
      -m            Merge downloaded financial reports for further studies.
      -C            Clean up downloaded financial reports.

                    (Scraping mode)
      -p            Allow sending POST requests. (Params 'apiUrl' and 'token' should be provided.)
      -u            Allow sending PUT requests. (Params 'apiUrl' and 'token' should be provided.)

PARAMS:
                    (Default mode)
      --directory   The download directory. Default: downloaded
      --retry       Number of retries made when failed to download the pdf from HKEX. Default: 3

                    (Scraping mode)
      --apiUrl      API url for sending requests
      --token       Authorization token
"""
    print(description)
  elif 'scrape' in argv:
    if len(argv) < 3:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tSymbol should be provided.')
      exit()
    else:
      symbol = argv[2]

    setVerbose = '-v' in options
    allowPost = '-p' in options
    allowUpdate = '-u' in options
    if allowPost or allowUpdate:
      apiUrl = get_param('apiUrl', options)
      token = get_param('token', options)
      if apiUrl in [None, ''] or token in [None, '']:
        print(description, '\n'*2)
        print('WARNING:')
        print('\tApiUrl and token should be provided for sending POST requests.')
        exit()

    scraper = FinDataScraper(symbol, setVerbose)

    scraper.get_all_statements()

    scraper.sort_financials()

    if apiUrl not in [None, ''] and token not in [None, '']:
      if allowUpdate:
        scraper.upload(apiUrl, token, 'update')
      elif allowPost:
        scraper.upload(apiUrl, token, 'post')
  else:
    symbol = argv[1]
    skipDownload = '-S' in options
    needTables = '-t' in options or '-T' in options
    needNotes = '-n' in options
    needMergeFiles = '-m' in options
    needCleanUp = '-C' in options
    downloadDirectory = get_param('directory', options)
    retryMax = get_param('retry', options)

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
