"""
鲲 Galgame 论坛自动签到脚本
每天自动签到获取萌萌点

用法:
  python auto_checkin.py --cookie <cookie1> --cookie <cookie2>
  python auto_checkin.py --cookie <cookie1> --cookie <cookie2> --loop
  KUN_COOKIE=<你的cookie> python auto_checkin.py
  KUN_COOKIES='["<cookie1>", "<cookie2>"]' python auto_checkin.py
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from http.cookies import SimpleCookie

import requests

BASE_URL = "https://www.kungal.com"
CHECKIN_ENDPOINT = "/api/user/check-in"
STATUS_ENDPOINT = "/api/user/status"


def normalize_cookie(cookie_value):
    """接受 kungal_session 的值或包含该字段的完整 Cookie 字符串。"""
    cookie_value = cookie_value.strip()
    if not cookie_value:
        return None

    # 原始 Cookie 值本身也可能包含 "="，只有明确包含字段名时才按完整
    # Cookie 请求头解析。
    if "kungal_session=" not in cookie_value:
        return cookie_value

    parsed_cookie = SimpleCookie()
    try:
        parsed_cookie.load(cookie_value)
    except Exception:
        return None

    session_cookie = parsed_cookie.get("kungal_session")
    return session_cookie.value.strip() if session_cookie else None


def parse_cookie_source(raw_value, source_name):
    """解析 JSON 数组或一行一个 Cookie 的配置。"""
    if not raw_value or not raw_value.strip():
        return []

    raw_value = raw_value.strip()
    if raw_value.startswith("["):
        try:
            values = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source_name} 不是有效的 JSON 数组: {exc.msg}") from exc
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"{source_name} 必须是字符串组成的 JSON 数组")
        return values

    return raw_value.splitlines()


def collect_cookies(cli_cookies, env_cookies=None, env_cookie=None):
    """按优先级读取 Cookie，去空值并按原顺序去重。"""
    if cli_cookies:
        raw_cookies = list(cli_cookies)
    elif env_cookies and env_cookies.strip():
        raw_cookies = parse_cookie_source(env_cookies, "KUN_COOKIES")
    else:
        # 兼容原有的单 Cookie 环境变量；也允许其中包含多行。
        raw_cookies = parse_cookie_source(env_cookie, "KUN_COOKIE")

    cookies = []
    seen = set()
    invalid_count = 0
    for raw_cookie in raw_cookies:
        cookie = normalize_cookie(raw_cookie)
        if not cookie:
            if raw_cookie.strip():
                invalid_count += 1
            continue
        if cookie not in seen:
            seen.add(cookie)
            cookies.append(cookie)

    if invalid_count:
        print(f"警告: 已忽略 {invalid_count} 个无法识别的 Cookie 配置")
    return cookies


def get_headers(cookie_value):
    return {
        "Cookie": f"kungal_session={cookie_value}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }


def check_status(cookie_value):
    try:
        resp = requests.get(
            f"{BASE_URL}{STATUS_ENDPOINT}",
            headers=get_headers(cookie_value),
            timeout=10,
        )
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data")
        else:
            print(f"[状态查询] {data.get('message', '未知错误')}")
            return None
    except Exception as e:
        print(f"[状态查询失败] {e}")
        return None


def print_status(status):
    if status:
        print(f"  萌萌点: {status.get('moemoepoints', '未知')}")
        print(f"  已签到: {'是' if status.get('is_check_in') else '否'}")
        print(f"  新消息: {'有' if status.get('has_new_message') else '无'}")


def check_in(cookie_value):
    try:
        resp = requests.post(
            f"{BASE_URL}{CHECKIN_ENDPOINT}",
            headers=get_headers(cookie_value),
            timeout=10,
        )
        data = resp.json()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if data.get("code") == 0:
            points = data.get("data")
            print(f"[{now}] 签到成功! 获得萌萌点: {points}")
            return True
        else:
            msg = data.get("message", "未知错误")
            print(f"[{now}] 签到结果: {msg}")
            if "已签到" in msg or "already" in msg.lower():
                return True
            return False
    except requests.exceptions.RequestException as e:
        print(f"[签到请求失败] {e}")
        return False


def run_once(cookie_value, account_number=None, account_total=None):
    print("=" * 40)
    if account_number is None:
        print("鲲 Galgame 论坛自动签到")
    else:
        print(f"账号 {account_number}/{account_total}")
    print("=" * 40)

    print("\n[签到前状态]")
    print_status(check_status(cookie_value))

    print("\n[执行签到]")
    success = check_in(cookie_value)

    if success:
        print("\n[签到后状态]")
        print_status(check_status(cookie_value))

    return success


def run_all(cookies):
    results = []
    total = len(cookies)
    for index, cookie_value in enumerate(cookies, start=1):
        if index > 1:
            print()
        try:
            success = run_once(cookie_value, index, total)
        except Exception as exc:
            # 某个账号的意外错误不应阻止后续账号签到。
            print(f"[账号 {index} 执行失败] {exc}")
            success = False
        results.append(success)

    success_count = sum(results)
    failed_count = total - success_count
    print("\n" + "=" * 40)
    print(f"签到汇总: 成功 {success_count}/{total}，失败 {failed_count}/{total}")
    print("=" * 40)
    return failed_count == 0


def run_loop(cookies, interval_hours=24):
    print("启动自动签到服务，按 Ctrl+C 停止\n")
    while True:
        run_all(cookies)
        print(f"\n下次签到将在 {interval_hours} 小时后...")
        print("-" * 40)
        try:
            time.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            print("\n已停止自动签到服务")
            break


def main():
    parser = argparse.ArgumentParser(description="鲲 Galgame 论坛自动签到")
    parser.add_argument(
        "--cookie",
        action="append",
        help="kungal_session 值或完整 Cookie；可重复传入多个账号",
    )
    parser.add_argument("--loop", action="store_true", help="持续运行模式")
    parser.add_argument("--hours", type=int, default=24, help="循环间隔小时数 (默认24)")
    args = parser.parse_args()

    if args.hours <= 0:
        parser.error("--hours 必须大于 0")

    try:
        cookies = collect_cookies(
            args.cookie,
            os.environ.get("KUN_COOKIES"),
            os.environ.get("KUN_COOKIE"),
        )
    except ValueError as exc:
        parser.error(str(exc))

    if not cookies:
        parser.error(
            "请通过 --cookie、KUN_COOKIES 或 KUN_COOKIE 提供至少一个有效 Cookie"
        )

    print(f"已加载 {len(cookies)} 个账号")

    if args.loop:
        run_loop(cookies, args.hours)
        return 0
    return 0 if run_all(cookies) else 1


if __name__ == "__main__":
    sys.exit(main())
