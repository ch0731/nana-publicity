# WeChat iLink 限流重试方案（B方案）

## 问题

A股收盘复盘日报定时任务（22:00）数据采集成功、简报生成成功，但推送到微信时被 iLink API 限流拦截。

## 症状

```
22:00:36 WARNING [Weixin] rate limited for o9cq804Y; backing off 3.0s
22:00:48 ERROR send failed: iLink sendmessage rate limited (ret=-2)
```

## 配置参数

在 `~/.hermes/.env` 中设置：

```ini
# WeChat retry config (B方案)
WEIXIN_SEND_CHUNK_RETRIES=6
WEIXIN_SEND_CHUNK_RETRY_DELAY_SECONDS=3.0
```

| 参数 | 默认值 | B方案值 | 作用 |
|------|--------|---------|------|
| `WEIXIN_SEND_CHUNK_RETRIES` | 4 | 6 | 重试次数（总尝试=retries+1） |
| `WEIXIN_SEND_CHUNK_RETRY_DELAY_SECONDS` | 1.0 | 3.0 | 基础退避间隔 |
| 限流时退避 | base×3=3s | base×3=9s | 限流专用退避 |

## 重试时序

```
旧方案（默认）:
  4次重试 × 3s退避 = 12s 总窗口 → 不够

B方案:
  第一轮（live adapter）: 6次 × 9s退避 = 54s
  第二轮（standalone fallback）: 6次 × 9s退避 = 54s
  总计: ~108s → 仍不够（限流窗口 >70s）
```

## 当前效果（2026-05-06 验证）

| 项目 | 结果 |
|------|------|
| 重试次数 | ✅ 从4次增加到6次 |
| 退避间隔 | ✅ 从3s增加到9s |
| 总重试窗口 | ✅ 从12s延长到~70s |
| 限流窗口 | ❌ 仍然超过70s，未成功送达 |

## ⚠️ 未解决问题

即使开启了 B 方案重试，22:00 时段仍然推送失败。说明：
1. iLink API 在 22:00 附近的限流窗口 >70 秒
2. 简单增加重试次数无法解决
3. 需要换推送时间段（如 21:00）或改用其他推送方式

## 后续方案（待实施）

### C方案：换时间段
```
cronjob action=update job_id=4f3a457a9f47 schedule="0 21 * * *"
```
将定时任务从 22:00 改到 21:00，避开晚间流量高峰。

### D方案：分段推送
将复盘报告拆分为多段，每段间隔 60 秒发送，降低单次推送频率。
