# -*- coding: utf-8 -*-
import json, requests

config = {}
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            config[k] = v

resp = requests.get('https://api.weixin.qq.com/cgi-bin/token', 
    params={'grant_type': 'client_credential', 'appid': config['WECHAT_APP_ID'], 'secret': config['WECHAT_APP_SECRET']})
token = resp.json()['access_token']

# 获取最新文章
resp = requests.post('https://api.weixin.qq.com/cgi-bin/freepublish/batchget',
    params={'access_token': token},
    json={'offset': 0, 'count': 1})
data = resp.json()
news = data['item'][0]['content']['news_item'][0]

print('URL:', news.get('url'))
