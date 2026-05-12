# 2026-05-04 仪玄发布会话记录

## 任务

发布绝区零角色「仪玄」的5张AI生成图片至NANA公众号草稿箱。

## 执行命令

```bash
cd /home/craig/.hermes/skills/nana-publicity && python3 publish.py \
  --folder "/mnt/d/AI图/每日作品/050401" \
  --character "仪玄" \
  --desc "绝区零·仪玄 高清壁纸" \
  --template "noir-cinema-dynamic"
```

## 执行结果

| 项目 | 结果 |
|------|------|
| 图片数量 | 5张 |
| 图片大小 | 2.2-2.4MB（无需压缩） |
| AI文案生成 | 5/5 成功 |
| 图片上传 | 5/5 成功 |
| 草稿创建 | 成功 |
| 草稿ID | `VCCbU0xfJxY74QV4M0kwEPrkFhpiwCI-ROcO3O4hyZHK1f50SMxSsCSXv2hp5EAs` |

## AI生成文案

1. 银发如瀑在子夜流淌，红痕裁剪出肃杀的凄凉。琥珀金眸敛尽尘世疏离，于霓虹碎...
2. 银发如霜划破幽暗长夜，琥珀瞳中锁住冷冽锋芒。明黄劲装撕开明暗边界，碎墨飞...
3. 银发如雪在漆黑裂隙间扬起一抹动人心魄的弧度。金黄外套撕裂了寂静长夜，于工业...
4. 银发如雪划破黑白交错的虚空，金瞳凝望处尽是不可侵犯的孤傲。橘色战衣在极简...
5. 霜雪长发在虚空流淌，一抹明橙色燃尽荒芜。回首凝望黑白之界，利落劲装尽显飒...

## 技术要点

### WSL路径转换

publish.py内置`wsl_to_win_path()`函数，自动将WSL路径`/mnt/d/AI图/...`转换为Windows路径`D:\AI图\...`，供mmx.exe使用。

**关键代码**：
```python
def wsl_to_win_path(path):
    import re
    m = re.match(r'^/mnt/([a-z])/(.*)', path)
    if m:
        drive = m.group(1).upper()
        rest = rest.replace('/', '\\')
        return drive + ':\\' + rest
    return path
```

### MMX CLI调用

```bash
mmx vision describe --image "D:\AI图\每日作品\050401\ComfyUI_16617_.png" \
  --prompt "详细描述这张图片的内容：角色、服装、动作、表情、场景、氛围等" \
  --output text --non-interactive
```

### 微信API调用

1. 获取access_token：`GET https://api.weixin.qq.com/cgi-bin/token`
2. 上传素材：`POST https://api.weixin.qq.com/cgi-bin/material/add_material`
3. 创建草稿：`POST https://api.weixin.qq.com/cgi-bin/draft/add`

## 问题与解决

| 问题 | 解决方案 |
|------|----------|
| 仪玄不在角色映射表中 | 手动指定`--template noir-cinema-dynamic` |
| 微信限流警告 | 自动退避3秒重试，Gateway自动处理 |

## 后续操作

草稿已保存至微信后台，需手动确认发布或运行：

```bash
python3 publish.py --folder "/mnt/d/AI图/每日作品/050401" \
  --character "仪玄" --force-publish
```

## 改进建议

1. **扩展绝区零角色映射**：已新增仪玄、安比、妮可、比利、苍角、月城柳
2. **AI文案质量**：5/5成功率，文案质量高，符合二次元风格
3. **模板选择**：noir-cinema-dynamic适合银发金瞳的暗黑工业风格角色
