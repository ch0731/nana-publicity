#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NANA公众号自动发布工具

用法:
  # 默认只建草稿，不直接发布
  python publish.py --title "标题" --images pic1.jpg pic2.jpg
  
  # AI自动生成每张图片的文案（推荐）
  python publish.py --title "标题" --images pic1.jpg pic2.jpg --auto-texts
  
  # 手动指定每张图片的文案
  python publish.py --title "标题" --images pic1.jpg pic2.jpg --texts "文案1" "文案2"
  
  # ⚠️ 强制直发（绕过草稿确认）
  python publish.py --title "标题" --images pic.jpg --force-publish

模板选择:
  star-purple-brutal  - 紫金大字报（默认）
  art-elegant         - 暗黑优雅艺术风
  art-watercolor      - 水彩清新风
  neon-luxury         - 暗夜奢华
  golden-noir         - 暖调象牙白
  cyberpunk-neon      - 赛博朋克霓虹
  vintage-paper       - 复古纸质感
  midnight-silver     - 午夜深蓝+银白
  rose-gold           - 玫瑰金渐变
  brutalist-white     - 粗野主义白底
"""

import argparse
import base64
import json
import os
import random
import sys
import requests
from datetime import datetime
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"
TOKEN_CACHE_PATH = Path(__file__).parent / ".token_cache.json"
OPENROUTER_KEY_FILE = Path(__file__).parent / ".openrouter_key"
TEMPLATE_USAGE_PATH = Path(__file__).parent / "template_usage.json"

# 全部20套配色模板
ALL_TEMPLATES = [
    "star-purple-brutal", "star-purple-dynamic", "art-deco-gold-dynamic",
    "aurora-borealis-dynamic", "brutalist-white-dynamic", "cherry-blossom-dynamic",
    "cyberpunk-neon-dynamic", "deep-ocean-dynamic", "ethereal-mist-dynamic",
    "golden-noir-dynamic", "holographic-dynamic", "industrial-steel-dynamic",
    "lofi-sunset-dynamic", "midnight-silver-dynamic", "neon-luxury-dynamic",
    "noir-cinema-dynamic", "retro-arcade-dynamic", "rose-gold-dynamic",
    "vintage-paper-dynamic", "zen-garden-dynamic",
]

# 风格族→模板映射（角色映射到族，族内递减随机）
STYLE_FAMILIES = {
    "purple-holographic": ["star-purple-dynamic", "star-purple-brutal", "holographic-dynamic"],
    "dark-noir": ["noir-cinema-dynamic", "golden-noir-dynamic", "neon-luxury-dynamic", "midnight-silver-dynamic"],
    "pink-romantic": ["rose-gold-dynamic", "cherry-blossom-dynamic"],
    "blue-ocean": ["deep-ocean-dynamic", "aurora-borealis-dynamic"],
    "green-mist": ["ethereal-mist-dynamic", "zen-garden-dynamic"],
    "gold-vintage": ["art-deco-gold-dynamic", "vintage-paper-dynamic"],
    "bold-cyber": ["brutalist-white-dynamic", "cyberpunk-neon-dynamic", "retro-arcade-dynamic", "industrial-steel-dynamic"],
    "warm-sunset": ["lofi-sunset-dynamic"],
}

# 角色→风格族映射
CHARACTER_STYLE_FAMILY = {
    "井河阿莎姬": "dark-noir",
    "対魔忍": "dark-noir",
    "阿莎姬": "dark-noir",
    "秋山凛子": "dark-noir",
    "仪玄": "dark-noir",
    "红袖": "dark-noir",
    "水城不知火": "dark-noir",
    "英格丽德": "dark-noir",
    "木星": "green-mist",
    "苍角": "green-mist",
    "水城雪风": "green-mist",
    "水城ゆきかぜ": "green-mist",
    "金星": "pink-romantic",
    "乱菊": "pink-romantic",
    "星野樱": "pink-romantic",
    "小兔": "pink-romantic",
    "小喵": "pink-romantic",
    "火野丽": "pink-romantic",
    "卯之花烈": "pink-romantic",
    "金美婷": "pink-romantic",
    "妮可": "pink-romantic",
    "露琪亚": "blue-ocean",
    "海王满": "blue-ocean",
    "小小兔": "blue-ocean",
    "月城柳": "blue-ocean",
    "伊芙琳": "blue-ocean",
    "黑猫娜": "purple-holographic",
    "阿丽亚": "purple-holographic",
    "比利": "purple-holographic",
    "八津紫": "purple-holographic",
    "安比": "dark-noir",  # midnight-silver 归入 dark-noir 族
    "女帝": "purple-holographic",
    "波雅·汉库克": "purple-holographic",
}


def _load_template_usage():
    """读取模板使用计数器，返回 {模板名: 次数}"""
    if TEMPLATE_USAGE_PATH.exists():
        try:
            data = json.loads(TEMPLATE_USAGE_PATH.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {t: 0 for t in ALL_TEMPLATES}


def _save_template_usage(data):
    """保存模板使用计数器"""
    TEMPLATE_USAGE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_template(template_pool):
    """从模板池中按递减随机策略选一个，记录使用次数"""
    usage = _load_template_usage()
    # 仅考虑候选池中有使用记录的模板
    candidates = [t for t in template_pool if t in usage]
    if not candidates:
        candidates = template_pool
    # 找使用次数最少的
    min_count = min(usage.get(t, 0) for t in candidates)
    least_used = [t for t in candidates if usage.get(t, 0) == min_count]
    # 从最少的里面随机抽
    chosen = random.choice(least_used)
    usage[chosen] = usage.get(chosen, 0) + 1
    # 检查是否全部20个都至少用过一次 → 全部减1，归零最低
    all_used_all = all(usage.get(t, 0) >= 1 for t in ALL_TEMPLATES)
    if all_used_all:
        min_all = min(usage.get(t, 0) for t in ALL_TEMPLATES)
        for t in ALL_TEMPLATES:
            usage[t] = usage.get(t, 0) - min_all
    _save_template_usage(usage)
    return chosen

_RANDOM_TITLES = [
    "NANA壁纸 | {char} | 绝美画风，错过可惜",
    "NANA壁纸 | {char} | 这画质能处一辈子",
    "NANA壁纸 | {char} | 细节满分，审美在线",
    "NANA壁纸 | {char} | 每张都能当头像",
    "NANA壁纸 | {char} | 漫画级画质，收藏不亏",
    "NANA壁纸 | {char} | 氛围感拉满，赞到失语",
    "NANA壁纸 | {char} | 美到不想眨眼",
    "NANA壁纸 | {char} | 壁纸首选，零差评",
    "NANA壁纸 | {char} | 视觉盛宴，速存系列",
    "NANA壁纸 | {char} | 原图输出，张张能打",
]

_RANDOM_DESCS = [
    "绝美画风，错过可惜",
    "这画质能处一辈子",
    "细节满分，审美在线",
    "每张都能当头像",
    "漫画级画质，收藏不亏",
    "氛围感拉满，赞到失语",
    "美到不想眨眼",
    "壁纸首选，零差评",
    "视觉盛宴，速存系列",
    "原图输出，张张能打",
    "高清无水印，速存不解释",
    "长按保存，评论区见",
    "同款壁纸，等你来拿",
]

def _random_title(char="二次元"):
    tpl = random.choice(_RANDOM_TITLES)
    return tpl.replace("{char}", char)

def _random_desc():
    return random.choice(_RANDOM_DESCS)

def _generate_ai_title(images_dir, character, template_name):
    """
    用 Sensenova API 分析图片内容，生成自媒体引流风格标题。
    """
    import base64, os

    sensenova_key = os.environ.get("SENSENOVA_API_KEY", "").strip()
    if not sensenova_key or sensenova_key == "sk-":
        return None

    # 取2张图分析（随机）
    all_imgs = [f for f in os.listdir(images_dir) if f.lower().endswith(('.png','.jpg','.jpeg'))]
    if not all_imgs:
        return None

    sample_imgs = random.sample(all_imgs, min(2, len(all_imgs)))
    img_paths = [os.path.join(images_dir, img) for img in sample_imgs]

    prompt = (
        "你是一个资深自媒体运营专家。请根据以下图片内容，生成3个适合二次元壁纸公众号的爆款标题。"
        "要求：1. 标题要有悬念感或情绪张力，能引发点击 2. 不能包含任何人物名字或角色名 3. 每行一个标题，不要编号，不要其他说明"
        "示例风格：\n"
        "• 美哭了...这画风我能吹一辈子\n"
        "• 终于找到这套了！高清无水印直接抱走\n"
        "• 这质量别说壁纸，拿来当头像都奢侈\n"
        "• 第一眼就破防了，画师太懂了吧\n"
        "• 氛围感拉满，零差评的宝藏图\n"
    )

    for img_path in img_paths:
        try:
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            url = "https://token.sensenova.cn/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {sensenova_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "sensenova-6.7-flash-lite",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                        ]
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.8,
                "reasoning_effort": "none",
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()

            if "error" in data:
                continue

            result = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if result and len(result) > 5:
                title = result.split('\n')[0].strip()
                # 去除项目符号
                title = title.lstrip('•-* ').strip()
                if len(title) > 5 and len(title) < 40:
                    print(f"  [AI标题] {title}")
                    return title
        except Exception:
            pass
    return None


def load_openrouter_key():
    """加载 OpenRouter API Key"""
    if OPENROUTER_KEY_FILE.exists():
        return OPENROUTER_KEY_FILE.read_text().strip()
    return os.environ.get("OPENROUTER_API_KEY", "")


def load_env():
    config = {}
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    config[key] = value
                    os.environ[key] = value
    return config


def get_access_token(app_id, app_secret):
    if TOKEN_CACHE_PATH.exists():
        with open(TOKEN_CACHE_PATH, "r") as f:
            cache = json.load(f)
            if cache.get("expires_at", 0) > datetime.now().timestamp():
                print("[OK] 使用缓存的access_token")
                return cache["access_token"]

    print("[...] 正在获取access_token...")
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": app_id, "secret": app_secret}
    resp = requests.get(url, params=params)
    data = json.loads(resp.content.decode("utf-8"))

    if "access_token" not in data:
        print(f"[ERROR] 获取token失败: {data}")
        sys.exit(1)

    token = data["access_token"]
    expires_in = data.get("expires_at", 7200) - 300
    cache = {"access_token": token, "expires_at": datetime.now().timestamp() + expires_in}
    with open(TOKEN_CACHE_PATH, "w") as f:
        json.dump(cache, f)
    print("[OK] access_token获取成功")
    return token


# ─────────────────────────────────────────────
# v3 新增：角色→模板对照表
CHARACTER_TEMPLATE_MAP = {
    # 绿色系
    "木星": "ethereal-mist-dynamic",
    # 粉色/金色系
    "金星": "rose-gold-dynamic",
    "乱菊": "rose-gold-dynamic",
    "星野樱": "rose-gold-dynamic",
    "小兔": "rose-gold-dynamic",
    "小喵": "rose-gold-dynamic",
    "火野丽": "rose-gold-dynamic",
    "卯之花烈": "rose-gold-dynamic",
    "花烈": "rose-gold-dynamic",
    # 蓝色系
    "露琪亚": "deep-ocean-dynamic",
    "海王满": "deep-ocean-dynamic",
    "小小兔": "deep-ocean-dynamic",
    # 紫色系
    "黑猫娜": "star-purple-dynamic",
    "阿丽亚": "star-purple-dynamic",
    # 韩漫角色（粉色优雅风）
    "金美婷": "rose-gold-dynamic",
    # 默认
}

DEFAULT_TEMPLATE = "star-purple-dynamic"

def analyze_with_image_tool(image_path):
    """
    调用 Sensenova API 分析图片
    返回分析文本，失败返回 None
    """
    import base64, os, time

    sensenova_key = os.environ.get("SENSENOVA_API_KEY", "").strip()
    if not sensenova_key or sensenova_key == "sk-":
        return None

    try:
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

    prompt = "详细描述这张图片的内容：角色、服装、动作、表情、场景、氛围等"

    url = "https://token.sensenova.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {sensenova_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sensenova-6.7-flash-lite",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                ]
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.3,
        "reasoning_effort": "none",
    }

    for attempt in range(2):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()

            if "error" in data:
                if attempt == 0:
                    time.sleep(3)
                    continue
                return None

            text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if text and len(text) > 3:
                return text

            if attempt == 0:
                time.sleep(3)
        except Exception:
            if attempt == 0:
                time.sleep(3)
    return None


# ─────────────────────────────────────────────
# 文案兜底库：AI 分析失败时随机轮换，避免千篇一律
_FALLBACK_CAPTIONS = [
    ["星河入梦，光影交织", "每一帧都是壁纸级享受", "长按保存，原图直出"],
    ["次元裂缝已开启", "绝美画风直击心灵", "评论区蹲一个同好"],
    ["光影魔术师上线", "细节控的终极盛宴", "无水印高清，速存"],
    ["穿越次元的邂逅", "每一眼都是心动信号", "原图在评论区等你"],
    ["壁纸界的艺术品", "色彩与线条的共舞", "长按识别，即刻收藏"],
    ["梦幻场景再现", "视觉系玩家的福利", "高清原图，评论区见"],
    ["打破次元壁的瞬间", "美到窒息的画面感", "速存！手慢无"],
    ["光影诗篇，帧帧封神", "二次元美学天花板", "原图直出，评论区蹲"],
    ["一眼沦陷的视觉冲击", "每一像素都是精致", "保存即可设为壁纸"],
    ["次元美学的极致表达", "画风精致到令人窒息", "高清无水印，速存"],
]


def generate_caption_from_analysis(analysis_text):
    """根据 image 工具的分析文本生成诗意文案，失败则随机兜底"""
    if not analysis_text or len(str(analysis_text)) < 3:
        return "<br>".join(random.choice(_FALLBACK_CAPTIONS))

    text = str(analysis_text).lower()
    lines = []
    # 颜色关键词匹配
    color_lines = {
        ("绿色", "green"): ["翠绿环绕，生机盎然", "自然之力，治愈心灵", "清新一夏，绿意满心"],
        ("金色", "gold", "黄色", "yellow"): ["金色流光，璀璨如星", "暖阳倾泻，温柔满溢", "黄金时代，梦幻降临"],
        ("粉色", "pink", "桃色", "peach"): ["粉色梦境，甜到心坎", "樱花飘落，浪漫满屏", "少女心爆棚的配色"],
        ("蓝色", "blue", "冰", "ice", "海", "sea"): ["冰蓝幻境，冷艳高贵", "深海秘境，静谧悠远", "蔚蓝之心，清澈见底"],
        ("紫色", "purple", "紫罗兰", "violet"): ["紫罗兰花语，神秘优雅", "薰衣草田，浪漫无边", "暗夜紫魅，高贵冷艳"],
        ("红色", "red", "绯红", "crimson"): ["烈焰红唇，热情似火", "血色浪漫，惊艳时光", "红妆倾城，一眼万年"],
        ("黑色", "black", "暗黑", "dark"): ["暗夜女王，气场全开", "黑金奢华，低调高级", "墨色倾城，神秘莫测"],
        ("白色", "white", "雪白", "snow"): ["纯白无瑕，天使降临", "冰雪奇缘，纯净之美", "白月光般的存在"],
    }
    for keywords, candidate_lines in color_lines.items():
        if any(k in text for k in keywords):
            lines = candidate_lines
            break

    if not lines:
        lines = random.choice(_FALLBACK_CAPTIONS)

    result = "<br>".join(lines[:3])
    if not result or len(result) < 5 or "Error" in result or "WARN" in result or "失败" in result:
        return "<br>".join(random.choice(_FALLBACK_CAPTIONS))
    return result


def _compress_for_ai(image_path):
    """为AI分析压缩图片：超过1280px则缩放到1280px。返回临时文件路径。"""
    try:
        tmp_path, _ = compress_image(image_path, max_size_mb=10, quality=85, max_width=1280)
        return tmp_path
    except Exception:
        return image_path  # 失败则用原图


def ai_analyze_and_caption(image_path):
    """
    v4 主文案生成：Sensenova API + 规则兜底
    """
    # 方案1：Sensenova API
    try:
        caption = ai_generate_caption(image_path)
        if caption and len(caption) > 5 and "Error" not in caption[:50] and "WARN" not in caption[:50]:
            print(f"  [OK] Sensenova生成文案: {caption[:40]}...")
            return caption
        elif caption:
            print(f"  [WARN] Sensenova内容无效: {caption[:50]}")
    except Exception as e:
        print(f"  [WARN] Sensenova失败: {e}")

    # 方案2：直接 analyze（旁路分析，不走文案生成）
    try:
        analysis = analyze_with_image_tool(image_path)
        if analysis and len(analysis) > 3:
            caption = generate_caption_from_analysis(analysis)
            if caption and len(caption) > 5:
                print(f"  [OK] Sensenova分析: {caption[:30]}...")
                return caption
    except Exception as e:
        print(f"  [WARN] Sensenova分析失败: {e}")

    # 方案3：规则兜底
    print(f"  [INFO] 规则兜底生成文案")
    return "<br>".join(["二次元壁纸盛宴", "高清美图欣赏", "无水印直存，评论区见"])


# ─────────────────────────────────────────────
# v3 新增：自动压缩（>10MB）
WECHAT_MAX_MB = 10  # 微信图片素材限制10MB


def compress_image(image_path, max_size_mb=4.5, quality=85, max_width=2560, return_bytes=False):
    """
    统一图片压缩函数。
    - return_bytes=False: 保存到文件，返回 (path, was_compressed)
    - return_bytes=True:  返回内存 bytes
    """
    size_mb = os.path.getsize(image_path) / 1024 / 1024
    if size_mb <= WECHAT_MAX_MB and not return_bytes:
        return image_path, False

    try:
        from PIL import Image
        import io
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)

        if return_bytes:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            cur_mb = len(buffer.getvalue()) / 1024 / 1024
            if cur_mb > max_size_mb:
                for q in [70, 60, 50]:
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=q, optimize=True)
                    cur_mb = len(buffer.getvalue()) / 1024 / 1024
                    if cur_mb <= max_size_mb:
                        break
            print(f"  [压缩] {os.path.basename(image_path)}: {size_mb:.1f}MB -> {cur_mb:.1f}MB")
            return buffer.getvalue()

        # 文件模式：保存到 .compressed.jpg，逐步降质量直到 < max_size_mb
        out_path = image_path + ".compressed.jpg"
        for q in [95, 90, 85, 80, 75, 70, 60, 50]:
            img.save(out_path, 'JPEG', quality=q)
            if os.path.getsize(out_path) < max_size_mb * 1024 * 1024:
                break
        new_mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"  [压缩] {os.path.basename(image_path)}: {size_mb:.1f}MB -> {new_mb:.1f}MB")
        return out_path, True

    except Exception as e:
        print(f"  [WARN] 压缩失败: {e}")
        if return_bytes:
            with open(image_path, 'rb') as f:
                return f.read()
        return image_path, False


def ai_generate_caption(image_path):
    """使用 Sensenova API 生成文案，重试3次"""
    import base64, os, time

    # 加载 Sensenova API Key
    sensenova_key = os.environ.get("SENSENOVA_API_KEY", "").strip()
    if not sensenova_key or sensenova_key == "sk-":
        print("  [WARN] SENSENOVA_API_KEY 未配置，跳过 Sensenova")
        return None

    # 读取图片并 base64 编码
    try:
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"  [WARN] 读取图片失败: {e}")
        return None

    prompt = (
        "你是一位专业的二次元壁纸公众号文案编辑。请仔细观察这张图片，"
        "根据图片的实际内容（角色、服装、动作、表情、场景、氛围等）生成一段3行左右的诗意文案。"
        "要求：1. 必须根据图片实际内容来写，不能泛泛而谈 2. 每行15-20字左右，共3行 3. 用<br>分隔每行 4. 直接返回文案，不要任何其他内容"
    )

    url = "https://token.sensenova.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {sensenova_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sensenova-6.7-flash-lite",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                ]
            }
        ],
        "max_tokens": 500,
        "temperature": 0.7,
        "reasoning_effort": "none",
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()

            if "error" in data:
                print(f"  [WARN] Sensenova API 错误 (attempt {attempt+1}/3): {data['error']}")
                if attempt < 2:
                    time.sleep(5)
                    continue
                return None

            caption = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if not caption or len(caption) < 5:
                print(f"  [WARN] Sensenova 返回内容过短 (attempt {attempt+1}/3)")
                if attempt < 2:
                    time.sleep(5)
                    continue
                return None

            # 清理前缀
            caption = caption.replace("好的，", "").replace("这是一段", "").replace("以下是的描述：", "")
            caption = caption.replace("以下是图片的描述：", "").replace("根据图片内容，", "").replace("图片展示的是", "")
            caption = caption.strip()

            if len(caption) > 5:
                print(f'  [OK] Sensenova生成文案: {caption[:40]}...')
                return caption

            if attempt < 2:
                time.sleep(5)
        except Exception as e:
            print(f'  [WARN] Sensenova API 调用失败 (attempt {attempt+1}/3): {e}')
            if attempt < 2:
                time.sleep(5)
    return None



def detect_dominant_color(image_path):
    """
    分析图片主色调，返回颜色关键词列表
    支持: purple/gold/pink/white/black/red/blue/green/warm/cool/default
    """
    try:
        from PIL import Image
        img = Image.open(image_path)
        img = img.convert("RGB")
        # 动漫图：主体在画面中央，裁剪中心 60% 区域，避免背景干扰
        w, h = img.size
        left, top = int(w * 0.2), int(h * 0.2)
        right, bottom = int(w * 0.8), int(h * 0.8)
        img = img.crop((left, top, right, bottom))
        # 缩小到100x100加快分析
        img = img.resize((100, 100), Image.Resampling.LANCZOS)
        pixels = list(img.getdata())
        r_sum = sum(p[0] for p in pixels)
        g_sum = sum(p[1] for p in pixels)
        b_sum = sum(p[2] for p in pixels)
        n = len(pixels)
        r_avg, g_avg, b_avg = r_sum // n, g_sum // n, b_sum // n
        # 判断色调
        brightness = (r_avg + g_avg + b_avg) / 3
        saturation = max(r_avg, g_avg, b_avg) - min(r_avg, g_avg, b_avg)
        # 判断主色通道（互斥，避免一图多标签）
        r_dominance = r_avg - max(g_avg, b_avg)
        g_dominance = g_avg - max(r_avg, b_avg)
        b_dominance = b_avg - max(r_avg, g_avg)
        max_dominance = max(r_dominance, g_dominance, b_dominance)
        colors = []
        # 主色必须明显占优（差值>25）才算有主色
        if max_dominance > 25:
            if g_dominance == max_dominance and g_avg > 110:
                colors.append("green")
            elif r_dominance == max_dominance and r_avg > 150 and g_avg < 100:
                colors.append("red")
            elif r_dominance == max_dominance and r_avg > 180 and b_avg > 100:
                colors.append("pink")
            elif b_dominance == max_dominance and b_avg > 150 and r_avg < 100:
                colors.append("blue")
            elif r_dominance == max_dominance and g_avg > 100:
                colors.append("gold")
            else:
                colors.append("purple")
        elif brightness > 200 and saturation < 40:
            colors.append("white")
        elif brightness < 70 and saturation > 40:
            colors.append("black")
        elif brightness > 170 and saturation < 80:
            colors.append("warm")
        elif brightness < 150 and saturation > 50:
            colors.append("cool")
        return colors if colors else ["default"]
    except Exception:
        return ["default"]


def match_template_by_color(image_paths):
    """
    根据多张图片的主色调投票，选出最合适的模板
    返回模板名称
    """
    from collections import Counter
    color_votes = []
    for path in image_paths:
        colors = detect_dominant_color(path)
        color_votes.extend(colors)
    dominant = Counter(color_votes).most_common(1)[0][0]
    # 颜色 -> 模板映射
    mapping = {
        "purple": ["star-purple-dynamic", "star-purple-brutal"],
        "gold": ["golden-noir-dynamic", "art-deco-gold-dynamic"],
        "pink": ["cherry-blossom-dynamic", "rose-gold-dynamic"],
        "white": ["brutalist-white-dynamic", "cherry-blossom-dynamic"],
        "black": ["noir-cinema-dynamic", "midnight-silver-dynamic"],
        "red": ["neon-luxury-dynamic", "cyberpunk-neon-dynamic"],
        "blue": ["deep-ocean-dynamic", "midnight-silver-dynamic"],
        "green": ["ethereal-mist-dynamic", "aurora-borealis-dynamic"],
        "warm": ["golden-noir-dynamic", "lofi-sunset-dynamic"],
        "cool": ["deep-ocean-dynamic", "midnight-silver-dynamic"],
        "default": ["star-purple-dynamic", "noir-cinema-dynamic"],
    }
    candidates = mapping.get(dominant, mapping["default"])
    return candidates[0]


def upload_images_concurrent(token, image_paths, max_workers=5):
    """并发上传多张图片，加快速度"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = [None] * len(image_paths)
    def worker(idx, path):
        result = upload_image(token, path)
        return idx, result
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, i, p): i for i, p in enumerate(image_paths)}
        for future in as_completed(futures):
            idx, url = future.result()
            results[idx] = url
    return results


