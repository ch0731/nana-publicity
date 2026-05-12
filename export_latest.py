#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""导出最新草稿内容"""
import json, requests
from pathlib import Path

# 加载配置
env = {}
with open(Path(__file__).parent / '.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()

# 获取token
resp = requests.get(
    'https://api.weixin.qq.com/cgi-bin/token',
    params={'grant_type': 'client_credential', 'appid': env['WECHAT_APP_ID'], 'secret': env['WECHAT_APP_SECRET']}
)
token = resp.json()['access_token']

# 获取草稿
resp = requests.post(
    'https://api.weixin.qq.com/cgi-bin/draft/batchget',
    params={'access_token': token},
    json={'type': 7, 'offset': 0, 'count': 5}
)
items = resp.json().get('item', [])

if items:
    # 取第一个草稿（最新的）
    item = items[0]
    news_item = item.get('content', {}).get('news_item', [{}])[0]
    content = news_item.get('content', '')
    
    # 保存为HTML
    out_path = Path(__file__).parent / 'preview_purple.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'[OK] 已导出: {out_path}')
    print(f'[INFO] 内容长度: {len(content)} 字符')
else:
    print('[ERROR] 没有找到草稿')
