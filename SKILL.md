---
name: nana-publicity
description: NANA公众号自动发布技能。触发词：发公众号、公众号草稿、NANA发布。根据图片内容随机选择5-6张生成AI文案，其余只发图。自动配色+角色模板映射双通道选模板，>10MB图片自动压缩，放入草稿箱供审阅。
version: 3.4.0
tags: [公众号, 微信, NANA, 自动发布]
---

# NANA公众号自动发布技能 v3.2

## 核心优势

- **自动压缩**：>10MB 图片自动压缩到 9MB 以下再上传，不超微信限制
- **智能文案**：Sensenova API 单路 + 规则兜底，直接读本地路径无需 workspace 复制
- **随机选图**：每批随机选 5-6 张生成 AI 文案，其余纯图
- **并发上传**：5线程同时上传

## 使用方式

### v3 推荐：全自动模式
```
发公众号，路径 D:\\AI图\\每日作品\\040903，角色名 木星
```
→ 自动扫描文件夹 → 对照表选模板 → 随机生成文案 → 自动压缩 → 并发上传 → 草稿预览

### 参数说明

| 参数 | 说明 |
|------|------|
| `--folder` | 图片文件夹路径（自动扫描所有图片） |
| `--character` | 角色名，用于自动选模板（见下方对照表） |
| `--template` | 指定配色模板（如 `rose-gold-dynamic`），覆盖自动选择 |
| `--random-template` | ⚡ 强制纯随机模板（忽略角色映射） |
| `--force-publish` | ⚠️ 强制直发（默认只建草稿） |
| `--skip-ai` | 跳过AI文案生成，快速创建草稿 |

> ⚠️ **注意**：`publish.py` 没有 `--auto-texts` 参数。默认行为就是自动为 5-6 张图生成 AI 文案，其余纯图。如需纯图模式，用 `--skip-ai`。

### 配色模板选择规则（优先级顺序）

```
用户指定 --template → --random-template 纯随机 → 角色风格族映射（族内递减随机） → 全部20套递减随机兜底
```

**递减随机策略**：每个模板记录使用次数，选择时从候选池中找出次数最少的模板随机抽取。全部20个模板都跑过一次后，整体减一轮再循环。长期确保所有模板使用率趋近均匀。

**角色→风格族映射**：角色不再绑定单模板，而是映射到风格族，族内递减随机：

| 风格族 | 包含模板 |
|--------|----------|
| purple-holographic | star-purple-dynamic, star-purple-brutal, holographic-dynamic |
| dark-noir | noir-cinema-dynamic, golden-noir-dynamic, neon-luxury-dynamic, midnight-silver-dynamic |
| pink-romantic | rose-gold-dynamic, cherry-blossom-dynamic |
| blue-ocean | deep-ocean-dynamic, aurora-borealis-dynamic |
| green-mist | ethereal-mist-dynamic, zen-garden-dynamic |
| gold-vintage | art-deco-gold-dynamic, vintage-paper-dynamic |
| bold-cyber | brutalist-white-dynamic, cyberpunk-neon-dynamic, retro-arcade-dynamic, industrial-steel-dynamic |
| warm-sunset | lofi-sunset-dynamic |

**20套模板清单：**
star-purple-brutal / star-purple-dynamic / art-deco-gold-dynamic / aurora-borealis-dynamic / brutalist-white-dynamic / cherry-blossom-dynamic / cyberpunk-neon-dynamic / deep-ocean-dynamic / ethereal-mist-dynamic / golden-noir-dynamic / holographic-dynamic / industrial-steel-dynamic / lofi-sunset-dynamic / midnight-silver-dynamic / neon-luxury-dynamic / noir-cinema-dynamic / retro-arcade-dynamic / rose-gold-dynamic / vintage-paper-dynamic / zen-garden-dynamic

## 执行流程

```
1. 扫描文件夹所有图片
2. 选择模板（优先级：--template > --random-template > 角色映射 > 纯随机）
3. 随机选 5-6 张图：
   a. Sensenova API 直接分析（vision 多模态）
   b. 失败则规则兜底生成
4. 自动压缩 >10MB 的图片（到 9MB 以下）
5. 并发上传微信素材
6. 创建草稿
7. 展示预览，等确认
   → 确认后加 --force-publish 发布
```

