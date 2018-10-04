import time
from random import randint
from math import floor, log10
import json
import requests
from bs4 import BeautifulSoup
from hanziconv import HanziConv

class BasicTools:
  session = requests.session()

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

  def log(self, response, informative=True):
    bs = BeautifulSoup(response.content, 'lxml')
    json_string = bs.get_text()
    data = json.loads(json_string) if '{' in json_string and '}' in json_string else None
    if data:
      if 'errors' in data:
        return { 'state': False, 'data': data['errors'] }
      else:
        if informative:
          print('Success.')
        return { 'state': True, 'data': data }
    else:
      print('Error: {}'.format(json_string))
      return { 'state': False, 'data': json_string }
    
  def retrieve_all_symbols(self):           # Format: [symbol, companyName]
    self.report('Retrieving all possible symbols and companyNames from HKEX...\n')

    site = 'http://www.hkexnews.hk/listedco/listconews/advancedsearch/stocklist_active_main_c.htm'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    for i in range(self.retryMax):
      try:
        response = self.session.get(site, headers=headers)
        break
      except:
        self.announce('Retrying again', wait=(i*10+randint(0,4)))
        pass

    bs = BeautifulSoup(response.content, 'lxml')
    
    self.report('Data retrieved. Further processing...\n')
    result = bs.select("[class^=TableContentStyle]")
    result = list(filter(lambda x: x.contents[0].get_text()[0] == '0' and x.contents[0].get_text()[1] in ['0', '1', '2', '3', '6', '8'], result))
    result = list(map(lambda x: [x.contents[0].get_text(), x.contents[1].get_text()], result))
    self.announce('Data are already formatted in form of [symbol, companyName]', skip=7)
    return result

  def round_sigfigs(self, num, sig_figs):
    if num != 0:
      return round(num, -int(floor(log10(abs(num))) - (sig_figs - 1)))
    else:
      return 0

class FinDataScraper(BasicTools):
  apiUrl = ''
  token = ''
  retryMax = 0
  symbols = []
  existedFinancialYears = None

  def __init__(self, apiUrl, token, retryMax, symbol, fromSymbol=None):
    print('\n'*20)

    self.apiUrl = apiUrl
    self.token = token
    self.retryMax = retryMax

    # Set symbols
    if symbol == 'ALL':
      self.announce("REMINDING: You're conducting a COMPLETE financial data search", wait=7, skip=7)
    
    self.symbols = self.retrieve_all_symbols()
    if symbol == 'ALL':
      if fromSymbol is None:
        return
      else:
        fromSymbol = fromSymbol if len(fromSymbol) == 5 else '0'*(5-len(fromSymbol))+fromSymbol
        for i, unit in enumerate(self.symbols):
          if unit[0] == fromSymbol:
            self.symbols = self.symbols[i:]
            print('Starting from {} {}...'.format(unit[1], unit[0]))
            return
        symbol = fromSymbol
    else:
      symbol = symbol if len(symbol) == 5 else '0'*(5-len(symbol))+symbol
      for i, unit in enumerate(self.symbols):
        if unit[0] == symbol:
          self.symbols = self.symbols[i:i+1]
          print('Working on {} {}...'.format(unit[1], unit[0]))
          return

    print("{} can't be found. Please check.".format(symbol))
    exit()

  def ensure_company(self, symbol, companyName):
    companyAPIs = {
      'get': '/companies/{}'.format(symbol.lstrip('0')),
      'post': '/companies'
    }

    site = '{}{}'.format(self.apiUrl, companyAPIs['get'])
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Token {}'.format(self.token)
    }

    for i in range(self.retryMax):
      try:
        response = self.session.get(site, headers=headers)
        break
      except:
        self.announce('Retrying again', wait=(i*10+randint(0,4)))
        pass
    
    if not self.log(response)['state']:
      self.announce('Creating company {} {}...'.format(companyName, symbol), wait=3)
      
      site = 'http://basic.10jqka.com.cn/{}{}/company.html'.format(self.region, symbol[-4:])
      headers = {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept-Encoding': 'gzip, deflate',
          'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
      }

      for i in range(self.retryMax):
        try:
          response = self.session.get(site, headers=headers)
          break
        except:
          self.announce('Retrying again', wait=(i*10+randint(0,4)))
          pass
      
      bs = BeautifulSoup(response.content, 'lxml')
      target = bs.find('table', { 'class': 'm_table' }).select('td span')

      companyFullName = HanziConv.toTraditional(target[0].get_text().strip())
      website = target[10].get_text()

      data = {
        'company': {
          'symbol': symbol.lstrip('0'),
          'name': companyFullName,
          'abbr': companyName,
          'link': 'http://{}'.format(website)
        }
      }
      json_company = json.dumps(data)
      
      site = '{}{}'.format(self.apiUrl, companyAPIs['post'])
      headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token {}'.format(self.token)
      }

      for i in range(self.retryMax):
        try:
          response = self.session.post(site, headers=headers, data=json_company)
          break
        except:
          self.announce('Retrying again', wait=(i*10+randint(0,4)))
          pass
      self.report('Company created.')
    else:
      self.report('Company existed.')

  def check_existed_financial_years(self, symbol):
    site = '{}{}'.format(self.apiUrl, self.financialAPI(symbol))
    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Token {}'.format(self.token)
    }

    for i in range(self.retryMax):
      try:
        response = self.session.get(site, headers=headers)
        break
      except:
        self.announce('Retrying again', wait=(i*10+randint(0,4)))
        pass
    
    response = self.log(response, informative=False)['data']
    self.existedFinancialYears = response['financials'] if 'financials' in response else []
    self.existedFinancialYears = list(map(lambda financial: financial['year'], self.existedFinancialYears))

  def make_hundred_millions(self, value, originalUnit):
    if value is not '':
      value = float(value)
      if originalUnit.startswith('万'):
        value = value * 10000
      value = round(value / 100000000, 6)
      return value
    else:
      return None

  def financialAPI(self, symbol, year=None):
    return '/companies/{}/financials{}'.format(symbol.lstrip('0'), '/{}'.format(year) if year is not None else '')

