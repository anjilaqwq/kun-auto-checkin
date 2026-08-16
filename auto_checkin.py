"""
鲲 Galgame 论坛自动签到脚本
每天自动签到获取萌萌点

用法:
  python auto_checkin.py --cookie <你的cookie>
  python auto_checkin.py --cookie <你的cookie> --loop
  KUN_COOKIE=<你的cookie> python auto_checkin.py
"""

import os
import sys
import argparse
import requests
import time
from datetime import datetime

BASE_URL = "https://www.kungal.com"
CHECKIN_ENDPOINT = "/api/user/check-in"
STATUS_ENDPOINT = "/api/user/status"


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


def run_once(cookie_value):
    print("=" * 40)
    print("鲲 Galgame 论坛自动签到")
    print("=" * 40)

    print("\n[签到前状态]")
    print_status(check_status(cookie_value))

    print("\n[执行签到]")
    success = check_in(cookie_value)

    if success:
        print("\n[签到后状态]")
        print_status(check_status(cookie_value))

    return success


def run_loop(cookie_value, interval_hours=24):
    print("启动自动签到服务，按 Ctrl+C 停止\n")
    while True:
        run_once(cookie_value)
        print(f"\n下次签到将在 {interval_hours} 小时后...")
        print("-" * 40)
        try:
            time.sleep(interval_hours * 3600)
        except KeyboardInterrupt:
            print("\n已停止自动签到服务")
            break


def main():
    parser = argparse.ArgumentParser(description="鲲 Galgame 论坛自动签到")
    parser.add_argument("--cookie", help="kungal_session cookie 值")
    parser.add_argument("--loop", action="store_true", help="持续运行模式")
    parser.add_argument("--hours", type=int, default=24, help="循环间隔小时数 (默认24)")
    args = parser.parse_args()

    # 优先使用命令行参数，其次环境变量
    cookie_value = args.cookie or os.environ.get("KUN_COOKIE")
    if not cookie_value:
        print("错误: 请提供 Cookie")
        print("  命令行: python auto_checkin.py --cookie <值>")
        print("  环境变量: KUN_COOKIE=<值> python auto_checkin.py")
        sys.exit(1)

    if args.loop:
        run_loop(cookie_value, args.hours)
    else:
        run_once(cookie_value)


if __name__ == "__main__":
    main()
