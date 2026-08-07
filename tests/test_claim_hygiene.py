"""C10 (docs/65) — 영구 철회 claim 의 재출현 hard-fail scan.

의미론적 정본은 `artifacts/audits/claim_registry.tsv` 다 (docs/65 §5 규율 2)
-- 이 scan 은 보조장치로, 명백히 철회된 문구가 **정정 표식 없이** docs 에
다시 나타나는 것만 잡는다 (G04 재발 방지). 철회 기록 자신은 allowlist:
근처 ±2줄에 표식 토큰(철회/정정/금지/기각/취소선 등)이 있으면 역사적
인용으로 간주한다. grep 은 semantic truth checker 가 아니다 -- 새 패턴
추가는 registry 의 RETRACTED 등재와 함께만.
"""
from __future__ import annotations

import pathlib
import re

DOCS = pathlib.Path(__file__).resolve().parents[1] / "docs"

RETRACTED = [
    ("하드킬 도피 (docs/48 정정 9)", re.compile(r"하드킬로\s*도[망피]")),
    ("성형 채널 구조적 무력 (docs/52 철회)",
     re.compile(r"성형\s*채널.{0,24}(구조적|물리적).{0,12}(무력|불가능)")),
    ("kinetic 창 닫힘 (리뷰 4 기각)", re.compile(r"창이\s*(이미\s*)?닫[혀힌]")),
    ("v_soft = 포획 확률 (영구 금지)",
     re.compile(r"v_?(shot_)?soft.{0,16}포획\s*확률")),
    ("post-fire 환원 (리뷰 4 철회)", re.compile(r"post-?fire\s*로?\s*환원")),
]
MARKERS = ("철회", "정정", "금지", "기각", "오독", "~~", "재인용", "죽은",
           "안 된다")   # "…로 읽으면 안 된다" 류의 명시적 부정 (docs/53 §형)


def test_retracted_claims_do_not_reappear_unmarked():
    bad = []
    for f in sorted(DOCS.glob("*.md")):
        # review_prompt_* 는 리뷰어에게 보낸 프롬프트 원문 -- 역사 기록이라
        # 수정·검사 대상이 아니다 (감사 C005 판정: 수정 불요, 인용 금지만).
        if f.name.startswith("review_prompt_"):
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            for name, pat in RETRACTED:
                if not pat.search(line):
                    continue
                ctx = "\n".join(lines[max(0, i - 2):i + 3])
                if any(m in ctx for m in MARKERS):
                    continue
                bad.append(f"{f.name}:{i + 1} [{name}] {line.strip()[:80]}")
    assert not bad, "철회된 claim 이 정정 표식 없이 재출현:\n" + "\n".join(bad)