class Fin10JQKA(FinDataScraper):
  site = 'http://basic.10jqka.com.cn'
  region = 'HK'

  resonance = None
  position = None
  cashFlow = None
  equityRecords = []
  
  financials = []
  year_sigs = []

  catched = []

  def __init__(self, apiUrl, token, retryMax, symbol, fromSymbol=None):
    super().__init__(apiUrl, token, retryMax, symbol, fromSymbol)
    self.report('Task:\n\tTarget {} from {} for resonance, position and cashFlow.'.format(symbol, self.site))

  def get_all_statements(self, symbol, retryMax):
    site = '{}/{}{}/finance.html'.format(self.site, self.region, symbol[1:])
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    for i in range(self.retryMax):
      try:
        response = self.session.get(site, headers=headers)
        break
      except:
        self.announce('Retrying again', wait=(i*10+randint(0,4)))
        pass

    self.report('Online source retrieved. Now getting into the data...')
    bs = BeautifulSoup(response.content, 'lxml')
    if bs.find(id='benefit'):
      self.resonance = json.loads(bs.find(id='benefit').get_text())
      self.report('利潤表 retrieved.')
      self.position = json.loads(bs.find(id='debt').get_text())
      self.report('資產負債表 retrieved.')
      self.cashFlow = json.loads(bs.find(id='cash').get_text())
      self.report('現金流量表 retrieved.')
      return True
    else:
      return None

  def get_equity_records(self, symbol, retryMax):
    # Reset equityRecords
    self.equityRecords = []

    site = '{}/{}{}/equity.html'.format(self.site, self.region, symbol[1:])
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    for i in range(self.retryMax):
      try:
        response = self.session.get(site, headers=headers)
        break
      except:
        self.announce('Retrying again', wait=(i*10+randint(0,4)))
        pass

    self.report('Equity records retrieved. Now getting into the data...')
    bs = BeautifulSoup(response.content, 'lxml')

    unit = bs.find('p', { 'class': 'p5_0 tr' })
    if unit is not None:
      unit = unit.get_text()[-3:]
      print('Equity unit:', unit)
      if unit == '百万股':
        target = bs.find('div', { 'id': 'change' })
        table = target.find('table', { 'class': 'm_table m_hl' })

        changes = table.find_all('tr')
        for change in changes:
          items = change.find_all('td')
          date = None
          equity = 1
          for i, item in enumerate(items):
            if i == 1:
              equity = int(float(item.get_text().strip())*1000000)
            elif i == 3:
              date = item.get_text().strip().replace('-', '')
          if date is not None:
            self.equityRecords.append((date, equity))
      else:
        print('Another unit is found:', unit)
        exit()
    else:
      self.catched.append(symbol)
      self.report('Equity records retrieved is not as expected. Catched. Now getting into another set of data...')
      site = '{}/{}{}/holder.html'.format(self.site, self.region, symbol[1:])

      for i in range(self.retryMax):
        try:
          response = self.session.get(site, headers=headers)
          break
        except:
          self.announce('Retrying again', wait=(i*10+randint(0,4)))
          pass
      bs = BeautifulSoup(response.content, 'lxml')

      holder_change_record = bs.find('table', { 'class': 'mt15 m_table m_hl'})
      if holder_change_record is not None:
        unit_target = holder_change_record.select('thead th')[3].get_text()
        unit = unit_target[unit_target.find('(')+1 : unit_target.find(')')]

        if unit == '万股':
          changes = holder_change_record.select('tbody tr')
          prev_date = ''
          for change in changes:
            date = change.find('th').get_text().replace('-','')
            items = change.find_all('td')

            part = float(items[2].get_text()) * 10000
            percentage = float(items[3].get_text()) / 100
            equity = int(self.round_sigfigs(part/percentage, 3))
            if date != prev_date:
              self.equityRecords.append((date, equity))
              prev_date = date
        else:
          print('Another unit is found:', unit)
          exit()
      else:
        print('holder_change_record is not found as expected. Please go check.')
        exit()

  def sort_financials(self):
    # Get Periods Ready
    self.report('Retrieving periods...')
    report_periods = self.cashFlow['report'][0]
    year_periods = self.cashFlow['year'][0]

    # Get Statements Clear
    self.report('Processing all statements...')
    # Processing 利潤表
    self.resonance['title'] = self.resonance['title'][1:]
    self.resonance['report'] = self.resonance['report'][1:]

    # Processing 資產負債表
    self.position['title'] = self.position['title'][1:]
    self.position['report'] = self.position['report'][1:]
    
    # Processing 現金流量表
    self.cashFlow['title'] = self.cashFlow['title'][1:]
    self.cashFlow['report'] = self.cashFlow['report'][1:]
    self.cashFlow['year'] = self.cashFlow['year'][1:]

    # Reset financials and year signatures
    self.financials = []
    if year_periods is not None:
      self.year_sigs = [(self.cashFlow['year'][1][i], self.cashFlow['year'][2][i]) for i, year_period in enumerate(year_periods)]

    # Create financial dictionaries one by one
    for i, period in enumerate(report_periods):
      financial = {
        'year': period.replace('-', ''),
        'sharesOutstanding': 1,
        'currency': '',
        'resonance': {},
        'position': {
          'currentAssets': {},
          'currentLiabilities': {},
          'nonCurrentAssets': {},
          'nonCurrentLiabilities': {}
        },
        'cashFlow': {}
      }
      
      # Mark Currency
      sampleUnit = self.resonance['title'][0][1]
      if sampleUnit.endswith('港元'):
        financial['currency'] = '億HKD'
      elif sampleUnit.endswith('美元'):
        financial['currency'] = '億USD'
      elif sampleUnit.endswith('元'):
        financial['currency'] = '億RMB'
      print('Currency unit: {}'.format(financial['currency']))
      
      # Sort Cash Flow
      for j, item in enumerate(self.cashFlow['title']):
        name = item[0]
        originalUnit = item[1]
        mapForCashFlow = {
          '经营流动现金流量净额': 'netOperating',
          '投资活动现金流量净额': 'netInvesting',
          '融资活动现金流量净额': 'netFinancing'
        }
        if name in mapForCashFlow:
          if j == 1 and len(self.year_sigs) != 0 and len([(first, second) for first, second in self.year_sigs if first == self.cashFlow['report'][1][i] and second == self.cashFlow['report'][2][i]]) == 1:
            financial['year'] += 'Y'
          value = self.make_hundred_millions(self.cashFlow['report'][j][i], originalUnit)
          financial['cashFlow'][mapForCashFlow[name]] = value

      # Sort Resonance
      for j, item in enumerate(self.resonance['title']):
        name = item[0]
        originalUnit = item[1]
        mapForResonance = {
          '营业额': 'revenue',
          '销售费用': 'sellingExpense',
          '销售成本': 'salesCost',
          '管理费用': 'adminCost',
          '财务费用': 'financingCost',
          '其它收入': 'otherRevenues',
          '税前利润': 'profitBeforeTax',
          '归属母公司股东利润': 'profit'
        }
        if name in mapForResonance:
          value = self.make_hundred_millions(self.resonance['report'][j][i], originalUnit)
          financial['resonance'][mapForResonance[name]] = value
      
      # Sort Position
      for j, item in enumerate(self.position['title']):
        name = item[0]
        originalUnit = item[1]

        mapForPosition = {
          '资产合计': 'totalAssets',
          '负债合计': 'totalLiabilities'
        }
        if name in mapForPosition:
          value = self.make_hundred_millions(self.position['report'][j][i], originalUnit)
          financial['position'][mapForPosition[name]] = value

        mapForDetailedPosition = {
          '现金及现金等价物': ['currentAssets', 'cash'],
          '应收账款': ['currentAssets', 'receivables'],
          '存货': ['currentAssets', 'inventory'],
          '流动资产合计': ['currentAssets', 'total'],
          '应付账款': ['currentLiabilities', 'payables'],
          '应交税费': ['currentLiabilities', 'tax'],
          '流动负债合计': ['currentLiabilities', 'total'],
          '不动产、厂房和设备': ['nonCurrentAssets', 'propertyPlantEquip'],
          # '非流动资产合计': ['nonCurrentAssets', 'total'],    Handled later
          '非流动负债合计': ['nonCurrentLiabilities', 'total'],
        }
        if name in mapForDetailedPosition:
          value = self.make_hundred_millions(self.position['report'][j][i], originalUnit)
          financial['position'][mapForDetailedPosition[name][0]][mapForDetailedPosition[name][1]] = value

      # nonCurrentAssets
      if financial['position']['totalAssets'] is not None and financial['position']['currentAssets']['total'] is not None:
        financial['position']['nonCurrentAssets']['total'] = round(financial['position']['totalAssets'] - financial['position']['currentAssets']['total'], 6)

      self.report('Data of {} loaded.'.format(financial['year']))
      self.financials.append(financial)

  def sort_shares_outstanding(self):
    for i, financial in enumerate(self.financials):
      for date, equity in self.equityRecords:
        if financial['year'][:8] >= date:
          self.financials[i]['sharesOutstanding'] = equity
          break

  def process(self):
    self.announce('Start scraping resonance, position and cashFlow!', skip=7)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token {}'.format(self.token)
    }

    for symbol, companyName in self.symbols:
      self.announce('{}: Getting resonance, position, cashFlow statements'.format(companyName), wait=(7+randint(0,4)))
      if self.get_all_statements(symbol, retryMax=self.retryMax):
        # Ensure the company has been created.
        self.ensure_company(symbol, companyName)

        # Get equity records
        self.get_equity_records(symbol, retryMax=self.retryMax)

        # Sort self.resonance, self.position and self.cashFlow into self.financials
        self.sort_financials()

        # Sort respective sharesOutstanding
        self.sort_shares_outstanding()

        self.check_existed_financial_years(symbol)

        # Upload self.financials   
        for financial in self.financials:
          data = { 'financial': financial }
          json_string = json.dumps(data)

          # Check if the financial of the year already exists
          existed = financial['year'] in self.existedFinancialYears
          site = '{}{}'.format(self.apiUrl, self.financialAPI(symbol, financial['year'])) if existed else '{}{}'.format(self.apiUrl, self.financialAPI(symbol))
          
          self.report('{}: {} financial {}'.format(companyName, 'Updating' if existed else 'Posting', financial['year']))
          for i in range(self.retryMax):
            try:
              response = self.session.put(site, headers=headers, data=json_string) if existed else self.session.post(site, headers=headers, data=json_string)
              break
            except:
              self.announce('Retrying again', wait=(i*10+randint(0,4)))
              pass
          self.log(response)
        self.announce('Uploads for {} completed.'.format(companyName), skip=3)
      else:
        self.report('Company {}{} is not listed at {}'.format(self.region, symbol, self.site))
        self.announce('Skip', skip=3)
    print('Processing Completed.')
    if len(self.catched) != 0:
      print('\nCatched:')
      for i, symbol in enumerate(self.catched):
        print('{}. {}'.format(i,symbol))