## Sensenova API 使用规范

Sensenova API 直接读取任意本地路径，自动 base64 编码：
```
POST https://token.sensenova.cn/v1/chat/completions
model: sensenova-6.7-flash-lite
```

### 配置要求
在 `.env` 中配置 `SENSENOVA_API_KEY`：
```
SENSENOVA_API_KEY=sk-你的密钥
```

### 多模态图片理解
```python
import base64, requests

with open("image.png", "rb") as f:
    img_data = base64.b64encode(f.read()).decode("utf-8")

resp = requests.post(
    "https://token.sensenova.cn/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": "sensenova-6.7-flash-lite",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "描述这张图片"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
            ]
        }],
        "reasoning_effort": "none",  // ⚠️ 必须设置
    }
)
```

### ⚠️ 关键 Pitfall：reasoning_effort

**Sensenova 6.7 Flash-Lite 默认开启推理模式。** 如果不设置 `reasoning_effort: "none"`，API 会返回 200 OK 但 `content` 字段为空，实际内容在 `reasoning` 字段中。

| 症状 | API 调用成功但返回空文案 |
|------|--------------------------|
| 原因 | 模型把输出放到了 `reasoning` 字段 |
| 解决 | 所有 vision 调用必须加 `"reasoning_effort": "none"` |
| 参考 | `references/sensenova-reasoning-pitfall.md` |

### ⚠️ Pitfall: Sensenova Error Code 3（bad request / Request size limit exceeded）

**症状**：
- **变种 A（通用）**：Vision 调用返回 `{'message': 'bad request', 'type': 'invalid_request_error', 'code': '3'}`，3次重试全部失败，走规则兜底。
- **变种 B（大小超限）**：Vision 调用返回 `{'code': 3, 'message': 'Request size limit exceeded'}`，仅大图（≥7.5MB）失败，其他图正常。

**可能原因**：
- 变种 A：API Key 过期（被包装为 code 3 而非 HTTP 401）、模型负载。
- 变种 B：原图 ≥7.5MB，base64 后约 10-11MB，超 Sensenova 单请求大小限制。

**处理**：
- 变种 A：先单张测试 vision 是否正常，正常则重跑即可。
- 变种 B：压缩大图到 5MB 以下。publish.py 自动压缩阈值 >10MB 太高了——对 Sensenova vision 来说 ≥7.5MB 就已可能失败。

详见 `references/sensenova-error-code-3.md`。

### ⚠️ 关键配置：本地 .env 与 ~/.hermes/.env 的 key 同步

publish.py 读取的是 **同目录下的 `.env`** 中的 `SENSENOVA_API_KEY`，不是 `~/.hermes/.env` 中的 `SN_API_KEY`。虽然值相同，但本地 `.env` 可能因过期或意外修改导致 vision 失败。

**最佳实践**：每次运行前确认两个 key 一致。如本地 key 失效，用 `~/.hermes/.env` 中的 `SN_API_KEY` 覆盖。

## 角色 → 风格族对照表（精确匹配）

| 角色 | 风格族 | 风格说明 |
|------|--------|----------|
| 木星/苍角/水城雪风 | green-mist | 翠绿电力/空灵 |
| 金星/乱菊/星野樱/小兔/小喵/火野丽/卯之花烈/金美婷/妮可 | pink-romantic | 粉色优雅 |
| 露琪亚/海王满/小小兔/月城柳/伊芙琳 | blue-ocean | 深海蓝调 |
| 黑猫娜/阿丽亚/比利/八津紫 | purple-holographic | 紫色星辉 |
| 女帝/波雅·汉库克 | purple-holographic | 黑长直紫瞳，蛇姬女王霸气 |
| **红袖/井河阿莎姬/対魔忍/阿莎姬/秋山凛子/仪玄/英格丽德/水城不知火/安比** | **dark-noir** | **暗黑电影（深蓝+黑金）** |
| 水城ゆきかぜ/水城雪风 | green-mist | 茶长双马尾粉眼，空灵 |