def upload_image(token, image_path):
    # v3: 图片>10MB时压缩到9MB以下再上传（WeChat限制）。上传后清理临时压缩文件。
    upload_path = image_path
    temp_compressed = None

    upload_path, was_compressed = compress_image(image_path, max_size_mb=WECHAT_MAX_MB)
    if was_compressed:
        temp_compressed = upload_path

    url = "https://api.weixin.qq.com/cgi-bin/material/add_material"
    if upload_path.startswith("http"):
        resp = requests.get(upload_path)
        if resp.status_code != 200:
            return None
        img_data = resp.content
        files = {"media": ("image.jpg", img_data, "image/jpeg")}
    else:
        if not os.path.exists(upload_path):
            return None
        file_size = os.path.getsize(upload_path) / 1024 / 1024
        print(f"[...] 上传图片: {os.path.basename(upload_path)} ({file_size:.1f}MB)")
        files = {"media": open(upload_path, "rb")}

    params = {"type": "image", "access_token": token}
    resp = requests.post(url, params=params, files=files)
    data = json.loads(resp.content.decode("utf-8"))

    # 上传后清理临时压缩文件
    if temp_compressed and os.path.exists(temp_compressed):
        try:
            os.remove(temp_compressed)
            print(f"  [清理] 删除临时压缩文件")
        except Exception:
            pass

    if "media_id" in data:
        print(f"[OK] 图片上传成功: {data['media_id']}")
        return {"media_id": data["media_id"], "url": data.get("url", "")}
    else:
        print(f"[ERROR] 上传失败: {data}")
        return None


