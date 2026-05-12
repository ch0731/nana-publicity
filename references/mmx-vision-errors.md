# MMX Vision API 错误记录

## 错误码 4 — 2026-05-05 秋山凛子发布

**现象**: `mmx vision describe` 对所有 6 张采样图片返回 `error code 4`

```
{"error": {"code": 4, "message": ...}}
```

**影响**: AI 文案生成全部失败，草稿只有纯图无配文。

**可能原因**:
- MiniMax API key 权限不足（vision 接口需要额外权限）
- MMX CLI 版本与 API 不兼容
- 图片格式/大小超出 vision 接口限制

**临时方案**:
1. 用 `--skip-ai` 参数跳过文案，纯图发布
2. 手动写文案后重新创建草稿
3. 检查 `~/.mmx/config.json` 中 `region=cn` 是否指向正确的 API

**排查命令**:
```bash
mmx vision describe --image "D:\\test.png" --prompt "描述这张图"
```

**后续**: 如果持续失败，考虑切换到 OpenRouter 或其他 vision 提供商作为 fallback。