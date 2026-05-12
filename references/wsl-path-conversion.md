# WSL 路径转换模式

## 问题背景

在 WSL 环境下，Windows 程序（如 `mmx.exe`）无法识别 WSL 路径格式 `/mnt/d/...`，需要转换为 Windows 路径格式 `D:\...`。

## 解决方案

### publish.py 内置函数

`nana-publicity/publish.py` 已内置 `wsl_to_win_path()` 函数：

```python
def wsl_to_win_path(path):
    """WSL /mnt/d/... 路径转 Windows D:\... 路径，供 mmx CLI 使用"""
    import re
    m = re.match(r'^/mnt/([a-z])/(.*)', path)
    if m:
        drive = m.group(1).upper()
        rest = m.group(2).replace('/', '\\')
        return drive + ':\\' + rest
    return path
```

### 使用示例

```python
# WSL 路径
wsl_path = "/mnt/d/AI图/每日作品/050401/ComfyUI_16617_.png"

# 转换为 Windows 路径
win_path = wsl_to_win_path(wsl_path)
# 结果: "D:\\AI图\\每日作品\\050401\\ComfyUI_16617_.png"

# 调用 mmx CLI
cmd = f'mmx vision describe --image "{win_path}" --prompt "描述内容"'
```

## 注意事项

1. **空格处理**：路径含空格时需加引号
2. **反斜杠转义**：Python 字符串中反斜杠需转义 `\\`
3. **mmx 配置**：`C:\Users\craig\.mmx\config.json`，region=cn 指向 `api.minimaxi.com`

## 其他场景

此模式适用于所有需要在 WSL 中调用 Windows 程序的场景：
- `mmx.exe` 视觉分析
- `comfyui` 命令行调用
- 其他 Windows 原生工具

## 验证

```bash
# 检查 mmx 是否在 PATH 中
which mmx

# 如找不到，创建包装脚本
mkdir -p /home/craig/bin
cat > /home/craig/bin/mmx << 'EOF'
#!/bin/bash
exec /mnt/c/Users/craig/.bun/bin/mmx.exe "$@"
EOF
chmod +x /home/craig/bin/mmx
export PATH="/home/craig/bin:$PATH"
```
