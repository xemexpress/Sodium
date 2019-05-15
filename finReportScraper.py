import os
import time
from random import randint
from urllib.request import urlretrieve
from glob import glob
from shutil import rmtree
import smtplib
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileMerger, PdfFileWriter
from credentials import sender_email, sender_password, receiver_email

class BasicTools:
    session = requests.session()

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    allSymbolResults = []

    lang = 'ch'

    source_site = ''

    wanted_word = '報'

    unwanted_word = '多檔案'
    
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

    def send_alert(self, subject, symbol):
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls() 
        s.login(sender_email, sender_password)
        msg = MIMEText('Symbol: {}\n\n'.format(symbol))
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        s.send_message(msg)
        s.quit()
        print('Email sent.')

    def stock_code(self, symbol):         # return a 5-letter-long symbol
        return symbol if len(symbol) == 5 else '0'*(5-len(symbol))+symbol

    def append_urls(self, bs, pdfs, wanted_word='報', unwanted_word='多檔案'):                          # Format: [(file_name, source)]
        for pdf in bs.find_all('a', { 'class': 'news' }):
            linkText = pdf.get_text()
            # Format: name + publicationDate(for sake of sorting)
            if wanted_word in linkText and unwanted_word not in pdf.next_sibling.next_sibling.string and unwanted_word not in linkText:
                file_name = '{} {}.pdf'.format(linkText.replace('/', '%'), ''.join(pdf.get('href').split('/')[4:6]))
                source = 'http://www3.hkexnews.hk' + pdf.get('href')
                pdfs.append([file_name, source])
                print('PDF {} retrieved.'.format(linkText))
            else:
                print('PDF {} with {} skipped.'.format(linkText, pdf.next_sibling.next_sibling.string))
    
    def set_directory(self, download_directory, file_name, company_name, symbol):
        path = '{}/{}/reports/{}'.format(download_directory, '{}{}'.format(symbol, company_name), file_name)
        directory = os.path.dirname(path)
        
        if not os.path.exists(directory):
            os.makedirs(directory)
        return path

    def retrieve_all_symbols(self, symbol, retry_max):              # Format: [(symbol, company_name)]
        if(len(self.allSymbolResults) == 0):
            self.report('Retrieving all possible symbols and company_names from HKEX...\n')

            site = 'http://www3.hkexnews.hk/listedco/listconews/advancedsearch/stocklist_active_main_c.htm'

            for i in range(retry_max):
                try:
                    response = self.session.get(site, headers=self.headers)
                    break
                except:
                    self.announce('Retrying again', wait=(i*10+randint(0,4)))
                    pass

            bs = BeautifulSoup(response.content, 'lxml')
            
            self.report('Data retrieved. Further processing...\n')

            self.allSymbolResults = bs.select("[class^=TableContentStyle]")
        
        if symbol == 'ALL':
            result = list(filter(lambda x: x.contents[0].get_text()[0] == '0' and x.contents[0].get_text()[1] in ['0', '1', '2', '3', '6', '8'], self.allSymbolResults))
        else:
            symbol = self.stock_code(symbol)
            result = list(filter(lambda x: x.contents[0].get_text() == symbol, self.allSymbolResults))
        result = list(map(lambda x: [x.contents[0].get_text(), x.contents[1].get_text()], result))
        
        if len(result) == 0:
            print("{} can't be found. Please check.".format(symbol))
            exit()
        
        self.announce('Data are already formatted in form of [symbol, company_name]', skip=7)
        return result

