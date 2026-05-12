# Sensenova Error Code 3 — Transient Vision API Failure

## 症状

### 变种 A：通用 bad request

```
[WARN] Sensenova API 错误 (attempt 1/3): {'message': 'bad request', 'type': 'invalid_request_error', 'code': '3'}
```

连续 3 次重试全部失败，所有 5-6 张图的 vision 分析都走规则兜底。

### 变种 B：请求大小超限

```
[WARN] Sensenova API 错误 (attempt 1/3): {'code': 3, 'message': 'Request size limit exceeded', 'details': []}
```

**特征**：某些图成功、某张特定图失败（而非全部失败）。失败的那张往往是文件夹中最大的文件。

## 根因

Error code 3 是 Sensenova 的通用 `bad request`。可能原因（按概率排序）：

1. **图片 base64 过大** — 单张 ≥7.5MB 的 PNG base64 编码后约 10-11MB，超过 Sensenova vision 请求体大小限制。变现为 **变种 B**（仅大图失败）。
2. **API Key 过期/失效** — key 字符串正确但 token 已过期。变现为 **变种 A**（全部失败）。
3. **并发限流** — 5 张图并发请求时，Sensenova 可能返回 `code: 3` 作为限流信号。
4. **模型负载** — `sensenova-6.7-flash-lite` 的 vision 能力在高负载时不稳定。

## 诊断

```python
# 1. 检查 key 是否有效（文字 API）
resp = requests.post(
    "https://token.sensenova.cn/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": "sensenova-6.7-flash-lite",
        "messages": [{"role": "user", "content": "你好"}],
        "reasoning_effort": "none",
    },
)
# 200 → key 有效；401 → key 过期

# 2. 检查 vision 是否正常（单张测试，用小图）
with open("test.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
print(f"Base64 size: {len(b64) / 1024 / 1024:.1f} MB")  # 超过 8MB 有风险
resp = requests.post(
    "https://token.sensenova.cn/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": "sensenova-6.7-flash-lite",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "描述这张图"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
        }],
        "reasoning_effort": "none",
    },
)
# 200 → vision 正常；code: 3 → 检查 key 或图片大小
```

### 区分变种 A 和 B

| 特征 | 变种 A (general) | 变种 B (size limit) |
|------|-------------------|---------------------|
| 失败范围 | 全部 5-6 张图 | 仅部分大图失败 |
| 错误消息 | `bad request` | `Request size limit exceeded` |
| 大概率根因 | Key 过期 / 模型负载 | 图片 >7.5MB |
| 修复 | 检查 key / 重试 | 压缩图片到 5MB 以下 |

## 已知事件

| 日期 | 表现 | 根因 |
|------|------|------|
| 2026-05-05 | 所有 16 张图 vision 返回 error code 4（MMX API） | MMX API 废弃，迁移到 Sensenova |
| 2026-05-08 | 9 张图全部 error code 3，规则兜底 | key 在本地 `.env` 中已过期（401），但被包装成 code 3 |
| 2026-05-11 | 5/6 张成功，1 张 7.5MB 图失败（变种 B） | 原图 7.5MB → base64 ~10MB，超 Sensenova 单请求限制 |

## 解决方案

1. **检查本地 `.env`**：publish.py 读取 `SENSENOVA_API_KEY`，确认与 `~/.hermes/.env` 的 `SN_API_KEY` 一致且未过期
2. **压缩大图**：7MB+ 原图建议先压缩到 5MB 以下（publish.py 的 >10MB 自动压缩阈值太高，没触发）
3. **重试即可**：大部分 error code 3 是瞬时的，重新运行即可恢复
4. **降级方案**：`--skip-ai` 纯图发布，不受 vision API 影响

## 关于图片大小限制的建议

publish.py 的自动压缩阈值是 >10MB，但 Sensenova vision 对 **7.5MB+** 的原图已可能失败。建议：

- 考虑将自动压缩阈值从 10MB 下调到 **7MB**，避免大图触发变种 B
- 或只对即将发送 vision API 的 5-6 张图加预压缩逻辑（其他纯图不受影响）
