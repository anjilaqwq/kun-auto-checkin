"""鲲 Galgame 论坛多账号自动签到，使用论坛的 /api/v1 接口。"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from http.cookies import SimpleCookie

import requests

BASE_URL = "https://www.kungal.com"
STATUS_ENDPOINT = "/api/v1/me"
CHECKIN_ENDPOINT = "/api/v1/me/check-ins"
TIMEOUT_SECONDS = 10


class APIError(Exception):
    def __init__(self, message, status=None, code=None):
        super().__init__(message)
        self.status = status
        self.code = code


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


def request_api(session, method, path):
    """读取 v1 的直接 JSON 响应；错误响应使用 HTTP 状态和 problem.code。"""
    try:
        response = session.request(
            method,
            f"{BASE_URL}{path}",
            timeout=TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.exceptions.RequestException as exc:
        raise APIError(f"网络请求失败: {exc}") from exc

    if 300 <= response.status_code < 400:
        raise APIError(f"接口意外重定向 (HTTP {response.status_code})", response.status_code)

    try:
        data = response.json()
    except ValueError as exc:
        raise APIError(f"接口返回非 JSON (HTTP {response.status_code})", response.status_code) from exc

    if not isinstance(data, dict):
        raise APIError(f"接口响应格式错误 (HTTP {response.status_code})", response.status_code)

    if not 200 <= response.status_code < 300:
        code = data.get("code")
        detail = data.get("detail") or data.get("message") or data.get("title")
        message = f"HTTP {response.status_code} / {code or 'UNKNOWN'}"
        if detail:
            message += f": {detail}"
        raise APIError(message, response.status_code, code)

    return data


def print_status(status):
    print(f"  萌萌点: {status['moemoepoint']}")
    print(f"  已签到: {'是' if status['has_checked_in_today'] else '否'}")
    print(f"  新消息: {'有' if status.get('has_unread_messages') else '无'}")


def run_once(cookie_value, account_number=None, account_total=None):
    print("=" * 40)
    if account_number is None:
        print("鲲 Galgame 论坛自动签到")
    else:
        print(f"账号 {account_number}/{account_total}")
    print("=" * 40)

    with requests.Session() as session:
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "kun-auto-checkin/1.0",
        })
        session.cookies.set("kungal_session", cookie_value, domain="www.kungal.com", path="/")

        print("\n[签到前状态]")
        try:
            status = request_api(session, "GET", STATUS_ENDPOINT)
            if status.get("object") != "me" or not isinstance(
                status.get("has_checked_in_today"), bool
            ) or not isinstance(status.get("moemoepoint"), int):
                raise APIError("状态响应格式与 /api/v1/me 不符")
            print_status(status)
            if status["has_checked_in_today"]:
                print("[签到结果] 今天已签到，跳过重复请求")
                return True
        except APIError as exc:
            print(f"[状态查询失败] {exc}")
            if exc.status in (401, 403):
                return False

        print("\n[执行签到]")
        try:
            result = request_api(session, "POST", CHECKIN_ENDPOINT)
        except APIError as exc:
            if exc.status == 409 and exc.code == "ALREADY_EXISTS":
                print("[签到结果] 今天已签到")
                return True
            print(f"[签到失败] {exc}")
            return False

        if result.get("object") != "check_in" or not isinstance(
            result.get("moemoepoint_awarded"), int
        ):
            print("[签到失败] 签到响应格式与 /api/v1/me/check-ins 不符")
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] 签到成功，获得萌萌点: {result['moemoepoint_awarded']}")
        print(f"  当前萌萌点: {result.get('moemoepoint', '未知')}")
        return True


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
