@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe qlib-src\scripts\get_data.py qlib_data --target_dir qlib_data\cn_data --region cn --delete_old True 1>"dl_stdout.log" 2>"dl_stderr.log"
echo DONE_EXIT=%ERRORLEVEL% >> "dl_stdout.log"
