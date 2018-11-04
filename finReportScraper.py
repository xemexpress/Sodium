import os
import time
from random import randint
from urllib.request import urlretrieve
from glob import glob
from shutil import rmtree
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileMerger, PdfFileWriter

class BasicTools:
    session = requests.session()

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }
    
    def announce(self, message, wait=0, skip=0):
        print(message, end=' (waiting for {} seconds)'.format(wait) if wait is not 0 else '')
        while wait > 0:
            print('.', end='', flush=True)
            time.sleep(1)
            wait -= 1
        print('\n' * skip if skip is not 0 else '')

    def report(self, message):
        print(message)
        time.sleep(0.2)

    def log_downloads(self, total, acquired, existed):
        if acquired == total:
            self.announce('All files acquired successfully.', skip=7)
        else:
            print('{}. Got {} left.'.format('Downloaded' if not existed else 'Detected', total - acquired))

    def stock_code(self, symbol):         # return a 5-letter-long symbol
        return symbol if len(symbol) == 5 else '0'*(5-len(symbol))+symbol

    def append_urls(self, bs, pdfs, unwantedWord='多檔案'):                          # Format: [(fileName, source)]
        for pdf in bs.find_all('a', { 'class': 'news' }):
            # Format: name + publicationDate(for sake of sorting)
            if unwantedWord not in pdf.next_sibling.next_sibling.string and unwantedWord not in pdf.get_text():
                fileName = '{} {}.pdf'.format(pdf.get_text().replace('/', '%'), ''.join(pdf.get('href').split('/')[4:6]))
                source = 'http://www3.hkexnews.hk' + pdf.get('href')
                pdfs.append([fileName, source])
                print('PDF {} retrieved.'.format(pdf.get_text()))
            else:
                print('PDF {} with {} skipped.'.format(pdf.get_text(), pdf.next_sibling.next_sibling.string))
    
    def set_directory(self, downloadDirectory, fileName, companyName, symbol):
        path = '{}/{}/reports/{}'.format(downloadDirectory, '{}{}'.format(symbol, companyName), fileName)
        directory = os.path.dirname(path)
        
        if not os.path.exists(directory):
            os.makedirs(directory)
        return path

    def retrieve_all_symbols(self, symbol, retryMax):              # Format: [(symbol, companyName)]
        self.report('Retrieving all possible symbols and companyNames from HKEX...\n')

        site = 'http://www3.hkexnews.hk/listedco/listconews/advancedsearch/stocklist_active_main_c.htm'

        for i in range(retryMax):
            try:
                response = self.session.get(site, headers=self.headers)
                break
            except:
                self.announce('Retrying again', wait=(i*10+randint(0,4)))
                pass

        bs = BeautifulSoup(response.content, 'lxml')
        
        self.report('Data retrieved. Further processing...\n')

        result = bs.select("[class^=TableContentStyle]")
        
        if symbol == 'ALL':
            result = list(filter(lambda x: x.contents[0].get_text()[0] == '0' and x.contents[0].get_text()[1] in ['0', '1', '2', '3', '6', '8'], result))
        else:
            symbol = self.stock_code(symbol)
            result = list(filter(lambda x: x.contents[0].get_text() == symbol, result))
        result = list(map(lambda x: [x.contents[0].get_text(), x.contents[1].get_text()], result))
        
        if len(result) == 0:
            print("{} can't be found. Please check.".format(symbol))
            exit()
        
        self.announce('Data are already formatted in form of [symbol, companyName]', skip=7)
        return result