class FinReportHandler(BasicTools):
    download_directory = ''
    retry_max = 0
    symbols = []                # [(symbol, company_name)]
    pdfs = []                   # [(file_name, source)]

    def __init__(self, download_directory, retry_max, symbol, from_symbol=None, lang='ch'):
        print('\n'*20)

        self.download_directory = download_directory
        self.retry_max = retry_max
        self.lang = lang
        self.source_site = f'http://www3.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main{"_c" if self.lang=="ch" else ""}.aspx'

        self.wanted_word = '報' if self.lang == 'ch' else 'REPORT'
        
        # Set symbols
        if symbol == 'ALL':
            self.announce("REMINDING: You're conducting a COMPLETE financial reports search", wait=7, skip=7)
        
        self.symbols = self.retrieve_all_symbols(symbol, retry_max)
        if symbol == 'ALL':
            if from_symbol is None:
                return
            else:
                from_symbol = self.stock_code(from_symbol)
                for i, unit in enumerate(self.symbols):
                    if unit[0] == from_symbol:
                        self.symbols = self.symbols[i:]
                        print('Starting from {} {}...'.format(unit[1], unit[0]))
                        return
                symbol = from_symbol
        else:
            symbol = self.stock_code(symbol)
            for i, unit in enumerate(self.symbols):
                if unit[0] == symbol:
                    self.symbols = self.symbols[i:i+1]
                    print('Working on {} {}...'.format(unit[1], unit[0]))
                    return

        print("{} can't be found. Please check.".format(symbol))
        exit()
        
    def get(self, company_name, symbol): # This sets self.pdfs
        self.pdfs = []

        for i in range(self.retry_max):
            try:
                response = self.session.get(self.source_site, headers=self.headers)
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
        for i in range(self.retry_max):
            try:
                response = self.session.post(self.source_site, data=form_data, headers=self.headers)
                break
            except:
                self.announce('Retrying again', wait=(i*10+randint(0,4)))
                pass
        bs = BeautifulSoup(response.content, 'lxml')

        self.append_urls(bs, self.pdfs, wanted_word=self.wanted_word)

        next_btn = bs.find('input', { 'name': 'ctl00$btnNext' })
        while next_btn is not None:
            self.announce('Heading to next button', wait=(4+randint(0,4)))
            form_data = {
                '__VIEWSTATE': bs.find('input', { 'name': '__VIEWSTATE' }).get('value'),
                '__VIEWSTATEGENERATOR': bs.find('input', { 'name': '__VIEWSTATEGENERATOR' }).get('value'),
                '__VIEWSTATEENCRYPTED': bs.find('input', { 'name': '__VIEWSTATEENCRYPTED' }).get('value'),
                'ctl00$btnNext.x': 1,
                'ctl00$btnNext.y': 1
            }
            for i in range(self.retry_max):
                try:
                    response = self.session.post(self.source_site, data=form_data, headers=self.headers)
                    break
                except:
                    self.announce('Retrying again', wait=(i*10+randint(0,4)))
                    pass
            bs = BeautifulSoup(response.content, 'lxml')
            self.append_urls(bs, self.pdfs, wanted_word=self.wanted_word)
            next_btn = bs.find('input', { 'name': 'ctl00$btnNext' })

        if len(self.pdfs) != 0:
            print('Total: {} files from {} {}.\n\n\n\n'.format(len(self.pdfs), company_name, symbol))
            
            prev = glob('{}/{}/reports/*.pdf'.format(self.download_directory, '{}{}{}'.format(symbol, company_name, '' if self.lang == 'ch' else '_en')))
            for i, pdf in enumerate(self.pdfs):
                file_name = pdf[0]
                source = pdf[1]
                local_path = self.set_directory(self.download_directory, file_name, company_name, symbol)
                existed = local_path in prev
                print('Start working on {}...'.format(file_name))
                if not existed:
                    print('Downloading from {}'.format(source))
                    for j in range(self.retry_max):
                        try:
                            urlretrieve(source, local_path)
                            break
                        except:
                            self.announce('Retrying again', wait=(4+randint(0,4)))
                            pass
                self.log_downloads(len(self.pdfs), i+1, existed)

            self.pdfs = glob('{}/{}/reports/*.pdf'.format(self.download_directory, '{}{}{}'.format(symbol, company_name, '' if self.lang == 'ch' else '_en')))
            self.pdfs.sort(key=lambda x: x[-12:])
        else:
            print('No financial reports listed. Exit.\n')
            exit()
        
    def extract_tables(self, company_name, symbol, only_first_three, wanted='表', unwanted='附註'):
        def head_and_tail(reader, destinations, wanted_word=wanted, unwanted_word=unwanted, require_consolidated=only_first_three):
            # Destination's format: [(title, pageNum)]
            last_mark = None
            mark_next = False
            for des in reader.getOutlines():
                last_mark = des if mark_next else last_mark

                if require_consolidated and len(destinations) == 3:
                    break

                mark_next = type(des) is not list and wanted_word in des.title and unwanted_word not in des.title
                if mark_next:
                    destinations.append((des.title, reader.getDestinationPageNumber(des)))
                    print('{} extracted'.format(des.title))
            if last_mark is not None:
                destinations.append((last_mark.title, reader.getDestinationPageNumber(last_mark)))
            else:
                destinations.append(('.', reader.getNumPages()))

            return range(destinations[0][1], destinations[-1][1]) if destinations[0] is not None else []

        if len(self.pdfs) != 0:
            print('Start extracting tables...')
            writer = PdfFileWriter()
            printing_page = 0
            for pdf in self.pdfs:
                file_name = pdf.split('/')[-1][:-13]
                print('Searching in {}...'.format(file_name))
                reader = PdfFileReader(pdf)
                is_first_page = True
                parent = None
                bookmarks = []
                for i in head_and_tail(reader, bookmarks):
                    page = reader.getPage(i)
                    writer.addPage(page)
                    title = [title for title, pageNum in bookmarks if i == pageNum]
                    if is_first_page:
                        parent = writer.addBookmark(file_name, printing_page)
                        is_first_page = False
                    if title:
                        writer.addBookmark(title[0], printing_page, parent)
                    printing_page += 1
            
            with open('{}/{}/{} {} Tables.pdf'.format(self.download_directory, '{}{}'.format(symbol, company_name), company_name, 'Consolidated' if only_first_three else ''), 'wb') as tar:
                writer.write(tar)
                self.announce('Tables merged successfully.', skip=7)

    def merge_whole(self, company_name, symbol):
        if len(self.pdfs) != 0:
            print('Start merging files...')
            merger = PdfFileMerger()
            for pdf in self.pdfs:
                file_name = pdf.split('/')[-1][:-13]
                merger.append(pdf, bookmark=file_name)
                print('{} merged.'.format(file_name))

            print('Start writing...')
            with open('{}/{}/{}.pdf'.format(self.download_directory, '{}{}'.format(symbol, company_name), company_name), 'wb') as tar:
                merger.write(tar)
                self.announce('Merged successfully.', skip=7)

    def clean_up(self, company_name, symbol):
        rmtree('{}/{}/reports'.format(self.download_directory, '{}{}'.format(symbol, company_name)))
        print('Cleaned up.')

    def process(self, consolidated_tables, tables, merge_files, clean_up):
        for (symbol, company) in self.symbols:
            # try:
                self.announce('{}: Getting reports'.format(company), wait=(7+randint(0,4)))
                self.get(company, symbol)

                if merge_files:
                    self.merge_whole(company, symbol)
                if consolidated_tables or tables:
                    self.extract_tables(company, symbol, only_first_three=consolidated_tables)
                if clean_up:
                    self.clean_up(company, symbol)
            # except:
            #     self.send_alert('Report Download Alert', symbol)   
