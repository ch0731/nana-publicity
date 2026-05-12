import requests
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from publish import load_env, get_access_token

load_env()
cfg = load_env()
token = get_access_token(cfg["WECHAT_APP_ID"], cfg["WECHAT_APP_SECRET"])

# 两篇待删除草稿
drafts = [
    "VCCbU0xfJxY74QV4M0kwEFU7D6rPRLNgnD_J7ecAHyBTrlQPcYvO_dQW9j_cIvVI",  # 草稿A - 17张文案
    "VCCbU0xfJxY74QV4M0kwEHcXNHwUh67Ucm_2FaZBfjQSJG1Uhj-Kxakaq9-EkH95",  # 草稿B - 16张文案
]

for media_id in drafts:
    url = f"https://api.weixin.qq.com/cgi-bin/draft/delete"
    resp = requests.post(url, params={"access_token": token}, json={"media_id": media_id})
    result = resp.json()
    if result.get("errcode") == 0:
        print(f"[OK] 已删除: {media_id[:40]}...")
    else:
        print(f"[FAIL] 删除失败 {media_id[:40]}...: {result}")