def generate_image_section(uploaded_images, texts=None, style="elegant"):
    styles = {
        "elegant": {"bg": "#050505", "accent": "#ffe4b5", "text": "#ffffff", "text_sub": "#f0e8d8", "num_color": "#D4AF37", "border": "#ffe4b5", "glow": "rgba(255,228,181,0.35)"},
        "watercolor": {"bg": "#faf8f5", "accent": "#b8956f", "text": "#1a1510", "text_sub": "#3a3530", "num_color": "rgba(180,140,100,0.5)", "border": "#b8956f", "glow": "rgba(180,140,100,0.2)"},
        "purple": {"bg": "#1A0E30", "accent": "#D4AF37", "text": "#F0E6FF", "text_sub": "#C9B8E8", "num_color": "#6B3FA0", "border": "#D4AF37", "glow": "#6B3FA0"},
        "luxury": {"bg": "#0A0612", "accent": "#D4AF37", "text": "#F5F0FF", "text_sub": "#B8A8D0", "num_color": "#3D2A5C", "border": "#2A1F3D", "glow": "#1F1530"},
        "golden": {"bg": "#FAF8F5", "accent": "#B87333", "text": "#1A1612", "text_sub": "#8A7E6E", "num_color": "#C4A882", "border": "#E8E0D5", "glow": "#E8E0D5"},
        "cyberpunk": {"bg": "#0A0A0F", "accent": "#FF00FF", "text": "#FFFFFF", "text_sub": "#8888AA", "num_color": "#00FFFF", "border": "#FF00FF", "glow": "#00FFFF"},
        "vintage": {"bg": "#F5F0E8", "accent": "#8B7355", "text": "#2C2416", "text_sub": "#6B5D4D", "num_color": "#C4A882", "border": "#C4A882", "glow": "#D5CCC0"},
        "midnight": {"bg": "#0D1B2A", "accent": "#C0C0FF", "text": "#FFFFFF", "text_sub": "#8FA8C0", "num_color": "#7B8FA1", "border": "#C0C0FF", "glow": "#1B2838"},
        "rose": {"bg": "#FFF5F7", "accent": "#FF6B8A", "text": "#5C3D4F", "text_sub": "#8B7080", "num_color": "#FF6B8A", "border": "#FFB7C5", "glow": "#FFD5DD"},
        "brutalist": {"bg": "#FFFFFF", "accent": "#FF3333", "text": "#000000", "text_sub": "#333333", "num_color": "#FF3333", "border": "#000000", "glow": "#000000"},
        "purple-brutal": {"bg": "#1A0E30", "accent": "#D4AF37", "text": "#F0E6FF", "text_sub": "#C9B8E8", "num_color": "#D4AF37", "border": "#D4AF37", "glow": "#6B3FA0"},        "cherry": {"bg": "#FFF5F7", "accent": "#FF6B8A", "text": "#5C3D4F", "text_sub": "#8B7080", "num_color": "#FF6B8A", "border": "#FFB7C5", "glow": "#FFD5DD"},
        "aurora": {"bg": "#0B0C10", "accent": "#00D9FF", "text": "#FFFFFF", "text_sub": "#8B949E", "num_color": "#00D9FF", "border": "#7B2FBE", "glow": "#1a1a2e"},
        "deep-ocean": {"bg": "#0A1628", "accent": "#4ECDC4", "text": "#F7FFF7", "text_sub": "#8B9DAF", "num_color": "#4ECDC4", "border": "#1A535C", "glow": "#0D2137"},
        "ethereal": {"bg": "#F8F5FF", "accent": "#9B8AC4", "text": "#4A4063", "text_sub": "#7B68AE", "num_color": "#9B8AC4", "border": "#C5B3FF", "glow": "#EDE8FF"},
        "lofi": {"bg": "#0D1117", "accent": "#FF6B6B", "text": "#F0F6FC", "text_sub": "#8B949E", "num_color": "#FF6B6B", "border": "#161B22", "glow": "#1a1a2e"},
        "noir": {"bg": "#0F0F0F", "accent": "#8B7355", "text": "#E8E8E8", "text_sub": "#6B6B6B", "num_color": "#8B7355", "border": "#4A4A4A", "glow": "#2A2A2A"},
        "retro": {"bg": "#0D0221", "accent": "#00FF41", "text": "#E8E8FF", "text_sub": "#8B8BFF", "num_color": "#00FF41", "border": "#FF00FF", "glow": "#1A0533"},
        "holo": {"bg": "#000000", "accent": "#00FFFF", "text": "#FFFFFF", "text_sub": "#888888", "num_color": "#FF0080", "border": "#00FFFF", "glow": "#080808"},
        "steel": {"bg": "#1A1A1A", "accent": "#6B6B6D", "text": "#E8E8E8", "text_sub": "#8B8B8D", "num_color": "#FF6B35", "border": "#3D3D3D", "glow": "#3D3D3D"},
        "zen": {"bg": "#F5F0E8", "accent": "#8B7355", "text": "#2D2D2D", "text_sub": "#6B6B6B", "num_color": "#8B0000", "border": "#D4C4A8", "glow": "#EDE6D6"},
        "art-deco": {"bg": "#0A0A0A", "accent": "#C9A961", "text": "#E8D5A3", "text_sub": "#8B8B8B", "num_color": "#C9A961", "border": "#6B6B6B", "glow": "#111111"},
    }
    s = styles.get(style, styles["elegant"])

    decorations = ["✿", "❀", "✾", "❁", "❃"]
    image_html = ""

    for i, img_info in enumerate(uploaded_images):
        url = img_info["url"]
        if "wx_fmt=" not in url:
            url = url.rstrip("/") + "/0?wx_fmt=jpeg"

        # 没有文案的图片不显示任何文字
        if texts and i < len(texts) and texts[i] and texts[i].strip():
            reason = texts[i].replace("\n", "<br>")
        else:
            reason = ""

        num = f"{i+1:02d}"
        deco = decorations[i % len(decorations)]
        side = "left" if i % 2 == 0 else "right"

        # 各风格独立布局
        if style == "golden":
            section = f'''
<section style="background:#FAF8F5;padding:20px 30px 0;text-align:center;">
  <img src="{url}" style="display:block;width:100%;border:none;" />
</section>
<section style="background:#FAF8F5;padding:35px 55px 55px;text-align:center;">
  <div style="width:40px;height:2px;background-color:{s['accent']};margin:0 auto 25px;"></div>
  <p style="font-size:16px;color:{s['text']};line-height:2.4;letter-spacing:1px;margin:0;">{reason}</p>
  <p style="font-size:48px;font-weight:200;color:{s['num_color']};letter-spacing:12px;margin:30px 0 0 0;">{num}</p>
</section>
'''
        elif style == "cyberpunk":
            section = f'''
<section style="background:#0A0A0F;padding:15px 20px 0;">
  <img src="{url}" style="display:block;width:100%;border:1px solid #FF00FF;box-shadow:0 0 20px rgba(255,0,255,0.4);" />
</section>
<section style="background:#0A0A0F;padding:30px 45px 50px;text-align:center;">
  <div style="width:60px;height:2px;background:linear-gradient(90deg,#FF00FF,#00FFFF);margin:0 auto 22px;box-shadow:0 0 8px #FF00FF;"></div>
  <p style="font-size:15px;color:{s['text']};line-height:2.2;letter-spacing:1px;margin:0;">{reason}</p>
  <p style="font-size:50px;font-weight:900;color:{s['num_color']};letter-spacing:6px;margin:25px 0 0 0;text-shadow:0 0 15px {s['num_color']};">{num}</p>
</section>
'''
        elif style == "vintage":
            section = f'''
<section style="background:#F5F0E8;padding:20px 35px 0;text-align:center;">
  <img src="{url}" style="display:block;width:100%;border:none;filter:sepia(0.1);" />
</section>
<section style="background:#F5F0E8;padding:30px 55px 50px;text-align:center;">
  <p style="font-size:13px;color:{s['accent']};margin:0 0 20px 0;font-style:italic;">✦ ✦ ✦</p>
  <p style="font-size:15px;color:{s['text']};line-height:2.2;letter-spacing:1px;margin:0;font-style:italic;">{reason}</p>
  <p style="font-size:44px;font-weight:400;color:{s['num_color']};letter-spacing:10px;margin:25px 0 0 0;font-style:italic;">{num}</p>
</section>
'''
        elif style == "midnight":
            section = f'''
<section style="background:#0D1B2A;padding:18px 22px 0;text-align:center;">
  <img src="{url}" style="display:block;width:100%;border:none;box-shadow:0 0 30px rgba(192,192,255,0.15);" />
</section>
<section style="background:#0D1B2A;padding:30px 50px 50px;text-align:center;">
  <div style="width:40px;height:1px;background:#C0C0FF;margin:0 auto 22px;box-shadow:0 0 6px #C0C0FF;"></div>
  <p style="font-size:15px;color:{s['text']};line-height:2.2;letter-spacing:1px;margin:0;">{reason}</p>
  <p style="font-size:46px;font-weight:100;color:{s['num_color']};letter-spacing:10px;margin:25px 0 0 0;">{num}</p>
</section>
'''
        elif style == "rose":
            section = f'''
<section style="background:transparent;padding:18px 25px 0;text-align:center;">
  <img src="{url}" style="display:block;width:100%;border-radius:12px;box-shadow:0 30px 70px rgba(200,100,120,0.5),0 0 0 2px #FFB7C5,0 0 70px rgba(255,183,197,0.5);" />
</section>
<section style="background:transparent;padding:30px 50px 50px;text-align:center;">
  <div style="width:30px;height:2px;background:#FFB7C5;margin:0 auto 20px;box-shadow:0 0 8px #FFB7C5;"></div>
  <p style="font-size:15px;color:{s['text']};line-height:2.2;letter-spacing:1px;margin:0;text-shadow:0 2px 8px rgba(255,107,138,0.3);">{reason}</p>
  <p style="font-size:44px;font-weight:300;color:{s['num_color']};letter-spacing:10px;margin:25px 0 0 0;text-shadow:0 0 20px rgba(255,107,138,0.7),0 0 40px rgba(255,107,138,0.4),0 3px 8px rgba(0,0,0,0.3);">{num}</p>
</section>
'''
        elif style == "brutalist":
            section = f'''
<section style="background:#000000;padding:0;">
  <img src="{url}" style="display:block;width:100%;border:none;" />
</section>
<section style="background:#FFFFFF;padding:30px 35px 45px;">
  <div style="width:100%;height:4px;background:#000000;margin:0 0 22px;"></div>
  <p style="font-size:15px;color:{s['text']};line-height:2;font-weight:700;margin:0;">{reason}</p>
  <p style="font-size:56px;font-weight:900;color:{s['num_color']};letter-spacing:-2px;margin:22px 0 0 0;">{num}</p>
</section>
'''
        elif style == "purple-brutal":
            section = f'''<section style="background:#1A0E30;padding:0">
<img src="{url}" style="display:block;width:100%;border:none" />
</section>
<section style="background:#1A0E30;padding:28px 35px 40px">
<div style="width:100%;height:4px;background:#D4AF37;margin:0 0 20px"></div>
<p style="font-size:16px;color:#F0E6FF;line-height:1.8;font-weight:700;margin:0">{reason}</p>
<p style="font-size:56px;font-weight:900;color:#D4AF37;letter-spacing:-2px;margin:20px 0 0 0">{num}</p>
</section>
'''
        elif style == "luxury":
            section = f'''
<section style="background:{s['bg']};padding:10px 20px 0;text-align:center;">
  <img src="{url}" style="display:block;width:100%;border-radius:4px;border:1px solid {s['border']};" />
</section>
<section style="background:{s['bg']};padding:35px 50px 55px;text-align:center;">
  <table align="center" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto 25px auto;">
    <tr>
      <td style="width:40px;height:1px;background-color:{s['border']};"></td>
      <td style="width:10px;text-align:center;font-size:8px;color:{s['accent']};">◆</td>
      <td style="width:40px;height:1px;background-color:{s['border']};"></td>
    </tr>
  </table>
  <p style="font-size:15px;color:{s['text']};line-height:2.4;letter-spacing:1.5px;margin:0;">{reason}</p>
  <p style="font-size:48px;font-weight:100;color:{s['num_color']};letter-spacing:8px;margin:25px 0 0 0;">{num}</p>
</section>
'''
        else:
            section = f'''
<section style="background:{s['bg']};padding:0 25px;position:relative;overflow:hidden;">
  <div style="position:absolute;top:20px;{side}:25px;font-size:55px;color:{s['num_color']};pointer-events:none;text-shadow:0 0 25px {s['glow']};">{deco}</div>
  <img src="{url}" style="display:block;width:100%;border-radius:12px;box-shadow:0 30px 70px rgba(0,0,0,0.8),0 0 0 2px {s['glow']},0 0 70px {s['glow']};" />
  <div style="text-align:right;padding:18px 12px 0;">
    <span style="font-size:54px;font-weight:200;color:{s['accent']};line-height:1;letter-spacing:4px;text-shadow:0 0 30px {s['glow']};">{num}</span>
  </div>
</section>
<section style="background:{s['bg']};padding:50px 60px 65px;position:relative;">
  <div style="position:absolute;left:60px;top:35px;width:3px;height:calc(100% - 70px);background:linear-gradient(180deg,{s['accent']},transparent);box-shadow:0 0 15px {s['glow']};"></div>
  <div style="padding-left:35px;">
    <p style="font-size:17px;color:{s['text']};line-height:2.8;letter-spacing:2px;margin:0;text-shadow:0 2px 12px rgba(0,0,0,0.9);">{reason}</p>
  </div>
</section>
'''
        image_html += section
    return image_html


