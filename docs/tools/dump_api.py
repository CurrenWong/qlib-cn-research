"""扒取已安装 qlib 的真实 API 表面（用于写使用手册，避免凭记忆写错）。"""

import inspect
import pkgutil
from pathlib import Path

import qlib

ROOT = Path(r"D:\Project\qlib\docs\_api_dump")
ROOT.mkdir(parents=True, exist_ok=True)

out = []


def dump(title, obj, filt=None):
    out.append(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    try:
        names = [n for n in dir(obj) if not n.startswith("_")]
        if filt:
            names = [n for n in names if filt(n)]
        for n in sorted(names):
            o = getattr(obj, n)
            if inspect.isclass(o) or inspect.isfunction(o):
                try:
                    sig = str(inspect.signature(o))
                except Exception:
                    sig = "(...)"
                doc = (inspect.getdoc(o) or "").strip().split("\n")[0][:110]
                out.append(f"{n}{sig}\n    {doc}")
            else:
                out.append(f"{n} = {o!r}"[:200])
    except Exception as e:
        out.append(f"ERR {e}")


out.append(f"qlib version: {qlib.__version__}")
out.append(f"qlib path: {Path(qlib.__file__).parent}")

# 1) 顶层
dump("qlib 顶层 API", qlib)

# 2) data
from qlib import data

dump("qlib.data.D (数据入口) 的方法", data.D, filt=lambda n: not n.startswith("_"))

from qlib.data import ops

dump("qlib.data.ops 表达式算子（可直接用于 D.features）", ops, filt=lambda n: n[0].isupper())

# 3) dataset
from qlib.data.dataset import DatasetH, TSDatasetH, Dataset
from qlib.data.dataset.handler import DataHandler, DataHandlerLP

dump("qlib.data.dataset.DatasetH", DatasetH)
dump("qlib.data.dataset.handler.DataHandlerLP", DataHandlerLP)

# 4) contrib handler / model / strategy
from qlib.contrib.data.handler import Alpha158, Alpha360
from qlib.contrib.data.handler import check_transform_proc

dump("qlib.contrib.data.handler.Alpha158", Alpha158)

from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.model.linear import Ridge

dump("qlib.contrib.model.gbdt.LGBModel", LGBModel)
dump("qlib.contrib.model.linear.Ridge", Ridge)

from qlib.contrib.strategy import signal_strategy, order_generator, cost_control

dump("qlib.contrib.strategy.signal_strategy", signal_strategy, filt=lambda n: n[0].isupper())
dump("qlib.contrib.strategy.order_generator", order_generator, filt=lambda n: n[0].isupper())
dump("qlib.contrib.strategy.cost_control", cost_control, filt=lambda n: n[0].isupper())

# 5) backtest
from qlib import backtest

dump("qlib.backtest", backtest, filt=lambda n: not n.startswith("_"))
from qlib.backtest.executor import SimulatorExecutor

dump("qlib.backtest.executor.SimulatorExecutor", SimulatorExecutor)

# 6) workflow
from qlib.workflow import R
from qlib.workflow.recorder import Recorder
from qlib.workflow.record_temp import SignalRecord, SigAnaRecord, PortAnaRecord, HFSignalRecord

dump("qlib.workflow.R", R)
dump("qlib.workflow.record_temp.SignalRecord", SignalRecord)
dump("qlib.workflow.record_temp.PortAnaRecord", PortAnaRecord)

# 7) model ens
try:
    from qlib.model.ens import Rolling, Average, DoubleEnsemble

    dump("qlib.model.ens", None)
    out.append(f"Rolling={Rolling}\nAverage={Average}\nDoubleEnsemble={DoubleEnsemble}")
except Exception as e:
    out.append(f"ens ERR {e}")

# 8) 全部子模块清单
out.append(f"\n{'=' * 78}\nqlib 全部子模块\n{'=' * 78}")
for m in pkgutil.walk_packages(qlib.__path__, prefix="qlib."):
    out.append(m.name)

txt = "\n".join(out)
(ROOT / "api_dump.txt").write_text(txt, encoding="utf-8")
print(f"written {len(txt)} chars -> {ROOT / 'api_dump.txt'}")