class FinHKEX(FinDataScraper):
  site = 'http://www.hkexnews.hk/sdw/search/searchsdw_c.aspx'
  
  sharesOutstanding = 1
  
  def __init__(self, apiUrl, token, retryMax, symbol, fromSymbol=None):
    super().__init__(apiUrl, token, retryMax, symbol, fromSymbol)
    self.report('Task:\n\tTarget {} from {} for sharesOutstanding.'.format(symbol, self.site))

  def process(self):
    def get_sharesOutstanding(symbol):
      headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
      }
      
      # Retrieve necessary form data
      for i in range(self.retryMax):
        try:
          response = self.session.get(self.site, headers=headers)
          break
        except:
          self.announce('Retrying again', wait=(i*10+randint(0,4)))
          pass

      bs = BeautifulSoup(response.content, 'lxml')

      form_data = {
        '__VIEWSTATE': bs.find('input', { 'name': '__VIEWSTATE' }).get('value'),
        '__VIEWSTATEGENERATOR': bs.find('input', { 'name': '__VIEWSTATEGENERATOR' }).get('value'),
        '__EVENTVALIDATION': bs.find('input', { 'name': '__EVENTVALIDATION' }).get('value'),
        'today': bs.find('input', { 'name': 'today' }).get('value'),
        'ddlShareholdingDay': bs.find('select', { 'name': 'ddlShareholdingDay' }).find('option', { 'selected': 'selected' }).get('value'),
        'ddlShareholdingMonth': bs.find('select', { 'name': 'ddlShareholdingMonth' }).find('option', { 'selected': 'selected' }).get('value'),
        'ddlShareholdingYear': bs.find('select', { 'name': 'ddlShareholdingYear' }).find('option', { 'selected': 'selected' }).get('value'),
        'txtStockCode': symbol,
        'btnSearch.x': 31,
        'btnSearch.y': 7
      }

      for i in range(self.retryMax):
        try:
          response = self.session.post(self.site, data=form_data, headers=headers)
          break
        except:
          self.announce('Retrying again', wait=(i*10+randint(0,4)))
          pass

      self.report('Outstanding shares retrieved.')
      bs = BeautifulSoup(response.content, 'lxml')
      target = bs.find('div', { 'id': 'pnlResultSummary' })
      if target:
        target = target.find_all('tr')[-1].find('span')
        self.sharesOutstanding = int(target.get_text().lstrip().replace(',', ''))
        return True
      else:
        return False
      
    self.announce('Start scraping sharesOutstanding!', skip=7)

    headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Token {}'.format(self.token)
    }

    for symbol, companyName in self.symbols:
      self.check_existed_financial_years(symbol)

      if len(self.existedFinancialYears) > 0:
        self.announce('\n\n{} {}: Getting sharesOutstanding'.format(companyName, symbol), wait=(4+randint(0,4)))
        if get_sharesOutstanding(symbol):
          data = { 'financial': { 'sharesOutstanding': self.sharesOutstanding } }
          json_string = json.dumps(data)

          self.report('Updating sharesOutstanding ({}) at {}'.format(self.sharesOutstanding, self.existedFinancialYears[-1]))
          for i in range(self.retryMax):
            try:
              response = self.session.put('{}{}'.format(self.apiUrl, self.financialAPI(symbol, self.existedFinancialYears[-1])), headers=headers, data=json_string)
              break
            except:
              self.announce('Retrying again', wait=(i*10+randint(0,4)))
              pass
          self.log(response)
        else:
          print('Failed to get the latest sharesOutstanding of {} {}. Skip.'.format(companyName, symbol))
      else:
        print('Basic informations about {} {} do not exist. Skip.'.format(companyName, symbol))
    print('Processing Completed.')

