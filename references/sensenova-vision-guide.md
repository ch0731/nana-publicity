# Sensenova Vision API 调用指南

## API 端点
POST https://token.sensenova.cn/v1/chat/completions

## 模型
- sensenova-6.7-flash-lite — 多模态理解（vision）
- sensenova-u1-fast — 图像生成

## 关键参数：reasoning_effort

⚠️ 必须设置 "reasoning_effort": "none"

Sensenova 6.7 Flash-Lite 默认开启推理模式。如果不设置此参数：
- API 返回 HTTP 200 OK
- content 字段为空字符串
- 实际输出在 reasoning 字段中

## 图片编码方式

WSL 环境下直接读取本地文件并 base64 编码：
import base64
with open("/mnt/d/AI图/每日作品/050501/image.png", "rb") as f:
    img_data = base64.b64encode(f.read()).decode("utf-8")
image_url = f"data:image/png;base64,{img_data}"

## 与 MMX CLI 的区别

| 特性 | MMX CLI | Sensenova API |
|------|---------|---------------|
| 调用方式 | mmx vision describe 子进程 | requests.post() HTTP |
| 图片处理 | CLI 自动 base64 | 需手动 base64 编码 |
| 推理模式 | 无 | 需显式设置 reasoning_effort: "none" |
| 响应字段 | content | content + reasoning（需关闭推理） |