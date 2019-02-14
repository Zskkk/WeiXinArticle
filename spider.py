import requests
from urllib.parse import urlencode
from requests.exceptions import ConnectionError
from pyquery import PyQuery as pq
import pymongo

client = pymongo.MongoClient('localhost')
db = client['weixin']
KEYWORD = '旅行'
PROXY_POOL_URL = 'http://127.0.0.1:5555/random'
proxy = None
base_url = 'https://weixin.sogou.com/weixin?'
headers = {
    'Cookie': 'CXID=CFE8F2EAD36CE75ADB248455599A1DF3; SUID=0751150E3965860A5B90FD120001B4C8; SUV=003F8E76DF68418C5BC6102D765B2549; weixinIndexVisited=1; wuid=AAGADT6OJQAAAAqLK0Z+fgIA+QQ=; ad=PFlNtZllll2t2za1lllllVe6ajwlllllWGBGzyllll9lllllRv7ll5@@@@@@@@@@; IPLOC=CN4405; ABTEST=6|1550157455|v1; SNUID=31D6CB562F2BAFF306571B072F6C8909; JSESSIONID=aaaqhxVVyDpiZcKADO7Hw; sct=5; ppinf=5|1550158284|1551367884|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZTozNjolRTUlODUlQUMlRTglQkYlODclRTYlQjAlQjQlRTglOUElOEF8Y3J0OjEwOjE1NTAxNTgyODR8cmVmbmljazozNjolRTUlODUlQUMlRTglQkYlODclRTYlQjAlQjQlRTglOUElOEF8dXNlcmlkOjQ0Om85dDJsdU9qZHlxcVZpcVNONEtfaHJUbzk3cHNAd2VpeGluLnNvaHUuY29tfA; pprdig=lX2JgpbdMc7smKHwI3kC09eO2EfZCorMTyfxKinHYlyygU75GIBB0UsIff0ksIAv7Cw0EdxyE6HHODAqaeiXh0mNqd3otQxlv1BzOGHr0DIiOoGAw2EQCoFcRwvFbqLPIRAgIE8ru9TVjLxLzygDo22xF8KP__wpqoITqaZ54Jw; sgid=11-37985427-AVxliaczVvEHZCjjwSrFialhQ; ppmdig=1550158285000000fc43a5152d731f273028fe8819170cab',
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36'
}

def get_proxy():
    """
    得到一个随机代理
    :return:
    """
    try:
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def get_html(url):
    """
    返回页面
    :param url:
    :return:
    """
    global proxy
    try:
        # 先判断请求是否需要代理，调用Session的send()方法执行请求
        if proxy:
            proxies = {
                'http': 'http://' + proxy
            }
            response = requests.get(url, allow_redirects=False, headers=headers, proxies=proxies)
        else:
            # 请求调用prepare()方法转化为Prepared Request,不重定向，请求超时时间，响应返回
            response = requests.get(url, allow_redirects=False, headers=headers)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            print('302')
            proxy = get_proxy()
            if proxy:
                print('Useing Proxy', proxy)
                return get_html(url)
            else:
                print('Get Proxy Failed')
                return None
    except ConnectionError:
        proxy = get_proxy()
        return get_html(url)

def get_index(KEYWORD, page):
    """
    构建页码url
    :param KEYWORD:
    :param page:
    :return:
    """
    data = {
        'query': KEYWORD,
        '_sug_type_': '',
        'sut': '11216',
        'lkt': '0, 0, 0',
        's_from': 'input',
        '_sug_': 'y',
        'type': 2,
        'sst0': '1550158000370',
        'page': page,
        'ie': 'utf8',
        'w': '01019900',
        'dr': '1'
    }
    queries = urlencode(data)
    url = base_url + queries
    html = get_html(url)
    return html

def parse_index(html):
    """
    解析索引页
    :param response: 响应
    :return: 新的响应
    """
    doc = pq(html)
    # 获取本页所有的微信文章链接
    items = doc('.news-box .news-list li .txt-box h3 a').items()
    # 构造成WeixinRequest之后yield返回
    for item in items:
        yield item.attr('href')

def get_detail(url):
    """
    返回微信文章的源码
    :param url:
    :return:
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def parse_detail(html):
    """
    解析微信文章
    :param html:
    :return:
    """
    doc = pq(html)
    # 提取标题、正文文本、发布日期、发布人昵称、公众号名称,组合成字典返回
    title = doc('.rich_media_title').text()
    content = doc('.rich_media_content').text()
    date = doc('#publish_time').text()
    nickname = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
    wechat = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
    return {
        'title': title,
        'content': content,
        'date': date,
        'nickname': nickname,
        'wechat': wechat
    }

def main():
    """
    主函数
    :return:
    """
    for page in range(1, 101):
        html = get_index(KEYWORD, page)
        if html:
            article_urls = parse_index(html)
            for article_url in article_urls:
                #print(article_url)
                article_html = get_detail(article_url)
                if article_html:
                    article_data = parse_detail(article_html)
                    print(article_data)
                    save_to_mongo(article_data)

def save_to_mongo(data):
    """
    保存到MongoDB
    :param data:
    :return:
    """
    if db['article_data'].update({'title': data['title']}, {'$set': data}, True):
        print('Saved to Mongo', data['title'])
    else:
        print('Save to Mongo Failed', data['title'])

if __name__ == '__main__':
    main()