> ⚠️ 角色不再绑定单模板，而是映射到风格族，族内按**递减随机**选择。同一角色每次发布可能用族内不同模板。

### 配色快速参考（用户指定颜色→风格族映射）

| 用户说 | 风格族 | 风格 |
|--------|--------|------|
| 红色/红黑 | dark-noir | 暗黑电影（深蓝+黑金） |
| 黑色/黑金 | dark-noir | 暗黑电影 |
| 粉色/粉红 | pink-romantic | 粉色优雅 |
| 紫色 | purple-holographic | 紫色星辉 |
| 蓝色/深蓝 | blue-ocean | 深海蓝调 |
| 金色 | gold-vintage | 黑金奢华 |
| 绿色/翠绿 | green-mist | 翠绿空灵 |
| 银色/银白 | dark-noir | 银白冷峻 |
未匹配角色：全部20套递减随机。

> ⚠️ **Pitfall：日语角色名编码匹配问题**
> 
> 使用日语原名（如 `水城ゆきかぜ`）时，字符编码可能导致匹配失败，系统会回退到随机模板。
> 
> **解决方案：**
> 1. 优先使用中文名（如 `水城雪风`）而非日语原名
> 2. 或在映射表中同时添加中日文两种写法
> 3. 如不确定，用 `--random-template` 强制随机选模板

### ⚠️ 关键 Pitfall：角色映射双源同步

角色映射表存在于 **两份** 关键位置，新增角色必须全部更新：

| 文件 | 作用 | 漏掉的后果 |
|------|------|-----------|
| `SKILL.md` | 技能文档中的快速对照表 | AI 文档不准确 |
| `publish.py`（`CHARACTER_STYLE_FAMILY` 字典） | **实际运行时读取的映射** | 角色映射不生效，回退全部20套递减随机 |

> 映射表改为**角色→风格族**架构，族内自动递减随机，新增角色只需添加到这两处。`references/character-template-map.md` 为辅助参考文件，非强制更新。

> **注意**：`--template` 参数不指定时，自动按角色映射；指定 `--template` 则覆盖映射。使用 `--random-template` 可强制纯随机（忽略角色映射）。

## 标题命名规则

- **格式**: `NANA壁纸 | [角色+特点] | [获取方式]`
- **示例**: `NANA壁纸 | 木星 | 翠绿电力 治愈系`
- **获取方式**: `限定原图在网盘` / `无水印直存` / `可直存`

## 已知限制

- **Sensenova API 可能失败**: 如遇到 API 错误，改用 `--skip-ai` 纯图发布。
- **草稿内容偏大**: 37KB+ 的草稿微信可能拒绝，接受后重试即可
- **标题不与图片内容挂钩**: 目前标题是规则生成的固定格式 `NANA壁纸 | [角色] | [风格]`，不与实际图片内容关联。用户期望标题根据图片内容动态生成，但这依赖 Vision API 稳定可用。当前 Vision API 频繁 error code 3，暂不可行。

### ⚠️ 性能 Pitfall：改配色不应重传图片

**问题**：`publish.py` 没有"只改模板"模式。每次指定 `--template` 都会重新扫描文件夹、上传9张图片、调用 AI 生成文案。如果只是改个配色，这个流程太慢了。

**用户反馈**：*"为什么这么久啊，只是改个配色"* — 完全正确，改模板不应该重传图片。

**根因**：微信草稿创建是一次性的（create draft），没有"更新草稿模板"的 API。要改模板必须重建草稿，而重建草稿需要重新上传图片（微信素材 ID 不可跨草稿复用）。

**缓解方案**：
1. **先 `--skip-ai`**：改配色时加 `--skip-ai` 跳过 AI 文案生成，节省 vision API 时间
2. **小文件夹**：图片数量越少越快（5-6张比9张快）
3. **后续改进**：需要给 publish.py 加 `--template-only` 模式，复用已上传的素材 media_id

**用户期望**：改配色 ≈ 几秒钟的事，不是全套重跑几分钟。

## 注意事项

