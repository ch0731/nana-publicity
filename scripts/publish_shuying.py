#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成韩漫淑英公众号草稿"""

import random
import subprocess
import sys
from pathlib import Path

# 随机选6张图
src = Path(r'D:\AI图\每日作品\041901')
all_files = list(src.glob('*.png'))
selected = random.sample(all_files, 6)
print(f"选中的6张图片:")
for f in selected:
    print(f"  {f.name}")

# 图片路径列表
image_paths = [str(f) for f in selected]

# 6张图对应的AI描述生成的文案
captions = [
    "黑色蕾丝透视上衣搭配重度破洞牛仔裤，红底尖头细高跟，跪坐姿态，冷艳时尚博主既视感",
    "黑色蕾丝绑带连体衣加破洞牛仔裤，Red Bottom红底高跟鞋气场全开，背蹲回眸的御姐杀手",
    "黑色高领蕾丝连体衣配浅灰破洞牛仔裤，侧身倚桌轻抚面颊，高端时尚大片质感",
    "黑色无袖高领拼接蕾丝上衣，冰蓝破洞牛仔裤层叠穿搭，侧卧大地色长发撩人于无形",
    "黑色蕾丝拼接连体衣配冰蓝破洞牛仔裤，红底细高跟加持，自信站姿冷艳霸气",
    "黑色拼接蕾丝连体衣搭珍珠项链，长发披肩优雅从容，都市女性独立与性感的完美融合",
]

title = "NANA壁纸 | 韩漫淑英 · 美丽新世界 | 无水印直存"

cmd = [
    sys.executable,
    str(Path(__file__).parent.parent / 'skills' / 'nana-publicity' / 'publish.py'),
    '--title', title,
    '--images',
] + image_paths + [
    '--texts',
] + captions

print(f"\n执行命令:")
print(' '.join(cmd))
result = subprocess.run(cmd, capture_output=False)
sys.exit(result.returncode)
