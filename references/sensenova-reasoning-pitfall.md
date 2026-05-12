# Sensenova Reasoning 模式坑点

## 问题描述

Sensenova 6.7 Flash-Lite 默认开启推理模式（reasoning mode）。当调用 vision API 时，如果不显式关闭推理模式，API 会返回 200 OK 但 `content` 字段为空，实际内容在 `reasoning` 字段中。

## 症状

```json
{
  "id": "xxx",
  "choices": [{
    "message": {
      "role": "assistant",
      "reasoning": "用户要求简单描述这张图片...\n\n1. 观察主体：图片中心是一个动漫风格的女性角色...",
      "content": ""   ← 空的！
    },
    "finish_reason": "length"
  }]
}
```

## 原因

Sensenova 模型默认开启推理能力，思考过程放在 `reasoning` 字段，最终输出放在 `content` 字段。但 vision 任务通常不需要推理，模型会把所有内容都放在 `reasoning` 里。

## 解决方案

在所有 Sensenova vision 调用中添加 `"reasoning_effort": "none"`：

```python
resp = requests.post(
    "https://token.sensenova.cn/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": "sensenova-6.7-flash-lite",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
            ]
        }],
        "max_tokens": 500,
        "temperature": 0.7,
        "reasoning_effort": "none",  // ⚠️ 必须设置
    }
)
```

## 验证

设置 `reasoning_effort: "none"` 后，响应恢复正常：

```json
{
  "choices": [{
    "message": {
      "content": "这张图片展示了一位蓝发女性角色，她身穿黑色紧身衣和黑色长靴...",
      "reasoning": null
    }
  }]
}
```

## 影响范围

- `ai_generate_caption()` — 文案生成
- `analyze_with_image_tool()` — 图片分析
- `_generate_ai_title()` — 标题生成

## 相关文档

- [Sensenova API 文档](https://platform.sensenova.cn/docs)
- `nana-publicity` 技能 SKILL.md