class FinAdapter(FinDataScraper):
  site = 'http://basic.10jqka.com.cn'
  region = 'HK'

  cashFlow = None
  financials = []
  year_sigs = []

  def __init__(self, apiUrl, token, retryMax, symbol, fromSymbol=None):
    super().__init__(apiUrl, token, retryMax, symbol, fromSymbol)
    self.report('Task:\n\tTarget {} from {} for cashFlow.'.format(symbol, self.site))

  def get_all_statements(self, symbol, retryMax):
    site = '{}/{}{}/finance.html'.format(self.site, self.region, symbol[1:])
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    for i in range(self.retryMax):
      try:
        response = self.session.get(site, headers=headers)
        break
      except:
        self.announce('Retrying again', wait=(i*10+randint(0,4)))
        pass

    self.report('Online source retrieved. Now getting into the data...')
    bs = BeautifulSoup(response.content, 'lxml')
    if bs.find(id='cash'):
      self.cashFlow = json.loads(bs.find(id='cash').get_text())
      self.report('現金流量表 retrieved.')
      return True
    else:
      return None

  def sort_financials(self):
    # Get Periods Ready
    self.report('Retrieving periods...')
    report_periods = self.cashFlow['report'][0]
    year_periods = self.cashFlow['year'][0]

    # Get Statements Clear
    self.report('Processing...')
    # Processing 現金流量表
    self.cashFlow['title'] = self.cashFlow['title'][1:]
    self.cashFlow['report'] = self.cashFlow['report'][1:]
    self.cashFlow['year'] = self.cashFlow['year'][1:]

    # Reset financials and year signatures
    self.financials = []
    if year_periods is not None:
      self.year_sigs = [(self.cashFlow['year'][1][i], self.cashFlow['year'][2][i]) for i, year_period in enumerate(year_periods)]

    # Create financial dictionaries one by one
    for i, period in enumerate(report_periods):
      financial = {
        'year': period.replace('-', '')
      }
      # Sort Cash Flow
      for j, item in enumerate(self.cashFlow['title']):
        if j == 1 and len(self.year_sigs) != 0 and len([(first, second) for first, second in self.year_sigs if first == self.cashFlow['report'][1][i] and second == self.cashFlow['report'][2][i]]) == 1:
          financial['year'] += 'Y'

      self.report('Data of {} loaded.'.format(financial['year']))
      self.financials.append(financial)

  def process(self):
    self.announce('Start scraping cashFlow for updating year!', skip=7)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token {}'.format(self.token)
    }

    for symbol, companyName in self.symbols:
      self.announce('{}: Getting cashFlow statement'.format(companyName), wait=(7+randint(0,4)))
      if self.get_all_statements(symbol, retryMax=self.retryMax):
        # Ensure the company has been created.
        self.ensure_company(symbol, companyName)

        # Sort self.cashFlow into self.financials
        self.sort_financials()

        self.check_existed_financial_years(symbol)
        
        # Upload self.financials   
        for financial in self.financials:
          data = { 'financial': financial }
          json_string = json.dumps(data)

          # Check if the financial of the year already exists
          site = '{}{}'.format(self.apiUrl, self.financialAPI(symbol, financial['year'][:8]))
          
          self.report('{}: {} financial {} to {}'.format(companyName, 'Updating', financial['year'][:8], financial['year']))
          for i in range(self.retryMax):
            try:
              response = self.session.put(site, headers=headers, data=json_string)
              break
            except:
              self.announce('Retrying again', wait=(i*10+randint(0,4)))
              pass
          self.log(response)
        self.announce('Uploads for {} {} completed.'.format(companyName, symbol), skip=3)
      else:
        self.report('Company {}{} is not listed at {}'.format(self.region, symbol, self.site))
        self.announce('Skip', skip=3)
    print('Processing Completed.')
