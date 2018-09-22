import time
from random import randint
import json
import requests
from bs4 import BeautifulSoup

def announce(message, wait=0, skip=0):
  print(message, end=' (waiting for {} seconds)'.format(wait) if wait is not 0 else '')
  while wait > 0:
      print('.', end='', flush=True)
      time.sleep(1)
      wait -= 1
  print('\n' * skip if skip is not 0 else '')

def report(message):
  print(message)
  time.sleep(0.2)

class FinDataScraper:
  region = 'HK'
  symbols = []
  site = 'http://basic.10jqka.com.cn'

  resonance = None
  position = None
  cashFlow = None
  financials = []

  def __init__(self, symbol, fromSymbol=None):
    print('\n'*20)
    if symbol == 'ALL':
      announce("REMINDING: You're conducting a COMPLETE financial data search", wait=7, skip=7)
      def retrieve_all_symbols():           # Format: [symbol, companyName]
        report('Retrieving all possible symbols and companyNames from HKEX...\n')
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
        }
        site = 'http://www.hkexnews.hk/listedco/listconews/advancedsearch/stocklist_active_main_c.htm'

        session = requests.session()
        response = session.get(site, headers=headers)
        bs = BeautifulSoup(response.content, 'lxml')
        
        report('Data retrieved. Further processing...\n')
        result = bs.select("[class^=TableContentStyle]")
        result = list(filter(lambda x: x.contents[0].get_text()[0] == '0' and x.contents[0].get_text()[1] in ['0', '1', '2', '3'], result))
        result = list(map(lambda x: [x.contents[0].get_text(), x.contents[1].get_text()], result))
        announce('Data are already formatted in form of [symbol, companyName]', skip=7)
        return result
      self.symbols = retrieve_all_symbols()
      if fromSymbol:
        for i, unit in enumerate(self.symbols):
          if unit[0].endswith(fromSymbol):
            self.symbols = self.symbols[i:]
            print('Starting from {} {}.'.format(unit[1], unit[0]))
            break
    else:
      self.symbols = [symbol if len(symbol) == 5 else '0'*(5-len(symbol))+symbol]
    report('Task:\n\tTarget {} from {}.'.format(symbol, self.site))

  def get_all_statements(self, symbol, retryMax):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    session = requests.session()

    for i in range(retryMax):
      try:
        response = session.get('{}/{}{}/finance.html'.format(self.site, self.region, symbol), headers=headers)
        break
      except:
        announce('Retrying again', wait=(i*10+randint(0,4)))
        pass

    report('Online source retrieved. Now getting into the data...')
    bs = BeautifulSoup(response.content, 'lxml')
    if bs.find(id='benefit'):
      self.resonance = json.loads(bs.find(id='benefit').get_text())
      report('利潤表 retrieved.')
      self.position = json.loads(bs.find(id='debt').get_text())
      report('資產負債表 retrieved.')
      self.cashFlow = json.loads(bs.find(id='cash').get_text())
      report('現金流量表 retrieved.')
      return True
    else:
      return None

  def sort_financials(self):
    # Helper Functions
    def make_hundred_millions(value, originalUnit):
      if value is not '':
        value = float(value)
        if originalUnit.startswith('万'):
          value = value * 10000
        value = value / 100000000
        return value
      else:
        return None
    
    # Reset financials
    self.financials = []
    
    # Get Periods Ready
    report('Retrieving periods...')
    periods = self.resonance["report"][0]

    # Get Statements Clear
    report('Processing all statements...')
    # Processing 利潤表
    self.resonance['title'] = self.resonance['title'][1:]
    self.resonance['report'] = self.resonance['report'][1:]

    # Processing 資產負債表
    self.position['title'] = self.position['title'][1:]
    self.position['report'] = self.position['report'][1:]
    
    # Processing 現金流量表
    self.cashFlow['title'] = self.cashFlow['title'][1:]
    self.cashFlow['report'] = self.cashFlow['report'][1:]

    # Create financial dictionaries one by one
    for i, period in enumerate(periods):
      financial = {
        'year': period.replace('-', ''),
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
          value = make_hundred_millions(self.resonance['report'][j][i], originalUnit)
          financial['resonance'][mapForResonance[name]] = value
      
      # Sort Position
      for j, item in enumerate(self.position['title']):
        name = item[0]
        originalUnit = item[1]
        mapForPosition = {
          '现金及现金等价物': ['currentAssets', 'cash'],
          '应收账款': ['currentAssets', 'receivables'],
          '存货': ['currentAssets', 'inventory'],
          '流动资产合计': ['currentAssets', 'total'],
          '应付账款': ['currentLiabilities', 'payables'],
          '应交税费': ['currentLiabilities', 'tax'],
          '流动负债合计': ['currentLiabilities', 'total'],
          '不动产、厂房和设备': ['nonCurrentAssets', 'propertyPlantEquip'],
          '资产合计': ['nonCurrentAssets', 'total'],    # minus 流动资产合计 (currentAssets)
          '非流动负债合计': ['nonCurrentLiabilities', 'total'],
        }
        if name in mapForPosition:
          value = make_hundred_millions(self.position['report'][j][i], originalUnit)
          financial['position'][mapForPosition[name][0]][mapForPosition[name][1]] = value
      
      if financial['position']['nonCurrentAssets']['total'] is not None and financial['position']['currentAssets']['total'] is not None:
        financial['position']['nonCurrentAssets']['total'] = round(financial['position']['nonCurrentAssets']['total'] - financial['position']['currentAssets']['total'], 6)

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
          value = make_hundred_millions(self.cashFlow['report'][j][i], originalUnit)
          financial['cashFlow'][mapForCashFlow[name]] = value

      report('Data of {} loaded.'.format(financial['year']))
      self.financials.append(financial)

  def process(self, apiUrl, token, retryMax):
    def log(response):
      bs = BeautifulSoup(response.content, 'lxml')
      json_string = bs.get_text()
      data = json.loads(json_string) if '{' in json_string and '}' in json_string else None
      if data:
        if 'errors' in data:
          print('Response: {}'.format(data['errors']))
        else:
          print('Success.')
        return data
      else:
        print('Error: {}'.format(json_string))
        return json_string
      
    
    announce('Start!', skip=7)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token {}'.format(token)
    }
    session = requests.session()

    for symbol, companyName in self.symbols:
      apis = {
        'company': {
          'get': '/companies/{}'.format(symbol.lstrip('0')),
          'post': '/companies'
        },
        'financial': '/companies/{}/financials'.format(symbol.lstrip('0'))
      }

      # Check if the company is listed in the source site
      announce('{}: Getting resonance, position, cashFlow statements'.format(companyName), wait=(7+randint(0,4)))
      if self.get_all_statements(symbol[1:], retryMax):
        # Ensure the company has been created.
        for i in range(retryMax):
          try:
            company = session.get('{}{}'.format(apiUrl, apis['company']['get']), headers=headers)
            break
          except:
            announce('Retrying again', wait=(i*10+randint(0,4)))
            pass
        
        if log(company) == 'Unauthorized':
          announce('Creating company {} {}...'.format(companyName, symbol), wait=3)
          data = {
              'company': {
                  'symbol': symbol.lstrip('0'),
                  'name': companyName
              }
          }
          json_company = json.dumps(data)
          response = session.post('{}{}'.format(apiUrl, apis['company']['post']), headers=headers, data=json_company)
          log(response)
          report('Company created.')
        else:
          report('Company existed.')

        # Sort self.resonance, self.position and self.cashFlow into self.financials
        self.sort_financials()

        # Check the original recorded financials
        for i in range(retryMax):
          try:
            response = session.get('{}{}'.format(apiUrl, apis['financial']), headers=headers)
            break
          except:
            announce('Retrying again', wait=(i*10+randint(0,4)))
            pass
        originalFinancials = log(response)['financials']
        originalFinancials = list(map(lambda financial: financial['year'], originalFinancials))

        # Upload self.financials   
        for financial in self.financials:
          data = { 'financial': financial }
          json_string = json.dumps(data)

          # Check if the financial of the year already exists
          existed = financial['year'] in originalFinancials
          report('{}: {} financial {}'.format(companyName, 'Updating' if existed else 'Posting', financial['year']))
          if existed:
            for i in range(retryMax):
              try:
                response = session.put('{}{}/{}'.format(apiUrl, apis['financial'], financial['year']), headers=headers, data=json_string)
                break
              except:
                announce('Retrying again', wait=(i*10+randint(0,4)))
                pass
          else:
            for i in range(retryMax):
              try:
                response = session.post('{}{}'.format(apiUrl, apis['financial']), headers=headers, data=json_string)
                break
              except:
                announce('Retrying again', wait=(i*10+randint(0,4)))
                pass
          log(response)
        announce('Uploads for {} completed.'.format(companyName), skip=3)
      else:
        report('Company {}{} is not listed at {}'.format(self.region, symbol, self.site))
        announce('Skip', skip=3)
    print('Processing Completed.')
