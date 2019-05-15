from sys import argv
import time
import requests
from bs4 import BeautifulSoup
from random import randint
import json

session = requests.session()

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-TW;q=0.7,zh;q=0.6,zh-CN;q=0.5'
}

RETRYMAX = 7

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

def stock_code(symbol):         # return a 5-letter-long symbol
    return symbol if len(symbol) == 5 else '0'*(5-len(symbol))+symbol

def allSymbols():

    report('Retrieving all possible symbols and companyNames from HKEX...\n')

    site = 'http://www3.hkexnews.hk/listedco/listconews/advancedsearch/stocklist_active_main_c.htm'

    for i in range(RETRYMAX):
        try:
            response = session.get(site, headers=HEADERS)
            break
        except:
            announce('Retrying again', wait=(i*10+randint(0,4)))
            pass

    bs = BeautifulSoup(response.content, 'lxml')

    report('Data retrieved. Further processing...\n')

    allSymbolResults = bs.select("[class^=TableContentStyle]")

    result = list(filter(lambda x: x.contents[0].get_text()[0] == '0' and x.contents[0].get_text()[1] in ['0', '1', '2', '3', '6', '8'], allSymbolResults))

    result = list(map(lambda x: [x.contents[0].get_text()[1:], x.contents[1].get_text()], result))

    announce('Data are already formatted in form of [symbol, companyName]', skip=7)

    return result

def checkDividends(symbol):
    site = 'http://basic.10jqka.com.cn/HK{}/bonus.html'.format(symbol)
    for i in range(RETRYMAX):
        try:
            response = session.get(site, headers=HEADERS)
            break
        except:
            announce('Retrying again', wait=(i*10+randint(0,4)))
            pass

    bs = BeautifulSoup(response.content, 'lxml')
    
    report('Data retrieved. Further processing {}...\n'.format(symbol))
    numberOfTimesOfContinuousDividends = 0
    isFirst = True
    lastYear = 0
    captured = False

    rows = [row for row in bs.select('tbody tr') if len(row) >= 15]
    for row in rows:
        columns = row.contents
        year = int(columns[1].get_text()[:4])

        if isFirst:
            lastYear = year
            isFirst = False
        
        difference = lastYear - year
        if difference == 1:
            captured = False

        if not captured:
            if difference == 2:
                break
            dividend = columns[3].get_text()      # '不分红'
            execution = columns[15].get_text()    # '实施终止'
            if dividend != '不分红' and execution != '实施终止':
                lastYear = year
                numberOfTimesOfContinuousDividends = numberOfTimesOfContinuousDividends + 1
                captured = True
        
        if not captured and difference > 1:
            break

    return numberOfTimesOfContinuousDividends

def save(dictionary):
    with open('file.txt', 'w') as file:
        file.write(json.dumps(dictionary))

if __name__ == '__main__':
    # fromSymbol = stock_code(argv[1]) if len(argv) > 1 else 1
# ****************

    # Format: {companyName: Number of times of continuous dividends}
    continuousRecords = {}
    
    try:
        for (symbol, companyName) in allSymbols():
            announce('Checking {} {}...'.format(companyName, symbol), wait=randint(0,2))
            continuousRecords['{} {}'.format(companyName, symbol)] = checkDividends(symbol)
    except:
        save(continuousRecords)

    save(continuousRecords)
    
    # Testing
    # print(checkDividends('0001'))
