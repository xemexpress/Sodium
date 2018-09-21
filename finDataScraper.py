import json
import requests
from bs4 import BeautifulSoup

class FinDataScraper:
  mode = {}
  region = 'HK'
  symbol = ''
  site = ''

  resonance = None
  position = None
  cashFlow = None
  financials = []

  def __init__(self, symbol, verbose=False):
    self.mode['verbose'] = verbose
    self.symbol = symbol if len(symbol) == 4 else '0'*(4-len(symbol))+symbol
    self.site = 'http://basic.10jqka.com.cn/{}{}/finance.html'.format(self.region, self.symbol)
    print('Symbol: {}'.format(self.symbol))
    print('Site: {}'.format(self.site))
  
  def get_all_statements(self):
    print('Setting headers...')
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
    }

    print('Retrieving the site...')
    session = requests.session()
    response = session.get(self.site, headers=headers)

    print('Retrieving the data...')
    bs = BeautifulSoup(response.content, 'lxml')
    self.resonance = json.loads(bs.find(id='benefit').get_text())
    print('利潤表 retrieved.')
    self.position = json.loads(bs.find(id='debt').get_text())
    print('資產負債表 retrieved.')
    self.cashFlow = json.loads(bs.find(id='cash').get_text())
    print('現金流量表 retrieved.')

  def sort_financials(self, verbose=False):
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
    
    # Get Periods Ready
    print('self.resonance is alright.')
    periods = self.resonance["report"][0]
    print('Periods retrieved.')

    # Get Statements Clear
    print('Processing 利潤表...')
    self.resonance['title'] = self.resonance['title'][1:]
    self.resonance['report'] = self.resonance['report'][1:]

    print('Processing 資產負債表...')
    self.position['title'] = self.position['title'][1:]
    self.position['report'] = self.position['report'][1:]
    
    print('Processing 現金流量表...')
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
      print('Learning currency...')
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
          print(name)
          financial['cashFlow'][mapForCashFlow[name]] = value

      if self.mode['verbose']:
        print(financial)
      self.financials.append(financial)

  def upload(self, apiUrl, token, mode):
    print('Starting posting financials to Company {}{}...'.format(self.region, self.symbol))

    print('Setting headers...')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Token {}'.format(token)
    }

    session = requests.session()

    api = '/companies/{}/financials'.format(self.symbol.lstrip('0'))

    for financial in self.financials:
      data = {'financial': financial }
      json_string = json.dumps(data)

      if self.mode['verbose']:
        print('{} financial {} of Company {}'.format(('Posting' if mode == 'post' else '') + ('Updating' if mode == 'update' else ''), financial['year'], self.symbol))
      
      if mode == 'post':  
        response = session.post('{}{}'.format(apiUrl, api), headers=headers, data=json_string)
      elif mode == 'update':
        response = session.put('{}{}/{}'.format(apiUrl, api, financial['year']), headers=headers, data=json_string)
      bs = BeautifulSoup(response.content, 'lxml')

      json_string = bs.get_text()
      data = json.loads(json_string) if '{' in json_string and '}' in json_string else None
      if data:
        if 'errors' in data:
          print('Response {} of Company {}: '.format(financial['year'][:4], self.symbol), data['errors'])
        elif self.mode['verbose']:
          print('Response: ', data)
      else:
        print('Error: {}'.format(json_string))
    
    print('Uploads complete.')
