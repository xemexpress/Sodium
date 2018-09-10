import os
import time
from random import randint
from urllib.request import urlretrieve
from glob import glob
from shutil import rmtree
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileMerger, PdfFileWriter

class FinReportHandler:
    downloadDirectory = ''      # The place pdf got saved
    companyName = ''            # Name of listed company
    symbol = ''                 # Symbol of listed company
    pdfs = []                   # [pathName] if downloaded else [(fileName, source)]

    def __init__(self, downloadDirectory):
        self.downloadDirectory = downloadDirectory
    
    def announce(self, message, wait=0, skip=0):
        print(message, end=' (waiting for {} seconds)'.format(wait) if wait is not 0 else '')
        while wait > 0:
            print('.', end='', flush=True)
            time.sleep(1)
            wait -= 1
        print('\n' * skip if skip is not 0 else '')

    # pdfs is set.
    def get(self, symbol, skipDownload, retryMax):
        # This would set companyName, symbol and pdfs.
        def set_class_properties(symbol=symbol, skipPdfs=skipDownload):
            def stock_code(symbol):         # return a 5-letter-long symbol
                while len(symbol) < 5:
                    symbol = '0' + symbol
                print('Handling the company({})...'.format(symbol))
                return symbol

            def append_urls(bs, pdfs):
                for pdf in bs.find_all('a', { 'class': 'news' }):
                    # Format: name + publicationDate(for sake of sorting)
                    fileName = '{} {}.pdf'.format(pdf.get_text().replace('/', '%'), ''.join(pdf.get('href').split('/')[4:6]))
                    source = 'http://www.hkexnews.hk' + pdf.get('href')
                    pdfs.append([fileName, source])
                    print('PDF {} retrieved.'.format(pdf.get_text()))

            self.symbol = stock_code(symbol)
            self.announce('Start crawling', wait=(4+randint(0,4)))
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
                'ctl00$txt_stock_code': self.symbol,
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

            self.companyName = bs.find('span', { 'id': 'ctl00_lblStockName' }).get_text()
            
            if not skipPdfs:
                append_urls(bs, self.pdfs)

                nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
                while nextBtn is not None:
                    self.announce('Heading to next button', wait=(4+randint(0,4)))
                    form_data = {
                        '__VIEWSTATE': bs.find('input', { 'name': '__VIEWSTATE' }).get('value'),
                        '__VIEWSTATEGENERATOR': bs.find('input', { 'name': '__VIEWSTATEGENERATOR' }).get('value'),
                        '__VIEWSTATEENCRYPTED': bs.find('input', { 'name': '__VIEWSTATEENCRYPTED' }).get('value'),
                        'ctl00$btnNext.x': 1,
                        'ctl00$btnNext.y': 1
                    }
                    response = session.post('http://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', data=form_data, headers=headers)
                    bs = BeautifulSoup(response.content, 'lxml')
                    append_urls(bs, self.pdfs)
                    nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
                print('Total: {} files from {} {}.\n\n\n\n'.format(len(self.pdfs), self.companyName, self.symbol))
            else:
                print('Skip download process.\n\n\n\n')

        def set_directory(fileName):
            path = '{}/{}/{}'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol), fileName)
            directory = os.path.dirname(path)
            
            if not os.path.exists(directory):
                os.makedirs(directory)
            return path

        def log_downloads(total, acquired, existed):
            if acquired == total:
                self.announce('All files acquired successfully.', skip=7)
            else:
                print('{}. Got {} left.'.format('Downloaded' if not existed else 'Detected', total - acquired))

        if len(symbol) <= 5:
            set_class_properties()

            if not skipDownload:
                prev = glob('{}/{}/*.pdf'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol)))
                for i, pdf in enumerate(self.pdfs):
                    fileName = pdf[0]
                    source = pdf[1]
                    localPath = set_directory(fileName)
                    existed = localPath in prev
                    print('Start working on {}...'.format(fileName))
                    if not existed:
                        print('Downloading from {}'.format(source))
                        for j in range(retryMax):
                            try:
                                urlretrieve(source, localPath)
                                break
                            except:
                                self.announce('Retrying again', wait=(4+randint(0,4)))
                                pass
                    log_downloads(len(self.pdfs), i+1, existed)

            self.pdfs = glob('{}/{}/*.pdf'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol)))
            self.pdfs.sort(key=lambda x: x[-12:])
        else:
            print('The symbol provided is invalid.')

    def extract_tables(self, wanted, unwanted, onlyFirstThree):
        def head_and_tail(reader, destinations, wantedWord=wanted, unwantedWord=unwanted, requireConsolidated=onlyFirstThree):
            # Destination's format: [(title, pageNum)]
            lastMark = None
            markNext = False
            for des in reader.getOutlines():
                lastMark = des if markNext else lastMark

                if requireConsolidated and len(destinations) == 3:
                    break

                markNext = type(des) is not list and wantedWord in des.title and unwantedWord not in des.title
                if markNext:
                    destinations.append((des.title, reader.getDestinationPageNumber(des)))
                    print('{} extracted'.format(des.title))
            destinations.append((lastMark.title, reader.getDestinationPageNumber(lastMark)) if lastMark is not None else lastMark)

            return range(destinations[0][1], destinations[-1][1]) if destinations[0] is not None else []

        print('Start extracting tables...')
        writer = PdfFileWriter()
        printingPage = 0
        for pdf in self.pdfs:
            fileName = pdf.split('/')[-1][:-13]
            print('Searching in {}...'.format(fileName))
            reader = PdfFileReader(pdf)
            isFirstPage = True
            parent = None
            bookmarks = []
            for i in head_and_tail(reader, bookmarks):
                page = reader.getPage(i)
                writer.addPage(page)
                title = [title for title, pageNum in bookmarks if i == pageNum]
                if isFirstPage:
                    parent = writer.addBookmark(fileName, printingPage)
                    isFirstPage = False
                if title:
                    writer.addBookmark(title[0], printingPage, parent)
                printingPage += 1
        
        with open('{}/{} Tables.pdf'.format(self.downloadDirectory, self.companyName), 'wb') as tar:
            writer.write(tar)
            self.announce('Tables merged successfully.', skip=7)

    def extract_notes(self, wanted):
        def head_and_tail(reader, wanted=wanted):
            first = None
            end = None

            markNext = False
            for des in reader.getOutlines():
                end = des if markNext else end

                markNext = '附註' in des.title
                if markNext:
                    print('Notes extracted.')
                    first = reader.getDestinationPageNumber(des)
            end = reader.getDestinationPageNumber(end) if end else (reader.getNumPages()+1)
            return range(first, end)

        print('Start extracting notes...')
        writer = PdfFileWriter()
        printingPage = 0
        for pdf in self.pdfs:
            # Extract notes
            title = pdf.split('/')[-1][:-13] + ' 附註'
            print('Searching in {}...'.format(title[:-3]))
            reader = PdfFileReader(pdf)
            isFirstPage = True
            for i in head_and_tail(reader):
                page = reader.getPage(i)
                writer.addPage(page)
                if isFirstPage:
                    writer.addBookmark(title, printingPage)
                    isFirstPage = False
                printingPage += 1

        with open('{}/{} Notes.pdf'.format(self.downloadDirectory, self.companyName), 'wb') as tar:
            writer.write(tar)
            self.announce('Notes merged successfully.', skip=7)

    def merge_files(self):
            print('Start merging files...')
            merger = PdfFileMerger()
            for pdf in self.pdfs:
                fileName = pdf.split('/')[-1][:-13]
                merger.append(pdf, bookmark=fileName)
                print('{} merged.'.format(fileName))

            print('Start writing...')
            with open('{}/{}.pdf'.format(self.downloadDirectory, self.companyName), 'wb') as tar:
                merger.write(tar)
                self.announce('Merged successfully.', skip=7)

    def clean_up(self):
        rmtree('{}/{}'.format(self.downloadDirectory, '{}{}'.format(self.companyName, self.symbol)))
        print('Cleaned up.')
