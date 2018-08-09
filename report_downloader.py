import requests
from bs4 import BeautifulSoup

def retrieve_urls(symbol):
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

    for pdf in bs.find_all('a', { 'class': 'news' }):
        pdfs.append('http://www.hkexnews.hk' + pdf.get('href'))
        print("PDF retrieved.")

    nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
    while nextBtn is not None:
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
            pdfs.append('http://www.hkexnews.hk' + pdf.get('href'))
        nextBtn = bs.find('input', { 'name': 'ctl00$btnNext' })
    
    return pdfs

pdfs = retrieve_urls('00813')
for (i, pdf) in enumerate(pdfs):
    print('PDF {}: {}'.format(i, pdf))
