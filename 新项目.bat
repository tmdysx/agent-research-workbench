@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 双击开一个新项目：复制一份干净的应用到你指定的文件夹
rem Find Python ourselves: PATH may be broken or point to the Microsoft Store stub
set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%d\python.exe" set "PY=%%d\python.exe"
if not defined PY for /d %%d in ("%ProgramFiles%\Python3*") do if exist "%%d\python.exe" set "PY=%%d\python.exe"
if not defined PY for /f "delims=" %%p in ('where python 2^>nul ^| findstr /v /i WindowsApps') do if not defined PY set "PY=%%p"
if not defined PY (
  echo 找不到 Python 3.12 / Python 3.12 not found: https://www.python.org/downloads/
  pause
  exit /b 1
)
"%PY%" backend\new_project.py
pause
