@echo off
cd /d D:\Project\qlib
.venv\Scripts\python.exe qlib-src\scripts\get_data.py qlib_data --target_dir D:\Project\qlib\qlib_data\cn_data --region cn --delete_old True 1>"D:\Project\qlib\dl_stdout.log" 2>"D:\Project\qlib\dl_stderr.log"
echo DONE_EXIT=%ERRORLEVEL% >> "D:\Project\qlib\dl_stdout.log"
