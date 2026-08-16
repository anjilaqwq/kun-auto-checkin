@echo off
chcp 65001 >nul
cd /d "%~dp0"
python auto_checkin.py --cookie %1 >> checkin.log 2>&1
