# NANA 公众号角色模板映射工作流

## 添加新角色的标准流程

当用户发布新角色的图片时：

### 1. 确认角色信息
- 角色名（中文名）
- 来源作品（如：绝区零、原神、対魔忍等）
- 角色特征（发色、瞳色、气质）

### 2. 选择模板
对照 `references/character-template-map.md` 中的模板风格速查表：

| 模板 | 主色调 | 适用角色类型 |
|------|--------|-------------|
| star-purple-brutal | 紫金 | 威严、霸气、大女主 |
| star-purple-dynamic | 紫 | 神秘、优雅、御姐 |
| rose-gold-dynamic | 玫瑰金/粉 | 甜美、优雅、女性化 |
| deep-ocean-dynamic | 深蓝/青 | 知性、冷艳、冷静 |
| ethereal-mist-dynamic | 白/翠绿 | 空灵、治愈、清新 |
| noir-cinema-dynamic | 黑金/深蓝 | 暗黑、工业、冷峻 |
| neon-luxury-dynamic | 霓虹/炫彩 | 赛博、动感、活力 |
| midnight-silver-dynamic | 午夜蓝/银 | 机械、冷峻、未来感 |

### 3. 更新映射表
同时更新 **三个** 文件：
1. `references/character-template-map.md` — 详细映射表（含来源作品）
2. `SKILL.md` — 快速对照表（精简版）
3. `publish.py` — 硬编码 `character_template_map` 字典（约第1005行）。这是实际运行时读取的映射，不更新则角色映射不会生效，会回退到随机模板。

> ⚠️ **关键 Pitfall：三源同步**
> 角色映射表存在三份拷贝：`SKILL.md`（文档）、`character-template-map.md`（参考）、`publish.py`（代码）。
> 新增角色时必须同步更新 **全部三处**。遗漏 publish.py 会导致角色映射看似添加了但实际运行不生效（回退到随机模板）。
>
> 这是 2026-05-09 实际踩过的坑：`水城不知火` 加到了两个文档里但没加 publish.py，运行发现用了随机模板而非 noir-cinema-dynamic。

### 4. 测试验证
发布一张图验证模板效果是否符合角色气质。

## 绝区零角色映射（2026-05-05 更新）

| 角色 | 推荐模板 | 风格说明 |
|------|----------|----------|
| 仪玄 | noir-cinema-dynamic | 银发金瞳，暗黑工业风 |
| 安比 | midnight-silver-dynamic | 银发冷峻，机械感 |
| 妮可 | rose-gold-dynamic | 粉发御姐，奢华风 |
| 比利 | star-purple-dynamic | 红发热血，动感风 |
| 苍角 | ethereal-mist-dynamic | 白发萌系，清新风 |
| 月城柳 | deep-ocean-dynamic | 蓝发知性，优雅风 |
| **伊芙琳** | **deep-ocean-dynamic** | **蓝发冷艳，知性风** |

## 模板选择优先级

```
用户指定 --template → --random-template 纯随机 → 角色映射 → 纯随机兜底
```

## 注意事项

- 同一作品的角色可能有不同气质，需单独判断
- 如果角色特征与现有模板都不匹配，可考虑新增模板
- 映射表更新后，下次发布该角色时自动匹配，无需指定 `--random-template`

---

*2026-05-05：伊芙琳（绝区零）→ deep-ocean-dynamic*