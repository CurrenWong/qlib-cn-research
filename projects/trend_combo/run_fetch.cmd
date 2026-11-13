@echo off
cd /d D:\Project\qlib\projects\trend_combo
..\..\.venv\Scripts\python.exe -u tools\fetch_fundamental.py --workers 6 > results\fetch_run.log 2>&1
echo DONE > results\fetch_done.flag