def create_article(token, title, desc, uploaded_images, texts=None, template_name="star-purple-brutal"):
    thumb_media_id = uploaded_images[0]["media_id"] if uploaded_images else None

    # 模板名 -> (CSS风格, HTML模板文件名)
    # 支持短名和完整动态名，通过统一推导减少重复条目
    _STYLE_ALIASES = {
        "art-watercolor": "art-elegant", "art-elegant": "art-elegant",
        "star-purple": "star-purple", "star-purple-dynamic": "star-purple",
        "neon-luxury": "neon-luxury", "neon-luxury-dynamic": "neon-luxury",
        "golden-noir": "golden-noir", "golden-noir-dynamic": "golden-noir",
        "cyberpunk-neon": "cyberpunk-neon", "cyberpunk-neon-dynamic": "cyberpunk-neon",
        "vintage-paper": "vintage-paper", "vintage-paper-dynamic": "vintage-paper",
        "midnight-silver": "midnight-silver", "midnight-silver-dynamic": "midnight-silver",
        "rose-gold": "rose-gold", "cherry-blossom": "rose-gold",
        "rose-gold-dynamic": "rose-gold", "cherry-blossom-dynamic": "rose-gold",
        "brutalist-white": "brutalist-white", "brutalist-white-dynamic": "brutalist-white",
        "star-purple-brutal": "star-purple-brutal", "star-purple-brutal-dynamic": "star-purple-brutal",
        "art-deco-gold": "art-deco-gold", "art-deco-gold-dynamic": "art-deco-gold",
        "aurora-borealis": "aurora-borealis", "aurora-borealis-dynamic": "aurora-borealis",
        "deep-ocean": "deep-ocean", "deep-ocean-dynamic": "deep-ocean",
        "ethereal-mist": "ethereal-mist", "ethereal-mist-dynamic": "ethereal-mist",
        "lofi-sunset": "lofi-sunset", "lofi-sunset-dynamic": "lofi-sunset",
        "noir-cinema": "noir-cinema", "noir-cinema-dynamic": "noir-cinema",
        "retro-arcade": "retro-arcade", "retro-arcade-dynamic": "retro-arcade",
        "holographic": "holographic", "holographic-dynamic": "holographic",
        "industrial-steel": "industrial-steel", "industrial-steel-dynamic": "industrial-steel",
        "zen-garden": "zen-garden", "zen-garden-dynamic": "zen-garden",
    }
    _STYLE_TO_CSS = {
        "art-elegant": "watercolor", "star-purple": "purple", "neon-luxury": "luxury",
        "golden-noir": "golden", "cyberpunk-neon": "cyberpunk", "vintage-paper": "vintage",
        "midnight-silver": "midnight", "rose-gold": "rose", "brutalist-white": "brutalist",
        "star-purple-brutal": "purple-brutal", "art-deco-gold": "art-deco",
        "aurora-borealis": "aurora", "deep-ocean": "deep-ocean", "ethereal-mist": "ethereal",
        "lofi-sunset": "lofi", "noir-cinema": "noir", "retro-arcade": "retro",
        "holographic": "holo", "industrial-steel": "steel", "zen-garden": "zen",
    }
    base_name = _STYLE_ALIASES.get(template_name, template_name)
    style = _STYLE_TO_CSS.get(base_name, "purple-brutal")
    template_base = f"{base_name}-dynamic"

    template_path = os.path.join(os.path.dirname(__file__), "templates", f"{template_base}.html")
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(__file__), "templates", f"{template_name}.html")

    with open(template_path, "r", encoding="utf-8", errors="replace") as f:
        template = f.read()

    image_section = generate_image_section(uploaded_images, texts, style)
    description = desc.replace("\n", "<br>") if desc and len(desc) > 5 else "NANA二次元壁纸合集"

    content = template.replace("{{TITLE}}", title)
    content = content.replace("{{DESCRIPTION}}", description)
    content = content.replace("{{IMAGE_SECTION}}", image_section)
    content = content.replace("绝世女帝", title)

    article = {
        "title": title,
        "thumb_media_id": thumb_media_id,
        "author": "NANA",
        "digest": desc,
        "content": content,
        "need_open_comment": 1,
        "only_fans_can_comment": 0
    }

    draft_url = "https://api.weixin.qq.com/cgi-bin/draft/add"
    params = {"access_token": token}
    payload = {"articles": [article]}
    data_str = json.dumps(payload, ensure_ascii=False)
    content_len = len(data_str.encode('utf-8'))
    print(f"[DEBUG] Draft payload size: {content_len:,} bytes")
    if content_len > 20000:
        print(f"[WARN] Content is large ({content_len/1024:.0f}KB), WeChat may reject")
    resp = requests.post(draft_url, params=params, data=data_str.encode('utf-8'), headers={'Content-Type': 'application/json; charset=utf-8'}, timeout=30)
    print(f"[DEBUG] Response status: {resp.status_code}")
    print(f"[DEBUG] Response length: {len(resp.content)} bytes")
    raw = resp.content
    if len(raw) == 0:
        print(f"[ERROR] 微信API返回空响应, 状态码={resp.status_code}")
        print(f"[DEBUG] 标题: {title}")
        print(f"[DEBUG] content长度: {len(content)} 字符")
        print(f"[DEBUG] 图片数: {len(uploaded_images)}")
        print(f"[DEBUG] 文案数: {len(texts) if texts else 0}")
        return None
    data = json.loads(raw.decode("utf-8"))

    if "media_id" in data:
        print(f"[OK] 草稿创建成功: media_id={data['media_id']}")
        return data["media_id"]
    else:
        print(f"[ERROR] 创建草稿失败: {data}")
        return None


