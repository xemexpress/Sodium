import os
import time
from random import randint
from urllib.request import urlretrieve
from urllib.error import URLError
from glob import glob
from shutil import rmtree, copyfileobj
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileMerger

class PDFHandler:
    downloadDirectory = ''      # The place pdf got saved
    companyName = ''            # Name of listed company
    symbol = ''                 # Symbol of listed company
    pdfs = []                   # [(fileName, source)]

    def __init__(self, downloadDirectory='downloaded'):
        self.downloadDirectory = downloadDirectory

    # pdfs is set.
    def get(self, symbol, mergeFiles=True, cleanUp=True):
        def stock_code(symbol):         # return a 5-letter-long symbol
            while len(symbol) < 5:
                symbol = '0' + symbol
            print('Handling the company({})...'.format(symbol))
            return symbol

        def waiting_at_least_seconds(seconds):
            seconds = seconds + randint(0,4)
            print('Waiting for {} seconds...'.format(seconds))
            time.sleep(seconds)

        def retrieve_urls(symbol):          # companyName and symbol are set.
            print('Start crawling...')
            pdfs = []
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
            }

            session = requests.session()
            response = session.get('http://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', headers=headers)
            bs = BeautifulSoup(response.content, 'lxml')

            form_data = {
                '__VIEWSTATE': bs.find('input', { 'name': '__VIEWSTATE' }).get('value'),
                '__VIEWSTATEGENERATOR': bs.find('input', { 'name': '__VIEWSTATEGENERATOR' }).get('value'),
                '__VIEWSTATEENCRYPTED': bs.find('input', { 'name': '__VIEWSTATEENCRYPTED' }).get('value'),
                'ctl00$txt_today': bs.find('input', { 'name': 'ctl00$txt_today' }).get('value'),
                'ctl00$hfStatus': bs.find('input', { 'name': 'ctl00$hfStatus' }).get('value'),
                'ctl00$txt_stock_code': symbol,
                'ctl00$rdo_SelectDocType': 'rbAfter2006',
                'ctl00$sel_tier_1': 4,
                'ctl00$sel_DocTypePrior2006': -1,
                'ctl00$sel_tier_2_group': -2,
                'ctl00$sel_tier_2': -2,
                'ctl00$ddlTierTwo': bs.find('select', { 'name': 'ctl00$ddlTierTwo' }).select('option:nth-of-type(1)')[0].get('value'),     # can try "59,1,7"
                'ctl00$ddlTierTwoGroup': bs.find('select', { 'name': 'ctl00$ddlTierTwoGroup' }).select('option:nth-of-type(1)')[0].get('value'),     # can try "26,5",
                'ctl00$rdo_SelectDateOfRelease': 'rbManualRange',
                'ctl00$sel_DateOfReleaseFrom_d': '01',
                'ctl00$sel_DateOfReleaseFrom_m': '04',
                'ctl00$sel_DateOfReleaseFrom_y': '1999',
                'ctl00$sel_DateOfReleaseTo_d': '09',
                'ctl00$sel_DateOfReleaseTo_m': '08',
                'ctl00$sel_DateOfReleaseTo_y': '2018',
                'ctl00$sel_defaultDateRange': 'SevenDays',
                'ctl00$rdo_SelectSortBy': 'rbDateTime'
            }

            response = session.post('http://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', data=form_data, headers=headers)
            bs = BeautifulSoup(response.content, 'lxml')

            self.symbol = symbol
            self.companyName = bs.find('span', { 'id': 'ctl00_lblStockName' }).get_text()

            for pdf in bs.find_all('a', { 'class': 'news' }):
                # Format: name + publicationDate(for sake of sorting)
                fileName = '{} {}.pdf'.format(pdf.get_text(), ''.join(pdf.get('href').split('/')[4:6]))
                source = 'http://www.hkexnews.hk' + pdf.get('href')
                pdfs.append([fileName, source])
                print('PDF {} retrieved.'.format(pdf.get_text()))

            nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
            while nextBtn is not None:
                waiting_at_least_seconds(4)
                form_data = {
                    '__VIEWSTATE': bs.find('input', { 'name': '__VIEWSTATE' }).get('value'),
                    '__VIEWSTATEGENERATOR': bs.find('input', { 'name': '__VIEWSTATEGENERATOR' }).get('value'),
                    '__VIEWSTATEENCRYPTED': bs.find('input', { 'name': '__VIEWSTATEENCRYPTED' }).get('value'),
                    'ctl00$btnNext.x': 1,
                    'ctl00$btnNext.y': 1
                }
                response = session.post('http://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', data=form_data, headers=headers)
                bs = BeautifulSoup(response.content, 'lxml')
                for pdf in bs.find_all('a', { 'class': 'news' }):
                    # Format: name + publicationDate(for sake of sorting)
                    fileName = '{} {}.pdf'.format(pdf.get_text(), ''.join(pdf.get('href').split('/')[4:6]))
                    source = 'http://www.hkexnews.hk' + pdf.get('href')
                    pdfs.append([fileName, source])
                    print('PDF {} retrieved.'.format(pdf.get_text()))
                nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
                
            return pdfs

        def setDirectory(fileName):
            path = '{}/{}/{}'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol), fileName)
            directory = os.path.dirname(path)
            
            if not os.path.exists(directory):
                os.makedirs(directory)
            return path

        def download(source, localPath):
            def requests_retry_session(
                retries=3,
                backoff_factor=0.3,
                status_forcelist=(500, 502, 504),
                session=None,
            ):
                waiting_at_least_seconds(14)
                session = session or requests.Session()
                retry = Retry(
                    total=retries,
                    read=retries,
                    connect=retries,
                    backoff_factor=backoff_factor,
                    status_forcelist=status_forcelist,
                )
                adapter = HTTPAdapter(max_retries=retry)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                return session

            r = requests_retry_session().get(source)
            with open(localPath, 'wb') as f:
                copyfileobj(r.raw, f)

        def logDownloads(total, downloaded):
            if downloaded == total:
                print('All files downloaded successfully.')
            else:
                print('{} files downloaded. Got {} left...'.format(downloaded, total - downloaded))

        def merge_files(needCleanUp=cleanUp):
            print('Start gathering files...')
            pdfs = glob('{}/{}/*.pdf'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol)))
            pdfs.sort(key=lambda x: x[-12:])
            
            for pdf in pdfs:
                print(pdf)

            merger = PdfFileMerger()
            for pdf in pdfs:
                print('I am in!')
                merger.append(pdf)
            
            print('Starting merging...')
            with open('{}/{}.pdf'.format(self.downloadDirectory, self.companyName), 'wb') as tar:
                merger.write(tar)
                print('Merged successfully.')

            if needCleanUp:
                rmtree('{}/{}'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol)))
                print('Clean up.')

        if len(symbol) <= 5:
            symbol = stock_code(symbol)
            self.pdfs = retrieve_urls(symbol)

            # for i, pdf in enumerate(self.pdfs):
            #     fileName = pdf[0]
            #     source = pdf[1]
            #     localPath = setDirectory(fileName)
                
            #     print('Start downloading {} from {}'.format(fileName, source))
            #     download(source, localPath)
            #     logDownloads(len(self.pdfs), i+1)
            
            if mergeFiles:
                merge_files()
        else:
            print('The symbol provided is invalid.')

        print('Exit')

handler = PDFHandler('downloaded')
handler.get('813')
