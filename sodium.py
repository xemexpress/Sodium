import time
from sys import argv
from finDataScraper import Fin10JQKA
from finReportScraper import FinReportHandler
from credentials import apiUrl, token, receiver_email, sender_email, sender_password

description = """
NAME
      sodium - a helper to automate the visualisation of financial data of listed companies.

SYNOPSIS:
      python sodium.py help
      python sodium.py [ -t | -T ] [ -m ] [ -C ] [ --directory=DIRECTORY ] [ --retry_max=MAX ]
                              SYMBOL | [ --from_symbol=SYMBOL ] ALL
      python sodium.py scrape [ --retry_max=MAX ]
                              SYMBOL | [ --from_symbol=SYMBOL ] ALL

OPTIONS:
                    (Download mode)
      -t            Extract pages containing table(s) and merge for data analysis.
      -T            Extract notes.
      -m            Merge downloaded financial reports for further studies.
      -S            Skip downloading reports as this assumes required reports have been downloaded.
      -C            Clean up downloaded financial reports.

PARAMS:
                    (Common)
      --retry_max    Number of retries made when failed to download the pdf from HKEX. Default: 3
      --from_symbol  Starting symbol
      --lang        If Chinese is preferred, 'ch' (default); otherwise, 'en' (recommended) for english.

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
    'retry_max': 7,
    'download_directory': 'downloaded'
  }

  if 'help' in argv or len(argv) is 1:
    print(description)
  elif 'scrape' in argv:
    retry_max = get_param('retry_max', options)
    retry_max = int(retry_max if retry_max is not None and retry_max.isdigit() else default['retry_max'])

    if len(argv) < 3:
      print(description, '\n'*2)
      print('WARNING:')
      print('\tTarget should be provided.', '\n'*2)
      exit()
    else:
      symbol = argv[2].upper()
      from_symbol = get_param('from_symbol', options) if symbol == 'ALL' else None

    scraper = Fin10JQKA(apiUrl, token, retry_max, symbol, from_symbol)
    scraper.process()
  else:
    from_symbol = get_param('from_symbol', options) if argv[1].upper() == 'ALL' else None
    symbols = argv[1:] if from_symbol is None else 'ALL'

    need_consolidated_tables = '-T' in options
    need_tables = '-t' in options
    need_merge_files = '-m' in options
    skip_download = '-S' in options
    need_clean_up = '-C' in options
    download_directory = get_param('directory', options)
    retry_max = get_param('retry_max', options)
    lang = get_param('lang', options)
    lang = lang.lower() if lang else 'ch'

    download_directory = download_directory if download_directory not in [None, ''] else default['download_directory']
    retry_max = int(retry_max if retry_max is not None and retry_max.isdigit() else default['retry_max'])
    
    print('\n\nWARNING: YOU ARE SKIPPING REPORT DOWNLOAD PROCESSES!! \n\n Confirm by ^C.')
    try:
      time.sleep(9999999)
    except:
      pass

    for symbol in symbols:
      try:
          handler = FinReportHandler(download_directory, retry_max, symbol, from_symbol, lang)
          handler.process(consolidated_tables=need_consolidated_tables, tables=need_tables, merge_files=need_merge_files, skip_download=skip_download, clean_up=need_clean_up)
      except:
          pass

  print('Exit')
