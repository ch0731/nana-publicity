# MMX Vision → Sensenova API 迁移记录

## 背景

2026-05-05 发公众号任务中，MMX vision API 持续返回 `error code 4`，导致所有图片文案生成失败。

## 错误现象

```
[OK] MMX生成文案: {
  "error": {
    "code": 4,
    "message": ...
  }
}
```

MMX CLI 的 `mmx vision describe` 命令虽然返回 exit code 0，但内容实际是错误 JSON。

## 迁移方案

将 `publish.py` 中三个 vision 相关函数全部替换为 Sensenova API 直接调用：

| 函数 | 旧实现 | 新实现 |
|------|--------|--------|
| `ai_generate_caption` | `mmx vision describe` | Sensenova REST API |
| `analyze_with_image_tool` | `mmx vision describe` | Sensenova REST API |
| `_generate_ai_title` | `mmx vision describe` | Sensenova REST API |

## 技术细节

### Sensenova API 调用方式

```python
import base64, requests

with open(image_path, "rb") as f:
    img_data = base64.b64encode(f.read()).decode("utf-8")

resp = requests.post(
    "https://token.sensenova.cn/v1/chat/completions",
    headers={"Authorization": f"Bearer {sensenova_key}"},
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
    }
)
```

### 删除的无用代码

`wsl_to_win_path()` 函数（WSL 路径转 Windows 路径）在 MMX CLI 模式下必需，但 Sensenova API 直接读本地路径，不再需要此函数。

## 配置要求

在 `.env` 中添加：
```
SENSENOVA_API_KEY=sk-你的密钥
```

获取地址：https://platform.sensenova.cn/console/keys

## 模型参数建议

| 场景 | model | max_tokens | temperature |
|------|-------|------------|-------------|
| 文案生成 | sensenova-6.7-flash-lite | 500 | 0.7 |
| 图片分析 | sensenova-6.7-flash-lite | 1000 | 0.3 |
| 标题生成 | sensenova-6.7-flash-lite | 300 | 0.8 |

## 参考

- Sensenova API 文档：https://platform.sensenova.cn/docs
- Base URL: `https://token.sensenova.cn/v1`