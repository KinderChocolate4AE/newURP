"""깨끗한 체크아웃이 성립하는가 — **커밋 누락 탐지 전용**. torch 불필요.

WHY
---
명시적 `git add` 규율(2026URP 루트 사고 방지)의 부작용으로 **커밋 안 된 파일이 쌓인다.**
2026-08-03 에 `shepherd/spawn_rand.py` · `obs_threat.py` 가 미추적인 채로 남았는데
커밋된 `m4_env` · `curve_sweep` · `sweep_m4` · `train_m4` 가 전부 그걸 import 한다 —
즉 push 된 저장소는 **clone 하면 import 조차 안 되는 상태**였다. 서버에 올린 뒤에
알면 왕복 한 번을 버린다.

    git clone --quiet . $tmp && cd $tmp && python scripts/check_checkout.py

**torch 를 요구하지 않는다.** 묻는 것은 "파일이 커밋됐는가"이지 "환경이 준비됐는가"가
아니다. 둘을 섞으면 venv 밖에서 못 쓰는 검사가 된다 (첫 판이 그랬다 — `train_m4` 를
import 목록에 넣는 바람에 torch 부재로 죽어서, 정작 알고 싶던 것을 못 봤다).

torch 가 필요한 모듈은 `find_spec` 으로 **존재만** 확인한다. 그 모듈들의 저장소 내부
의존(`m4_env`, `curve_sweep`, `mission_rollout` ...)은 아래 목록이 이미 실제로 import
하므로 사슬은 그쪽에서 검증된다.
"""
from __future__ import annotations

import importlib
import importlib.util
import pathlib
import sys

# 실제로 import 한다 -- 저장소 내부 의존 사슬이 여기서 검증된다.
TORCH_FREE = [
    "shepherd.params", "shepherd.stats", "shepherd.m4_config", "shepherd.m4_env",
    "shepherd.env_sys", "shepherd.obs_threat", "shepherd.spawn_rand",
    "shepherd.scripts.mission_rollout", "shepherd.scripts.curve_sweep",
    "shepherd.scripts.sweep_m4", "shepherd.scripts.op_gate",
    "shepherd.scripts.channel_split", "shepherd.scripts.scale_smoke",
    "shepherd.scripts.slew_audit", "shepherd.scripts.signal_audit",
    "shepherd.scripts.spawn_sweep",
]

# 파일 존재만 확인한다 (module-level `import torch`).
NEEDS_TORCH = ["shepherd.scripts.train_m4"]

# import 대상이 아니지만 없으면 안 되는 것.
MUST_EXIST = [
    "tests/conftest.py", "tests/test_curve_sweep.py", "tests/test_sweep_verdict.py",
    "tests/test_m4_wiring.py", "tests/test_channel_split.py", "tests/test_spawn_rand.py",
    "docs/32_m4_retrain_runbook.md", "docs/40_operating_point_declaration.md",
    "docs/41_train_m4_wiring.md", "docs/45_slew_boundary.md",
    "docs/46_channel_split.md", "docs/47_gate_and_sweep.md",
    "results/hold_baseline.json", "results/intercept_baseline.json",
    "results/curve_hold.json", "results/curve_intercept.json",
]


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    # ★ 갓 clone 한 트리에는 `pip install -e .` 가 안 돼 있다. 저장소 루트를 직접
    #   앞에 꽂아야 **그 트리의** shepherd 를 본다. 안 그러면 어딘가 설치돼 있는
    #   다른 사본을 검사하게 되고, 그러면 이 검사는 아무것도 못 잡는다.
    sys.path.insert(0, str(root))
    bad: list[tuple[str, str]] = []

    def _under_root(path: str | None) -> bool:
        if not path:
            return False
        try:
            pathlib.Path(path).resolve().relative_to(root)
            return True
        except ValueError:
            return False

    for m in TORCH_FREE:
        try:
            mod = importlib.import_module(m)
        except Exception as exc:                     # noqa: BLE001
            bad.append((m, f"{type(exc).__name__}: {exc}"))
            continue
        # ★ import 가 됐다고 끝이 아니다. `pip install -e` 의 editable 파인더가
        #   `shepherd.__path__` 를 원본 저장소까지 넓혀 놓아서, 이 트리에 파일이
        #   **없어도** 원본 사본이 잡혀 조용히 통과한다 (실측으로 확인). 그러면
        #   이 검사는 아무것도 못 잡는다. 그래서 나온 파일이 이 트리 안인지 본다.
        if not _under_root(getattr(mod, "__file__", None)):
            bad.append((m, f"이 트리 밖의 사본이 잡혔다 ({getattr(mod, '__file__', '?')})"
                           " -- 파일이 커밋 안 됐거나 editable 설치가 가리고 있다"))

    for m in NEEDS_TORCH:
        try:
            spec = importlib.util.find_spec(m)
        except Exception as exc:                     # noqa: BLE001
            bad.append((m, f"find_spec 실패 ({type(exc).__name__}: {exc})"))
            continue
        if spec is None or not _under_root(getattr(spec, "origin", None)):
            bad.append((m, "이 트리에 모듈 파일이 없다 -- 커밋 누락"))

    for rel in MUST_EXIST:
        if not (root / rel).exists():
            bad.append((rel, "파일이 없다 -- 커밋 누락"))

    if bad:
        print("clean checkout INCOMPLETE — 커밋 안 된 것이 있다:\n")
        for name, why in bad:
            print(f"  {name}\n      {why}")
        print(f"\n{len(bad)} 건. 로컬에서 `git status --short` 확인 후 add 할 것.")
        return 1

    print(f"clean checkout imports OK   "
          f"({len(TORCH_FREE)} 모듈 import · {len(NEEDS_TORCH)} 존재확인 · "
          f"{len(MUST_EXIST)} 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