def publish_article(token, media_id):
    url = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"
    params = {"access_token": token}
    payload = {"media_id": media_id}
    resp = requests.post(url, params=params, json=payload)
    data = json.loads(resp.content.decode("utf-8"))
    if data.get("errcode", 0) == 0:
        print(f"[OK] 发布成功! publish_id={data.get('publish_id', 'N/A')}")
        return True
    else:
        print(f"[ERROR] 发布失败: {data}")
        return False


def main():
    import random

    parser = argparse.ArgumentParser(description="NANA公众号自动发布工具")
    # v3 新增：folder + character 组合（全自动入口）
    parser.add_argument("--folder", help="图片文件夹路径（自动扫描所有图片）")
    parser.add_argument("--character", help="角色名（如：木星、乱菊、海王满），用于自动选模板")
    parser.add_argument("--title", help="文章标题（不填则自动生成）")
    parser.add_argument("--desc", default="NANA二次元壁纸", help="文章摘要")
    # 兼容旧版：images 仍然支持
    parser.add_argument("--images", nargs="+", help="壁纸图片路径")
    parser.add_argument("--texts", nargs="*", default=None, help="每张图片文案（不填则AI自动生成，选5-6张）")
    parser.add_argument("--force-publish", action="store_true", help="⚠️ 强制直发（默认只建草稿）")
    parser.add_argument("--skip-ai", action="store_true", help="跳过AI文案生成，快速创建草稿")
    parser.add_argument("--random-template", action="store_true", help="强制纯随机模板（忽略角色映射）")
    parser.add_argument("--template", default=None,
                        choices=[
                            "art-elegant", "art-watercolor", "star-purple", "star-purple-brutal",
                            "neon-luxury", "golden-noir", "cyberpunk-neon", "vintage-paper",
                            "midnight-silver", "rose-gold", "brutalist-white",
                            "art-deco-gold-dynamic", "aurora-borealis-dynamic", "brutalist-white-dynamic",
                            "cherry-blossom-dynamic", "cyberpunk-neon-dynamic", "deep-ocean-dynamic",
                            "ethereal-mist-dynamic", "golden-noir-dynamic", "holographic-dynamic",
                            "industrial-steel-dynamic", "lofi-sunset-dynamic", "midnight-silver-dynamic",
                            "neon-luxury-dynamic", "noir-cinema-dynamic", "retro-arcade-dynamic",
                            "rose-gold-dynamic", "star-purple-dynamic", "vintage-paper-dynamic",
                            "zen-garden-dynamic",
                            "art-deco-gold", "aurora-borealis", "cherry-blossom", "deep-ocean",
                            "ethereal-mist", "holographic", "industrial-steel", "lofi-sunset",
                            "noir-cinema", "retro-arcade", "zen-garden",
                        ])
    args = parser.parse_args()

    # ── v3: folder + character 全自动入口 ──
    if args.folder:
        if not os.path.isdir(args.folder):
            print(f"[ERROR] 文件夹不存在: {args.folder}")
            sys.exit(1)
        supported = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
        all_images = [os.path.join(args.folder, f) for f in os.listdir(args.folder)
                      if f.lower().endswith(supported) and ".compressed" not in f.lower()]
        if not all_images:
            print(f"[ERROR] 文件夹内没有找到图片: {args.folder}")
            sys.exit(1)
        # 如果没有指定具体图片，才用全量扫描
        if not args.images:
            args.images = all_images
            print(f"[INFO] 扫描文件夹: {len(all_images)} 张图片")
        else:
            print(f"[INFO] 使用指定的 {len(args.images)} 张图片（跳过文件夹扫描）")

        # ── 自动选择模板：角色映射优先 + 随机兜底 ──
        if args.template is None:
            # --random-template 强制纯随机，跳过角色映射
            if args.random_template:
                args.template = _pick_template(ALL_TEMPLATES)
                print(f"[配色] 纯随机模板: {args.template}")
            else:
                # 角色→风格族映射（族内递减随机）
                if args.character and args.character in CHARACTER_STYLE_FAMILY:
                    family_name = CHARACTER_STYLE_FAMILY[args.character]
                    family_pool = STYLE_FAMILIES[family_name]
                    args.template = _pick_template(family_pool)
                    print(f"[配色] 角色映射: {args.character} → {family_name} → {args.template}")
                else:
                    args.template = _pick_template(ALL_TEMPLATES)
                    print(f"[配色] 随机选择模板: {args.template}")

        # 自动生成标题
        if not args.title:
            if args.character:
                # 先尝试AI分析图片内容生成标题
                ai_title = None
                if args.folder:
                    ai_title = _generate_ai_title(args.folder, args.character, args.template)
                if ai_title:
                    args.title = f"NANA壁纸 | {args.character} | {ai_title}"
                else:
                    # 回退到随机模板描述
                    desc_map = {
                        "ethereal-mist": "翠绿电力，治愈系",
                        "rose-gold": "玫瑰金粉，优雅奢华",
                        "deep-ocean": "深海之蓝，高贵冷艳",
                        "star-purple": "紫金星光，神秘优雅",
                        "star-purple-brutal": "紫金大字报，视觉冲击",
                        "cherry-blossom": "樱花粉调，甜美清新",
                        "noir-cinema": "电影质感，格调满分",
                        "neon-luxury": "霓虹奢风，赛博朋克",
                        "neon-luxury-dynamic": "霓虹流光，炫彩之夜",
                        "cyberpunk-neon": "赛博霓虹，酷炫炸场",
                        "midnight-silver": "午夜深蓝，银白流光",
                        "midnight-silver-dynamic": "银白午夜，冷艳杀疯了",
                        "golden-noir": "暖调象牙，精致复古",
                        "golden-noir-dynamic": "金棕映画，优雅满分",
                        "art-deco-gold-dynamic": "艺术 Deco，奢华滤镜",
                        "lofi-sunset-dynamic": "落日氛围，慵懒复古",
                        "vintage-paper-dynamic": "复古纸艺，文艺质感",
                        "industrial-steel-dynamic": "工业钢感，冷峻高级",
                        "aurora-borealis-dynamic": "极光流转，梦幻空灵",
                        "ethereal-mist-dynamic": "迷雾仙子，空灵绝美",
                        "holographic-dynamic": "全息彩虹，炫彩未来",
                        "brutalist-white-dynamic": "极简纯白，高级留白",
                        "zen-garden-dynamic": "禅意庭院，静谧东方",
                        "retro-arcade-dynamic": "像素复古，游戏情怀",
                    }
                    auto_desc = desc_map.get(args.template, _random_desc())
                    args.title = f"NANA壁纸 | {args.character} | {auto_desc}"
            else:
                args.title = _random_title()
        print(f"[INFO] 标题: {args.title}")

    elif args.images:
        # 旧版模式：手动指定图片
        if args.template is None:
            print(f"[配色] 未指定模板，自动分析图片配色...")
            args.template = match_template_by_color(args.images[:5])
            print(f"[配色] 检测结果: {args.template}")
        if not args.title:
            args.title = "NANA壁纸 | 二次元壁纸盛宴 | 无水印直存"
    else:
        print("[ERROR] 必须指定 --folder 或 --images")
        sys.exit(1)

    config = load_env()
    app_id = config.get("WECHAT_APP_ID")
    app_secret = config.get("WECHAT_APP_SECRET")
    if not app_id or not app_secret:
        print("[ERROR] 请先配置 .env 文件中的 WECHAT_APP_ID 和 WECHAT_APP_SECRET")
        sys.exit(1)

    print(f"[INFO] 公众号: {config.get('WECHAT_OFFICIAL_NAME', 'NANA')}")
    token = get_access_token(app_id, app_secret)

    # ── v3: AI 文案生成（随机选 5-6 张，非全部）──
    print(f"\n[STEP 0] AI分析图片生成文案 ({len(args.images)}张)")
    generated_texts = [""] * len(args.images)

    if args.skip_ai:
        print(f"   [跳过AI文案生成]")
    elif args.texts:
        generated_texts = list(args.texts)
        print(f"   [使用手动文案]")
    else:
        # 随机选 5-6 张图生成文案
        n = min(random.randint(5, 6), len(args.images))
        selected_idx = set(random.sample(range(len(args.images)), n))
        success_count = 0
        for i, img_path in enumerate(args.images):
            if i not in selected_idx:
                continue
            print(f"   [...] 分析图片 {success_count+1}/{n}: {os.path.basename(img_path)}")
            caption = ai_analyze_and_caption(img_path)
            if caption:
                generated_texts[i] = caption
                success_count += 1
                print(f"   [OK] {caption[:40]}...")
            else:
                print(f"   [WARN] AI 分析失败，跳过该张文案")
        print(f"   [OK] {success_count}/{n} 张图已生成文案")

    print(f"\n[STEP 1] 上传图片素材 ({len(args.images)}张，并发5线程)")
    uploaded_results = upload_images_concurrent(token, args.images, max_workers=5)
    uploaded_images = [r for r in uploaded_results if r is not None]

    if not uploaded_images:
        print("[ERROR] 没有成功上传的图片")
        sys.exit(1)

    print(f"\n[STEP 2] 创建草稿 (模板: {args.template})")
    draft_id = create_article(token, args.title, args.desc, uploaded_images, generated_texts, args.template)
    if not draft_id:
        sys.exit(1)

    # v3: 默认只建草稿，确认后再发
    if args.force_publish:
        print(f"\n[STEP 3] WARNING 强制发布文章")
        publish_article(token, draft_id)
    else:
        print(f"\n[STEP 3] OK 已保存为草稿（等你确认）")
        print(f"       确认无误后，加 --force-publish 参数发布")

    print("\n[DONE] 完成!")


if __name__ == "__main__":
    main()
