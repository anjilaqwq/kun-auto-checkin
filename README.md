# 鲲 Galgame 论坛自动签到脚本

## 使用方法

### 命令行

```bash
# 单次签到
python auto_checkin.py --cookie <你的cookie>

# 持续运行（每24小时签到一次）
python auto_checkin.py --cookie <你的cookie> --loop

# 自定义间隔（如每12小时）
python auto_checkin.py --cookie <你的cookie> --loop --hours 12
```

### 环境变量

```bash
# Linux/Mac
KUN_COOKIE=<你的cookie> python auto_checkin.py

# Windows PowerShell
$env:KUN_COOKIE="<你的cookie>"; python auto_checkin.py
```

### GitHub Actions

1. Fork 本仓库
2. 进入仓库 Settings → Secrets and variables → Actions
3. 添加 Secret: `KUN_COOKIE`，值为你的 cookie
4. 每天北京时间 8:00 自动执行，也可手动触发

## 如何获取 Cookie

1. 浏览器登录 https://www.kungal.com/
2. 按 F12 打开开发者工具
3. 切换到 Application/存储 标签
4. 找到 Cookies → `kungal_session` 的值

## 注意事项

- Cookie 有效期约 90 天，过期后需重新获取
- Cookie 是你的登录凭证，**不要**提交到公开仓库