- 默认只建草稿，必须加 `--force-publish` 才发布
- 图片 >10MB 会自动压缩（不损失主要画质）
- 压缩文件上传后自动清理，不占用空间
- AI 文案失败不影响整体流程，只该张无文案
- **新增角色映射时必须同步两处**：`SKILL.md` + `publish.py`（`CHARACTER_STYLE_FAMILY` 字典）。

## 变更日志

### v3.4.0 (2026-05-11)
- **重构** 配色模板选择逻辑：角色→风格族映射 + 族内递减随机
- **新增** 8个风格族（purple-holographic/dark-noir/pink-romantic/blue-ocean/green-mist/gold-vintage/bold-cyber/warm-sunset）
- **新增** `template_usage.json` 使用计数器，全部20个模板轮完一轮后重置循环
- **删除** 旧的单模板精确映射表（角色→风格族替代）
- **简化** 角色映射从三源同步改为双源同步（publish.py + SKILL.md）

### v3.3.1 (2026-05-08)
- **新增** 红袖 → noir-cinema-dynamic 角色映射
- **新增** 配色快速参考表（用户说颜色→推荐模板映射）
- **新增** `references/sensenova-error-code-3.md` — error code 3 诊断文档
- **新增** Pitfall: 本地 `.env` 与 `~/.hermes/.env` 的 Sensenova key 同步问题
- **修复** 角色映射表 SKILL.md 与实际 publish.py 映射不一致

### v3.3.4 (2026-05-11)
- **新增** 八津紫 → star-purple-dynamic 角色映射
- **同步** SKILL.md、character-template-map.md、publish.py 三处映射表
- **新增** Sensenova error code 3 变种 B（Request size limit exceeded）诊断
- **新增** Pitfall: Sensenova vision 对 ≥7.5MB 原图可能失败（base64 ~10MB 超限）
- **建议** 考虑将自动压缩阈值从 10MB 下调至 7MB

### v3.3.3 (2026-05-10)
- **新增** 英格丽德/Ingrid → noir-cinema-dynamic 角色映射（対魔忍）
- **同步** SKILL.md、character-template-map.md、publish.py 三处映射表
- **验证** 17张图全自动发布成功（Sensenova vision + 并发上传正常）

### v3.3.2 (2026-05-09)
- **新增** 水城不知火 → noir-cinema-dynamic 角色映射
- **新增** 伊芙琳 → deep-ocean-dynamic 角色映射
- **修复** publish.py 缺少伊芙琳和水城不知火的硬编码映射
- **同步** SKILL.md、character-template-map.md、publish.py 三处映射表

### v3.3.0 (2026-05-06)
- **新增** 水城ゆきかぜ/水城雪风 → ethereal-mist-dynamic 角色映射
- **新增** 女帝/波雅·汉库克 → star-purple-brutal 角色映射
- **新增** 伊芙琳 → deep-ocean-dynamic 角色映射
- **修复** 日语角色名编码匹配问题：添加 pitfall 说明，建议优先用中文名
- **修复** SKILL.md 与 references/character-template-map.md 角色映射表不一致问题

### v3.2.0 (2026-05-05)
- **新增** `--random-template` 参数：强制纯随机模板，跳过角色映射
- **修复** 角色映射优先级过高导致模板无法随机的问题
- **修复** Sensenova API 返回空内容的问题（添加 `reasoning_effort: "none"`）
- **迁移** MMX vision → Sensenova API（MMX 接口返回 error code 4）
- **删除** `wsl_to_win_path()` 函数（已无引用）
- **新增** `SENSENOVA_API_KEY` 配置（从 `~/.hermes/.env` 的 `SN_API_KEY` 复制）

### v3.1.0
- 迁移到 Sensenova API
- 新增角色→模板对照表

---

## 支持文件

| 文件 | 说明 |
|------|------|
| `references/sensenova-reasoning-pitfall.md` | Sensenova reasoning 模式坑点详解 |
| `references/sensenova-vision-guide.md` | Sensenova vision API 调用指南 |
| `references/sensenova-error-code-3.md` | Error code 3 诊断与修复 |
| `references/character-template-map.md` | 完整角色模板映射表 |
| `references/character-template-workflow.md` | 添加新角色的标准流程及三源同步 |
| `references/wechat-rate-limit-retry.md` | WeChat iLink 限流重试方案 |