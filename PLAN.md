# Qlib 安装与示例跑通计划

目标：在 <repo> 下用 uv 建虚拟环境，安装 GitHub 版 microsoft/qlib，跑通官方示例代码。

## ✅ 状态：全部完成（2026-10-28）

| 步骤 | 结果 |
|---|---|
| 1. 建目录 | ✅ <repo> |
| 2. `uv venv` | ✅ Python 3.12.12 |
| 3. `uv pip install git+...qlib.git` | ✅ pyqlib 0.9.8 @ 5435523，一次编译成功，无需回退 PyPI |
| 3b. 额外：`pip-system-certs` | ✅ 解决 Watt Toolkit MITM 证书问题（原计划未预见） |
| 4. 数据下载 | ✅ 187.4 MB，改写为断点续传脚本（官方脚本不支持续传，且中途被超时打断一次） |
| 5. Quick Start | ✅ examples\01_quickstart.py |
| 6. LightGBM + Alpha158 | ✅ IC 0.0468 / 年化 12.6% / IR 1.43 / MDD -7.23% |
| 7. 记忆记录 | ✅ memory/2026-10-28.md + MEMORY.md 环境硬约束 |

详见 README.md。

