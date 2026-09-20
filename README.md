# 鲲 Galgame 论坛自动签到脚本

## 使用方法

### 命令行

```bash
# 单次签到
python auto_checkin.py --cookie <你的cookie>

# 多账号签到（重复传入 --cookie）
python auto_checkin.py --cookie <账号1的cookie> --cookie <账号2的cookie>

# 持续运行（每24小时签到一次）
python auto_checkin.py --cookie <你的cookie> --loop

# 自定义间隔（如每12小时）
python auto_checkin.py --cookie <你的cookie> --loop --hours 12

# 有账号失败时仍返回退出码 0（适合不希望收到失败通知的定时任务）
python auto_checkin.py --cookie <你的cookie> --no-fail
```

### 环境变量

```bash
# Linux/Mac
KUN_COOKIE=<你的cookie> python auto_checkin.py

# 多账号：JSON 数组
KUN_COOKIES='["<账号1的cookie>", "<账号2的cookie>"]' python auto_checkin.py

# Windows PowerShell
$env:KUN_COOKIE="<你的cookie>"; python auto_checkin.py

# 多账号：一行一个 Cookie
$env:KUN_COOKIES=@"
<账号1的cookie>
<账号2的cookie>
"@; python auto_checkin.py
```

Cookie 来源按 `--cookie`、`KUN_COOKIES`、`KUN_COOKIE` 的顺序优先选用，避免
新旧配置意外混用；同一来源中重复的 Cookie 会被自动去除。Cookie 既可以只填
`kungal_session` 的值，也可以填包含 `kungal_session=...` 的完整 Cookie 字符串。

### GitHub Actions

1. Fork 本仓库
2. 进入仓库 Settings → Secrets and variables → Actions
3. 添加 Secret：
   - 单账号：创建 `KUN_COOKIE`，值为该账号的 Cookie
   - 多账号：创建 `KUN_COOKIES`，值使用 JSON 数组或一行一个 Cookie
4. 每天北京时间 8:00 自动执行，也可手动触发

## 如何获取 Cookie

1. 浏览器登录 https://www.kungal.com/
2. 按 F12 打开开发者工具
3. 切换到 Application/存储 标签
4. 找到 Cookies → `kungal_session` 的值

## 注意事项

- Cookie 有效期约 90 天，过期后需重新获取
- Cookie 是你的登录凭证，**不要**提交到公开仓库
- 多账号会依次签到；单个账号失败不会影响后续账号，结束时会输出汇总
- GitHub Actions 默认使用 `--no-fail`，签到失败会保留在日志中，但不会使任务失败
