"""ntfy 푸시 훅 — 의존성 없음 · torch-free · **절대 예외를 던지지 않는다**.

WHY 여기 있는가
---------------
이 함수는 원래 `shepherd/scripts/train_m3a.py` 안에만 있었다 (docs/11 §3).
역할 분리 실행기(docs/48)도 같은 훅이 필요한데, 복사하면 이 리포가 반복해서
겪은 사고 — *"같은 규칙이 두 곳에 있고 한쪽만 갱신됐다"* (정정 3 · 정정 8 ·
결함 1 · 결함 2, docs/47 §7.4) — 를 한 번 더 만드는 것이다. 그래서 옮겨서
한 곳에 둔다. `train_m3a` 는 이제 이걸 import 하고, 호출부는 그대로다.

규약
----
* `NTFY_TOPIC` 이 비어 있으면 **아무 일도 안 한다** (기본이 off).
* 네트워크·DNS·타임아웃 무엇이 터져도 삼킨다. 9시간짜리 학습을 알림 때문에
  죽이지 않는다. 그래서 반환값도 없다 -- 성공 여부를 호출부가 분기하면
  그 자체가 새 실패 경로가 된다.
* 토픽은 **공개 채널**이다 (ntfy.sh 는 인증 없이 구독 가능). 그래서 메시지에
  수치는 넣되 경로·호스트명 같은 것은 넣지 않는다.
"""
from __future__ import annotations

import os
import urllib.request

__all__ = ["ntfy", "ntfy_enabled"]

_TIMEOUT_S = 3


def ntfy_enabled() -> bool:
    """`NTFY_TOPIC` 이 설정돼 있는가. 런북이 '알림 켜졌는지' 를 찍을 때 쓴다."""
    return bool(os.environ.get("NTFY_TOPIC", "").strip())


def ntfy(msg: str, title: str = "shepherd", priority: str | None = None) -> None:
    """Best-effort push. 토픽이 없으면 no-op, 실패해도 조용히 넘어간다."""
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        return
    try:
        headers = {"Title": title}
        if priority:
            headers["Priority"] = priority
        req = urllib.request.Request(f"https://ntfy.sh/{topic}",
                                     data=msg.encode("utf-8"),
                                     headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=_TIMEOUT_S)
    except Exception:
        pass                        # never fail a run on a push