class FinReportHandler(BasicTools):
    downloadDirectory = ''
    retryMax = 0
    symbols = []                # [(symbol, companyName)]
    pdfs = []                   # [(fileName, source)]

    def __init__(self, downloadDirectory, retryMax, symbol, fromSymbol=None):
        print('\n'*20)

        self.downloadDirectory = downloadDirectory
        self.retryMax = retryMax

        # Set symbols
        if symbol == 'ALL':
            self.announce("REMINDING: You're conducting a COMPLETE financial reports search", wait=7, skip=7)
        
        self.symbols = self.retrieve_all_symbols(symbol, retryMax)
        if symbol == 'ALL':
            if fromSymbol is None:
                return
            else:
                fromSymbol = self.stock_code(fromSymbol)
                for i, unit in enumerate(self.symbols):
                    if unit[0] == fromSymbol:
                        self.symbols = self.symbols[i:]
                        print('Starting from {} {}...'.format(unit[1], unit[0]))
                        return
                symbol = fromSymbol
        else:
            symbol = self.stock_code(symbol)
            for i, unit in enumerate(self.symbols):
                if unit[0] == symbol:
                    self.symbols = self.symbols[i:i+1]
                    print('Working on {} {}...'.format(unit[1], unit[0]))
                    return

        print("{} can't be found. Please check.".format(symbol))
        exit()
        
    def get(self, companyName, symbol): # This sets self.pdfs
        self.pdfs = []

        for i in range(self.retryMax):
            try:
                response = self.session.get('http://www3.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', headers=self.headers)
                break
            except:
                self.announce('Retrying again', wait=(4+randint(0,4)))
                pass

        bs = BeautifulSoup(response.content, 'lxml')

        date = bs.find('input', { 'name': 'ctl00$txt_today' }).get('value')
        date = {
            'year': date[:4],
            'month': date[4:6],
            'day': date[-2:]
        }

        form_data = {
            '__VIEWSTATE': bs.find('input', { 'name': '__VIEWSTATE' }).get('value'),
            '__VIEWSTATEGENERATOR': bs.find('input', { 'name': '__VIEWSTATEGENERATOR' }).get('value'),
            '__VIEWSTATEENCRYPTED': bs.find('input', { 'name': '__VIEWSTATEENCRYPTED' }).get('value'),
            'ctl00$txt_today': date['year']+date['month']+date['day'],
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
            'ctl00$sel_DateOfReleaseTo_d': date['day'],
            'ctl00$sel_DateOfReleaseTo_m': date['month'],
            'ctl00$sel_DateOfReleaseTo_y': date['year'],
            'ctl00$sel_defaultDateRange': 'SevenDays',
            'ctl00$rdo_SelectSortBy': 'rbDateTime'
        }
        for i in range(self.retryMax):
            try:
                response = self.session.post('http://www3.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', data=form_data, headers=self.headers)
                break
            except:
                self.announce('Retrying again', wait=(i*10+randint(0,4)))
                pass
        bs = BeautifulSoup(response.content, 'lxml')

        self.append_urls(bs, self.pdfs)

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
            for i in range(self.retryMax):
                try:
                    response = self.session.post('http://www3.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx', data=form_data, headers=self.headers)
                    break
                except:
                    self.announce('Retrying again', wait=(i*10+randint(0,4)))
                    pass
            bs = BeautifulSoup(response.content, 'lxml')
            self.append_urls(bs, self.pdfs)
            nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
        print('Total: {} files from {} {}.\n\n\n\n'.format(len(self.pdfs), companyName, symbol))
        
        prev = glob('{}/{}/reports/*.pdf'.format(self.downloadDirectory, '{}{}'.format(symbol, companyName)))
        for i, pdf in enumerate(self.pdfs):
            fileName = pdf[0]
            source = pdf[1]
            localPath = self.set_directory(self.downloadDirectory, fileName, companyName, symbol)
            existed = localPath in prev
            print('Start working on {}...'.format(fileName))
            if not existed:
                print('Downloading from {}'.format(source))
                for j in range(self.retryMax):
                    try:
                        urlretrieve(source, localPath)
                        break
                    except:
                        self.announce('Retrying again', wait=(4+randint(0,4)))
                        pass
            self.log_downloads(len(self.pdfs), i+1, existed)

        self.pdfs = glob('{}/{}/reports/*.pdf'.format(self.downloadDirectory, '{}{}'.format(symbol, companyName)))
        self.pdfs.sort(key=lambda x: x[-12:])
        
    def extract_tables(self, companyName, symbol, onlyFirstThree, wanted='表', unwanted='附註'):
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
            if lastMark is not None:
                destinations.append((lastMark.title, reader.getDestinationPageNumber(lastMark)))
            else:
                destinations.append(('.', reader.getNumPages()))

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
        
        with open('{}/{}/{} {} Tables.pdf'.format(self.downloadDirectory, '{}{}'.format(symbol, companyName), companyName, 'Consolidated' if onlyFirstThree else ''), 'wb') as tar:
            writer.write(tar)
            self.announce('Tables merged successfully.', skip=7)

    def merge_whole(self, companyName, symbol):
            print('Start merging files...')
            merger = PdfFileMerger()
            for pdf in self.pdfs:
                fileName = pdf.split('/')[-1][:-13]
                merger.append(pdf, bookmark=fileName)
                print('{} merged.'.format(fileName))

            print('Start writing...')
            with open('{}/{}/{}.pdf'.format(self.downloadDirectory, '{}{}'.format(symbol, companyName), companyName), 'wb') as tar:
                merger.write(tar)
                self.announce('Merged successfully.', skip=7)

    def clean_up(self, companyName, symbol):
        rmtree('{}/{}/reports'.format(self.downloadDirectory, '{}{}'.format(symbol, companyName)))
        print('Cleaned up.')

    def process(self, consolidatedTables, tables, mergeFiles, cleanUp):
        for (symbol, company) in self.symbols:
            self.announce('{}: Getting reports'.format(company), wait=(7+randint(0,4)))
            self.get(company, symbol)

            if mergeFiles:
                self.merge_whole(company, symbol)
            if consolidatedTables or tables:
                self.extract_tables(company, symbol, onlyFirstThree=consolidatedTables)
            if cleanUp:
                self.clean_up(company, symbol)
