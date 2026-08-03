"""torch 가 **진짜인지** 확인하고, 아니면 torch 표시 테스트를 깨끗이 건너뛴다.

WHY
---
`shepherd/scripts/a3d_calibration.py` 는 torch 없는 샌드박스를 위해 `import torch` 가
`ModuleNotFoundError` 를 내면 **가짜 torch 를 `sys.modules` 에 심는다**. 그 자체는
의도된 것이지만, `sys.modules` 는 프로세스 전역이라 **한 번 심기면 그 pytest 세션의
모든 `import torch` 가 가짜를 받는다.**

그래서 torch 가 없는 인터프리터로 `pytest` 를 돌리면 torch 표시 테스트가 "건너뜀"이
아니라 **실행되고 깨진다** -- 그것도 원인을 못 알아볼 형태로:

    TypeError: cannot unpack non-iterable _Base object
    TypeError: 'Sequential' object is not iterable
    TypeError: 'as_tensor' object is not subscriptable
    TypeError: 'shepherd.scripts.a3d_calibration.no_grad' object does not
               support the context manager protocol

스텁을 세션에 심는 지점은 `tests/test_a3e.py:270` 의 `import shepherd.scripts.
a3d_calibration` 이다 (torch-free 경로를 테스트하려고 **일부러** 부른다). torch 가
진짜로 설치돼 있으면 `import torch` 가 성공해 스텁이 안 깔리므로 무해하다.
근본 해법은 그 import 를 `sys.modules` 격리 픽스처 안으로 넣는 것이지만 별건으로 둔다.

2026-08-03 에 이걸로 한 바퀴 돌았다. "torch 버전 문제" 로 읽혔지만 실제 원인은
**venv 를 안 켜서 torch 가 아예 없었던 것**이었다 (Python 3.14 에는 torch 휠이 없다).

여기서 하는 일은 원인을 **표면으로 끌어올리는 것뿐**이다. 가짜 torch 를 감지하면
`-m torch` 항목을 이유를 붙여 skip 한다. 결과 줄이 달라지므로 눈에 띈다:

    torch 진짜 -> 452 passed, 2 skipped
    torch 가짜 -> 405 passed, 49 skipped   <- venv 를 안 켰다는 신호

**테스트를 무르게 만드는 장치가 아니다.** 서버 런북 [1] 은 venv 를 켠 상태를 전제하고,
그 상태에서 skip 이 2개를 넘으면 멈추라고 되어 있다.
"""
from __future__ import annotations

import pytest


def _torch_status() -> tuple[bool, str]:
    """(진짜인가, 아니라면 왜)."""
    try:
        import torch
    except Exception as exc:                       # ModuleNotFoundError 뿐만이 아니다
        return False, f"import 실패 ({type(exc).__name__}: {exc})"

    # 스텁의 `_Mod` 는 a3d_calibration 안에서 정의된다.
    if type(torch).__module__.startswith("shepherd."):
        return False, f"a3d_calibration 의 스텁이 잡혀 있다 ({type(torch).__module__})"

    # 스텁의 `__getattr__` 은 아무 이름에나 클래스를 돌려주므로 버전이 문자열이 아니다.
    if not isinstance(getattr(torch, "__version__", None), str):
        return False, "torch.__version__ 이 문자열이 아니다 -- 스텁으로 보인다"

    return True, ""


def pytest_collection_modifyitems(config, items):
    ok, why = _torch_status()
    if ok:
        return
    skip = pytest.mark.skip(reason=f"torch 사용 불가: {why}. venv 를 켰는지 확인할 것")
    n = 0
    for item in items:
        if "torch" in item.keywords:
            item.add_marker(skip)
            n += 1
    if n:
        print(f"\n[conftest] torch 사용 불가 -- torch 표시 {n}건을 건너뜁니다. {why}")
