"""Research Evidence Dashboard 생성기 — 연구 증거 인벤토리 (결과 시각화 아님).

    python viz/build_research_evidence_dashboard.py
        -> viz/research_evidence_dashboard.html

기존 `viz/build_results_dashboard.py` (결과 시각화) 와 **별개**다. 이 페이지의
질문은 "숫자가 얼마인가" 가 아니라 "무엇이 실재하고 · 어떻게 생성됐고 · 어디까지
검증됐고 · 논문에 무엇을 쓸 수 있는가" 다.

authority 우선순위 (구현 전 합의 규율)
--------------------------------------
  존재 여부          filesystem / git
  artifact 등급      results/README.md 의 supersession 블록 (CANONICAL /
                     SUPERSEDED-FOR-MEASUREMENT / NO-OP / PROVENANCE-RETAINED)
  claim status·문구  artifacts/audits/claim_registry.tsv — **수정하지 않는다**,
                     불일치는 CONFLICT 배지로 표시만 한다
  publication 배정   docs/84 §2 동결표 (KSAS 원고는 authority 아님 — 숫자 stale)
  dirty 의미론       shepherd.scripts.pivot_manifest.dirty_state — R-025 3분할을
                     재구현하지 않고 호출 시점에 소비한다 (X-002/X-005 부류 재발 방지)

이 생성기는 **판정을 만들지 않는다**. 부재·모호는 등급으로 표기한다
(RESOLVED / NOT_FOUND / AMBIGUOUS / NONE). lineage edge 는 registry
`Superseded by` 열과 README 블록에서만 도출하며, 도출 불가능한 관계는
비연결로 남긴다 — 그래프가 성긴 것이 현재 리포가 강제하는 관계의 전부다.

결정론: 같은 HEAD · 같은 `--now` 에서 출력은 bit-동일하다
(tests/test_evidence_dashboard_gates.py 가 게이트).

torch-free.
"""
from __future__ import annotations

import argparse
import csv
import html as html_mod
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import shepherd.scripts.pivot_manifest as pivot_manifest            # noqa: E402

REGISTRY = "artifacts/audits/claim_registry.tsv"
RESULTS_README = "results/README.md"

# ---------------------------------------------------------------- registry ---

def load_registry(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


#: 경로로 인정하는 토큰 (registry 셀 안의 산문에서 뽑는다)
_PATH = re.compile(r"(?:results|viz|artifacts|docs|configs|tests|shepherd|figures)"
                   r"/[\w.\-*/]+")
_EMPTY = {"", "—", "-", "–"}


def _token_exists(root: pathlib.Path, tok: str) -> bool:
    if re.fullmatch(r"docs/\d+", tok):            # "docs/58" 류 — 번호 참조
        nn = tok.split("/")[1]
        return any((root / "docs").glob(f"{nn}_*"))
    if "*" in tok:
        return any(root.glob(tok))
    return (root / tok).exists()


def classify_artifact_cell(cell: str | None, root: pathlib.Path) -> dict:
    """claim 의 `Experiment artifact` 셀 4 등급 분류 (drift check B).

        RESOLVED    경로 토큰이 전부 실재
        NOT_FOUND   경로 토큰 중 하나라도 로컬에 없다
        AMBIGUOUS   경로가 아니다 (산문·세션 기록 등) — 해석하지 않는다
        NONE        빈 값 ("—" 등)
    """
    c = (cell or "").strip()
    if c in _EMPTY:
        return {"grade": "NONE", "paths": [], "self_reported_uncommitted": False}
    toks = [t.rstrip(".,;·)") for t in _PATH.findall(c)]
    toks = [t for t in dict.fromkeys(toks) if t]
    if not toks:
        return {"grade": "AMBIGUOUS", "paths": [],
                "self_reported_uncommitted": "미커밋" in c}
    paths = [(t, _token_exists(root, t)) for t in toks]
    grade = "RESOLVED" if all(ok for _, ok in paths) else "NOT_FOUND"
    return {"grade": grade, "paths": paths,
            "self_reported_uncommitted": "미커밋" in c}


_DOC = re.compile(r"docs/(\d+)")


def docs_reference_conflicts(rows: list[dict], root: pathlib.Path) -> list[dict]:
    """registry 셀의 `docs/NN` 참조를 리포 현실과 대조하는 **일반 검사**.

    특정 claim 을 특수 처리하지 않는다 — 같은 부류가 더 생기면 그대로 잡힌다.
      stale-미작성        "docs/NN 미작성" 이라 하나 docs/NN_*.md 가 실재
      referenced-missing  docs/NN 를 참조하나 docs/NN_*.md 가 없다
    registry 는 고치지 않는다. 대시보드가 양쪽을 나란히 보일 뿐이다.
    """
    out, seen = [], set()
    for r in rows:
        cid = r.get("CLAIM_ID", "?")
        text = " ".join(str(v) for v in r.values() if v)
        for mt in _DOC.finditer(text):
            nn = mt.group(1)
            exists = any((root / "docs").glob(f"{nn}_*"))
            tail = text[mt.end(): mt.end() + 16]
            if exists and "미작성" in tail:
                kind = "stale-미작성"
                detail = f"registry 는 docs/{nn} 미작성이라 하나 실재한다"
            elif not exists:
                kind = "referenced-missing"
                detail = f"registry 가 docs/{nn} 를 참조하나 docs/{nn}_*.md 가 없다"
            else:
                continue
            key = (cid, nn, kind)
            if key not in seen:
                seen.add(key)
                out.append({"claim": cid, "doc": f"docs/{nn}", "kind": kind,
                            "detail": detail})
    return out


# ------------------------------------------------- results/README.md 계약 ----

#: README supersession 블록에서 등급을 만드는 key (그 외 key 는 무시)
_README_KEYS = {
    "canonical": "CANONICAL",
    "supersedes-for-measurement": "SUPERSEDED-FOR-MEASUREMENT",
    "provenance-retained": "PROVENANCE-RETAINED",
    "no-op rerun (인용 금지)": "NO-OP",
}


def _parse_readme_block(block: str) -> list[tuple[str | None, dict]]:
    """```text 블록 하나를 (그룹제목, {key: [경로...]}) 목록으로."""
    out: list[tuple[str | None, dict]] = []
    title, data, cur = None, {}, None
    for raw in block.splitlines():
        s = raw.strip()
        if not s:
            cur = None
            continue
        if ":" in s:
            key, _, val = s.partition(":")
            key, val = key.strip(), val.split("#")[0].strip()
            if key in _README_KEYS:
                data.setdefault(key, [])
                if val:
                    data[key].append(val)
                cur = key
                continue
            if not val:                                  # 그룹 제목 줄
                if data:
                    out.append((title, data))
                    data = {}
                title, cur = s.rstrip(":"), None
                continue
            cur = None                                   # reason: 등 — 무시
            continue
        tok = s.split("#")[0].strip()                    # 연속 줄 (경로만)
        if cur and _PATH.fullmatch(tok):
            data[cur].append(tok)
    if data:
        out.append((title, data))
    return out


def parse_results_readme(root: pathlib.Path) -> dict:
    """canonical pointer 의 유일한 authority. 등급 + supersession edge 도출."""
    text = (root / RESULTS_README).read_text(encoding="utf-8")
    grades: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    groups = []
    for block in re.findall(r"```text\n(.*?)```", text, re.S):
        for title, data in _parse_readme_block(block):
            groups.append({"title": title or "", "data": data})
            for key, paths in data.items():
                for p in paths:
                    grades[p] = _README_KEYS[key]
            for old, new in zip(data.get("supersedes-for-measurement", []),
                                data.get("canonical", [])):
                edges.append((old, new, "supersedes-for-measurement"))
            for old, new in zip(data.get("provenance-retained", []),
                                data.get("canonical", [])):
                edges.append((old, new, "provenance-retained"))
    return {"grades": grades, "edges": edges, "groups": groups}


def registry_edges(rows: list[dict]) -> list[tuple[str, str, str]]:
    """registry `Superseded by` 열 — Stage 4 신설, 현재 C034 한 행만 채워져 있다."""
    out = []
    for r in rows:
        cell = (r.get("Superseded by") or "").strip()
        if not cell:
            continue
        for t in dict.fromkeys(re.findall(r"C\d{3}", cell)):
            if t != r["CLAIM_ID"]:
                out.append((r["CLAIM_ID"], t, "registry-superseded-by"))
    return out


def all_edges(root: pathlib.Path, rows: list[dict]) -> list[tuple[str, str, str]]:
    """lineage edge 전체 = README 블록 + registry 열. **이 둘뿐이다** —
    hand-maintained edge 를 추가하면 게이트(EXPECTED_EDGES)가 깨진다."""
    return parse_results_readme(root)["edges"] + registry_edges(rows)


# --------------------------------------------------------------- git 상태 ----

def _git(root: pathlib.Path, *args) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args],
                                       text=True, encoding="utf-8").strip()
    except Exception:                                     # pragma: no cover
        return "unknown"


def tracked_set(root: pathlib.Path) -> set[str]:
    try:
        out = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"],
                                      text=True, encoding="utf-8")
    except Exception:                                     # pragma: no cover
        return set()
    return {p for p in out.split("\0") if p}


def snapshot(root: pathlib.Path) -> dict:
    """Snapshot header. dirty 는 정본 `pivot_manifest.dirty_state` 를 그대로 쓴다
    (R-025 3분할: code_dirty = 실행 코드 divergence 전용 / untracked_present 는
    미추적 산출물 존재 — 의미론을 바꾸지 않는다)."""
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": pivot_manifest.dirty_state(repo=str(root)),
        "claim_registry": REGISTRY,
        "results_registry": RESULTS_README,
        "science_freeze": "docs/84_arxiv_v0_scope_freeze.md "
                          "(E1e 판정 시점 = arXiv v0 science freeze)",
    }


# ------------------------------------------------------------ view model -----

def _status_key(status: str) -> str:
    m = re.match(r"[A-Z]+", status or "")
    return m.group(0) if m else "UNKNOWN"


def claim_cards(rows: list[dict], root: pathlib.Path) -> list[dict]:
    cards = []
    for r in rows:
        res = classify_artifact_cell(r.get("Experiment artifact"), root)
        status = (r.get("Status") or "").strip()
        cards.append({"id": r["CLAIM_ID"], "status": status,
                      "status_key": _status_key(status), "row": r,
                      "resolution": res})
    return cards


def claim_artifact_map(root: pathlib.Path, cards: list[dict]) -> dict[str, list[str]]:
    mp: dict[str, set] = {}
    for c in cards:
        for tok, ok in c["resolution"]["paths"]:
            if not ok:
                continue
            if "*" in tok:
                for hit in sorted(root.glob(tok)):
                    mp.setdefault(hit.relative_to(root).as_posix(), set()).add(c["id"])
            else:
                mp.setdefault(tok, set()).add(c["id"])
    return {k: sorted(v) for k, v in mp.items()}


_STAMP_KEYS = ("code_commit", "protocol_hash", "generated_at", "code_dirty",
               "tracked_dirty", "untracked_present", "judge_commit")


#: 함수명에 stamp 호출 형태의 literal 을 쓰지 않는다 — R-025 scope probe
#: (test_provenance_stamp) 는 viz/ 에서 그 literal 을 가진 파일을 stamped-artifact
#: **생성기**로 간주한다. 이 모듈은 stamp 를 호출하지 않고 **읽기만** 한다.
def _extract_provenance(obj: dict) -> dict | None:
    top = {k: obj[k] for k in _STAMP_KEYS if k in obj}
    if top:
        return top
    for k, v in obj.items():
        if isinstance(v, dict) and "code_commit" in v:
            return {"(under)": k, **{s: v[s] for s in _STAMP_KEYS if s in v}}
    return None


def artifact_records(root: pathlib.Path, tracked: set[str], grades: dict[str, str],
                     claim_map: dict[str, list[str]]) -> list[dict]:
    rdir = root / "results"
    files = sorted((p for p in rdir.iterdir()
                    if p.is_file() and p.name != ".gitkeep"),
                   key=lambda p: p.name)
    names = {p.name for p in files}
    recs = []
    for p in files:
        if p.name.endswith(".manifest.json"):
            continue                                     # 본체 카드에 붙인다
        rel = f"results/{p.name}"
        rec = {"path": rel, "size": p.stat().st_size, "tracked": rel in tracked,
               "grade": grades.get(rel, ""), "claims": claim_map.get(rel, []),
               "manifest": (p.stem + ".manifest.json"
                            if p.stem + ".manifest.json" in names else None),
               "keys": None, "n": None, "stamp": None, "parse_error": None}
        if p.suffix == ".json":
            try:
                try:
                    obj = json.loads(p.read_text(encoding="utf-8"))
                except UnicodeDecodeError:               # 로컬 환경 cp949 산출물
                    obj = json.loads(p.read_text(encoding="cp949"))
                if isinstance(obj, dict):
                    rec["keys"] = list(obj.keys())[:40]
                    for k in ("records", "episodes"):
                        if isinstance(obj.get(k), list):
                            rec["n"] = len(obj[k])
                            break
                    rec["stamp"] = _extract_provenance(obj)
                elif isinstance(obj, list):
                    rec["keys"] = [f"<list[{len(obj)}]>"]
            except Exception as e:                        # 표시만, 수정 금지
                rec["parse_error"] = type(e).__name__
        recs.append(rec)
    return recs


def legacy_dirs(root: pathlib.Path) -> list[dict]:
    out = []
    for d in sorted((p for p in (root / "results").iterdir() if p.is_dir()),
                    key=lambda p: p.name):
        out.append({"name": d.name,
                    "n_files": sum(1 for f in d.rglob("*") if f.is_file())})
    return out


def ksas_assets(root: pathlib.Path, tracked: set[str]) -> list[dict]:
    """KSAS 원고는 **나열만** 한다. authority 아님 — 수치를 읽지 않는다."""
    out = []
    for p in sorted((root / "docs").glob("KSAS2026*"), key=lambda p: p.name):
        rel = p.relative_to(root).as_posix()
        out.append({"path": rel, "size": p.stat().st_size,
                    "tracked": rel in tracked,
                    "badge": "Stage 5 대기 · 숫자 stale",
                    "note": "docs/85 §8: 새 spine 반영 · 숫자는 T0 legacy — "
                            "publication authority 는 docs/84 + registry"})
    return out


def viz_assets(root: pathlib.Path, tracked: set[str],
               grades: dict[str, str]) -> list[dict]:
    out = []
    for p in sorted((root / "viz").glob("*.html"), key=lambda p: p.name):
        rel = f"viz/{p.name}"
        out.append({"path": rel, "size": p.stat().st_size,
                    "tracked": rel in tracked, "grade": grades.get(rel, "")})
    return out


def figure_assets(root: pathlib.Path, tracked: set[str]) -> list[dict]:
    fdir = root / "figures"
    if not fdir.exists():
        return []
    return [{"path": f"figures/{p.name}", "size": p.stat().st_size,
             "tracked": f"figures/{p.name}" in tracked}
            for p in sorted(fdir.iterdir(), key=lambda p: p.name) if p.is_file()]


_VERDICTS = ("넣음", "압축", "아주 짧게", "appendix 또는 삭제", "뺌")


def parse_publication(root: pathlib.Path) -> list[dict]:
    """docs/84 §2 동결표 (넣음/뺌) — publication 배정의 유일한 authority."""
    text = (root / "docs" / "84_arxiv_v0_scope_freeze.md").read_text(encoding="utf-8")
    sec = text.split("\n## 2.")[1].split("\n### 2.1")[0]
    rows = []
    for line in sec.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 3 and cells[0].strip("* ") in _VERDICTS:
            rows.append({"verdict": cells[0].strip("* "),
                         "item": cells[1], "role": cells[2]})
    return rows


def open_questions(root: pathlib.Path, cards: list[dict]) -> list[dict]:
    """H-4 (docs/85 §8 인용) + drift check B 의 NOT_FOUND 를 **같은 패널**에 —
    사용자가 랩 서버 보유 여부를 한 번에 답할 수 있게."""
    items = []
    p85 = root / "docs" / "85_repair_stages_1_4_audit.md"
    if p85.exists():
        mt = re.search(r"H-4:[^\n]*", p85.read_text(encoding="utf-8"))
        if mt:
            items.append({"source": "docs/85 §8 미해결 human decision",
                          "text": "H-4: " + mt.group(0)[len("H-4:"):].strip()})
    miss: dict[str, list[str]] = {}
    for c in cards:
        if c["resolution"]["grade"] != "NOT_FOUND":
            continue
        for tok, ok in c["resolution"]["paths"]:
            if not ok:
                miss.setdefault(tok, []).append(c["id"])
    for tok in sorted(miss):
        cids = ", ".join(sorted(set(miss[tok])))
        items.append({"source": "claim registry drift check B",
                      "text": f"{tok} 가 로컬에 없음 (claims: {cids}) — H-4 와 "
                              "같은 계열: 랩 서버 보유 여부 확인 필요"})
    return items


# ------------------------------------------------------------------ build ----

def build(root: pathlib.Path, *, now: str) -> tuple[str, dict, list[str]]:
    rows = load_registry(root / REGISTRY)
    cards = claim_cards(rows, root)
    readme = parse_results_readme(root)
    conflicts = docs_reference_conflicts(rows, root)
    tracked = tracked_set(root)
    claim_map = claim_artifact_map(root, cards)
    edges = readme["edges"] + registry_edges(rows)

    # ---- 생성기 자체의 drift assertion --------------------------------------
    warnings: list[str] = []
    missing_canonical = [p for p, g in readme["grades"].items()
                         if g == "CANONICAL" and not (root / p).exists()]
    if missing_canonical:
        raise RuntimeError(f"README canonical artifact 가 없다: {missing_canonical}")
    for c in cards:
        if c["status_key"] == "ACTIVE" and c["resolution"]["grade"] == "NOT_FOUND":
            bad = [t for t, ok in c["resolution"]["paths"] if not ok]
            warnings.append(f"drift check B: {c['id']} (ACTIVE) 의 Experiment "
                            f"artifact 미해상 — {', '.join(bad)}")
    for cf in conflicts:
        warnings.append(f"CONFLICT: {cf['claim']} — {cf['detail']}")

    conflict_ids = {c["claim"] for c in conflicts}
    artifacts = artifact_records(root, tracked, readme["grades"], claim_map)
    for a in artifacts:
        if a["parse_error"]:
            warnings.append(f"JSON 판독 불가: {a['path']} ({a['parse_error']})")

    model = {
        "snapshot": snapshot(root),
        "generated": now,
        "claims": cards,
        "conflicts": conflicts,
        "conflict_ids": sorted(conflict_ids),
        "artifacts": artifacts,
        "legacy_dirs": legacy_dirs(root),
        "edges": edges,
        "publication": parse_publication(root),
        "docs_assets": ksas_assets(root, tracked),
        "viz_assets": viz_assets(root, tracked, readme["grades"]),
        "figure_assets": figure_assets(root, tracked),
        "open_questions": open_questions(root, cards),
        "warnings": warnings,
        "paper1": _paper1_model(root),
    }
    return _render(model), model, warnings


def _paper1_model(root: pathlib.Path) -> dict:
    """Paper 1 v0 논리 지도 (viz/paper1_logic.py) — 숫자는 빌드 시점 원자료 재계산."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import paper1_logic
    return paper1_logic.chain(root)


# ------------------------------------------------------------------ HTML -----

_E = html_mod.escape
_P1_CLS = {"확정": "g-ok", "해석": "s-res", "기술통계": "g-amb", "대기": "s-pend", "조건부": "a-sup"}


def _paper1_section(p1: dict) -> str:
    out = ['<section id="paper1"><h2>Paper 1 v0 논리 지도 — 숫자는 빌드 때마다 원자료에서 다시 계산 '
           '<span class="muted">(spine = docs/136, 장부 = docs/131)</span></h2>']
    out.append(f'<div class="card"><b>절단선</b> — {_E(p1["cut_line"])}<br>' +
               "".join(f'<div><b>메시지 {_E(k)}</b> {_E(v)}</div>' for k, v in p1["messages"].items()) +
               '<div class="muted" style="margin-top:6px">상태: ' +
               " · ".join(_badge(k, _P1_CLS[k]) + f" {_E(v)}" for k, v in p1["status"].items()) +
               '</div></div>')
    nodes = {n["id"]: n for n in p1["nodes"]}
    out.append('<h3 class="muted">논리 사슬</h3><div class="card mono">' + "".join(
        f'<div class="edge"><b>{_E(a)}</b> {_E(nodes[a]["claim"][:34])}… → <b>{_E(b)}</b> '
        f'<span class="muted">({_E(lbl)})</span></div>' for a, b, lbl in p1["links"]) + '</div>')
    for n in p1["nodes"]:
        nums = "".join(f'<div class="mono">· {_E(x)}</div>' for x in n["nums"])
        cav = "".join(f'<div class="conf">⚠ {_E(x)}</div>' for x in n["caveats"])
        src = "".join(f'<div class="mono">{_E(x)}</div>' for x in n["src"]) or '<div class="muted">해석식</div>'
        out.append(f'<div class="card" data-search="{_E((n["id"] + " " + n["claim"]).lower())}" data-status="" '
                   f'data-grade=""><div class="hd"><span class="cid">{_E(n["id"])}</span>'
                   f'{_badge("메시지 " + n["msg"], "s-res")}{_badge(n["status"], _P1_CLS[n["status"]])}'
                   f'<span class="muted">{_E(n["sec"])}</span></div>'
                   f'<div class="wording">{_E(n["claim"])}</div>{nums}{cav}{_details("원자료", src)}</div>')
    out.append('<h3 class="muted">봉인된 후속 실험 (로컬 harvest 기준)</h3>')
    for q in p1["queue"]:
        st = _badge("판독 있음", "g-ok") if q["readout"] else _badge("결과 대기", "s-pend")
        out.append(f'<div class="card"><b>{_E(q["name"])}</b> {st} <span class="mono">{_E(q["doc"])}'
                   f'{" · manifest " + _E(q["hash"]) if q["hash"] else " · 계약 미작성"}</span>'
                   f'{"<div class=mono>" + _E(q["readout"]) + "</div>" if q["readout"] else ""}</div>')
    out.append('<h3 class="muted">그림 (artifacts/paper1)</h3><div class="card" style="display:flex;flex-wrap:wrap;gap:10px">' +
               "".join(f'<a href="../{_E(f)}"><img src="../{_E(f)}" alt="{_E(f)}" '
                       f'style="width:240px;background:#fff;border-radius:4px"></a>' for f in p1["figures"]) + '</div>')
    out.append('<h3 class="muted">미해결 gap (docs/131)</h3>' + "".join(
        f'<div class="card"><span class="cid">{_E(g["id"])}</span> {_E(g["item"])}'
        f'<div class="muted">{_E(g["state"])}</div></div>' for g in p1["gaps"]))
    out.append('</section>')
    return "".join(out)

_STATUS_CLS = {"ACTIVE": "s-act", "DOWNGRADED": "s-down", "RETRACTED": "s-ret",
               "PENDING": "s-pend", "CONFLICT": "s-conf", "RESOLVED": "s-res"}
_GRADE_CLS = {"RESOLVED": "g-ok", "NOT_FOUND": "g-miss", "AMBIGUOUS": "g-amb",
              "NONE": "g-none"}
_AGRADE_CLS = {"CANONICAL": "a-canon", "SUPERSEDED-FOR-MEASUREMENT": "a-sup",
               "NO-OP": "a-noop", "PROVENANCE-RETAINED": "a-prov"}


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{_E(text)}</span>'


def _kb(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n >= 1024 else f"{n} B"


def _sel_boxes(item_id: str) -> str:
    return ('<span class="selbox">' + "".join(
        f'<label><input type="checkbox" class="sel" data-item="{_E(item_id)}" '
        f'data-target="{t}">{lbl}</label>'
        for t, lbl in (("ksas", "KSAS"), ("arxiv-main", "arXiv"),
                       ("arxiv-appx", "appx"), ("pres", "발표"))) + "</span>")


def _details(summary: str, body: str) -> str:
    return f"<details><summary>{summary}</summary><div>{body}</div></details>"


def _claim_card(c: dict, conflict_ids: set[str], conflicts: list[dict]) -> str:
    r, res = c["row"], c["resolution"]
    badges = [_badge(c["status"] or "?", _STATUS_CLS.get(c["status_key"], "s-pend")),
              _badge(res["grade"].replace("_", " "), _GRADE_CLS[res["grade"]])]
    if c["id"] in conflict_ids:
        badges.append(_badge("CONFLICT", "s-conf"))
    if res["self_reported_uncommitted"]:
        badges.append(_badge("미커밋 자인", "g-amb"))
    paths = "".join(
        f'<div class="mono">{"✓" if ok else "✗"} {_E(t)}'
        f'{"" if ok else "  <b>(로컬 부재)</b>"}</div>'
        for t, ok in res["paths"]) or '<div class="muted">경로 없음</div>'
    my_conf = "".join(f'<div class="conf">⚠ {_E(cf["detail"])} '
                      f'(<span class="mono">{_E(cf["doc"])}</span>)</div>'
                      for cf in conflicts if cf["claim"] == c["id"])
    rows = []
    for label, col in (("Allowed scope", "Allowed scope"),
                       ("Forbidden wording", "Forbidden wording"),
                       ("Superseded by", "Superseded by"),
                       ("Evidence", "Evidence"),
                       ("Contract", "Contract version"),
                       ("Evidence strength", "Evidence strength"),
                       ("Known counterevidence", "Known counterevidence"),
                       ("Code path", "Code path"),
                       ("Docs", "Docs"),
                       ("Needs follow-up?", "Needs follow-up?")):
        v = (r.get(col) or "").strip()
        if v:
            rows.append(f'<tr><th>{_E(label)}</th><td>{_E(v)}</td></tr>')
    search = " ".join([c["id"], c["status"], res["grade"],
                       r.get("Current wording") or "",
                       r.get("Experiment artifact") or "",
                       r.get("Docs") or ""]).lower()
    return (f'<div class="card claim" data-search="{_E(search)}" '
            f'data-status="{_E(c["status_key"])}" data-grade="{_E(res["grade"])}">'
            f'<div class="hd"><span class="cid">{_E(c["id"])}</span>'
            f'{"".join(badges)}{_sel_boxes("claim:" + c["id"])}</div>'
            f'<div class="wording">{_E((r.get("Current wording") or "").strip())}</div>'
            f'{my_conf}'
            f'{_details("artifact 해상", paths)}'
            f'{_details("registry 원문 (verbatim)", f"<table>{''.join(rows)}</table>")}'
            f'</div>')


def _artifact_row(a: dict) -> str:
    badges = []
    if a["grade"]:
        badges.append(_badge(a["grade"], _AGRADE_CLS.get(a["grade"], "a-prov")))
    badges.append(_badge("tracked" if a["tracked"] else "untracked",
                         "t-ok" if a["tracked"] else "t-no"))
    if a["manifest"]:
        badges.append(_badge("manifest", "a-canon"))
    if a["parse_error"]:
        badges.append(_badge(f"판독 불가 {a['parse_error']}", "g-miss"))
    claims = " ".join(f'<span class="mono cl">{_E(c)}</span>' for c in a["claims"])
    meta = []
    if a["n"] is not None:
        meta.append(f"n={a['n']}")
    meta.append(_kb(a["size"]))
    det = ""
    if a["keys"]:
        body = '<div class="mono">' + ", ".join(_E(k) for k in a["keys"]) + "</div>"
        if a["stamp"]:
            body += ("<div class='mono stamp'>stamp: " +
                     _E(json.dumps(a["stamp"], ensure_ascii=False, sort_keys=True))
                     + "</div>")
        det = _details("keys / stamp", body)
    search = " ".join([a["path"], a["grade"]] + a["claims"]).lower()
    return (f'<div class="card art" data-search="{_E(search)}" data-status="" '
            f'data-grade="{_E(a["grade"] or "")}">'
            f'<span class="mono path">{_E(a["path"])}</span>{"".join(badges)}'
            f'<span class="muted">{" · ".join(meta)}</span> {claims}'
            f'{_sel_boxes("artifact:" + a["path"])}{det}</div>')


def _render(m: dict) -> str:
    s = m["snapshot"]
    d = s["dirty"]
    p = []
    p.append(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research Evidence Dashboard</title><style>
:root{{--bg:#0b0e14;--card:#12161f;--line:#232a38;--fg:#d7dce6;--mut:#8b93a5;
--mono:ui-monospace,Consolas,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.55 -apple-system,'Segoe UI','Malgun Gothic',sans-serif;padding-bottom:40vh}}
a{{color:#7fb3ff}}
.top{{position:sticky;top:0;z-index:9;background:#0d1119ee;border-bottom:1px solid
var(--line);padding:10px 16px;backdrop-filter:blur(4px)}}
.top h1{{font-size:16px;margin:0 0 6px}}
.snap{{font-family:var(--mono);font-size:12px;color:var(--mut)}}
.snap b{{color:var(--fg)}}
.controls{{margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
#search{{background:var(--card);border:1px solid var(--line);color:var(--fg);
padding:6px 10px;border-radius:6px;width:min(340px,60vw)}}
.chip{{cursor:pointer;border:1px solid var(--line);border-radius:12px;
padding:3px 10px;font-size:12px;color:var(--mut);background:var(--card)}}
.chip.on{{color:#fff;border-color:#7fb3ff}}
section{{max-width:1080px;margin:22px auto;padding:0 16px}}
h2{{font-size:15px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:10px 12px;margin:8px 0}}
.card .hd{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.cid{{font-family:var(--mono);font-weight:700;font-size:15px}}
.wording{{margin:6px 0;white-space:pre-wrap}}
.badge{{font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid;
font-family:var(--mono);white-space:nowrap}}
.s-act{{color:#7ee2a8;border-color:#2e7d4f}} .s-down{{color:#ffc46b;border-color:#8a6116}}
.s-ret{{color:#ff8f8f;border-color:#8a2b2b}} .s-pend{{color:#a7b0c0;border-color:#4a5468}}
.s-conf{{color:#ff6b6b;border-color:#b3261e;background:#2a1416}}
.s-res{{color:#9db8e8;border-color:#375a7f}}
.g-ok{{color:#7ee2a8;border-color:#2e7d4f}} .g-miss{{color:#ff8f8f;border-color:#b3261e}}
.g-amb{{color:#ffc46b;border-color:#8a6116}} .g-none{{color:#8b93a5;border-color:#4a5468}}
.a-canon{{color:#7ee2a8;border-color:#2e7d4f}} .a-sup{{color:#c9a7ff;border-color:#6b4d9e}}
.a-noop{{color:#ff8f8f;border-color:#b3261e}} .a-prov{{color:#a7b0c0;border-color:#4a5468}}
.t-ok{{color:#9db8e8;border-color:#375a7f}} .t-no{{color:#ffc46b;border-color:#8a6116}}
.mono{{font-family:var(--mono);font-size:12px}}
.path{{margin-right:6px}} .muted{{color:var(--mut);font-size:12px}}
.cl{{color:#9db8e8;margin-left:4px}}
.conf{{color:#ff9f9f;font-size:13px;margin:4px 0}}
details{{margin-top:6px}} summary{{cursor:pointer;color:var(--mut);font-size:12px}}
details>div{{border-left:2px solid var(--line);margin:6px 0 0 4px;padding:4px 10px}}
table{{border-collapse:collapse;font-size:12.5px}}
th{{color:var(--mut);text-align:left;vertical-align:top;padding:3px 10px 3px 0;
white-space:nowrap}}td{{padding:3px 0;white-space:pre-wrap}}
.warn{{border-color:#8a6116;background:#1d1810}}
.edge{{font-family:var(--mono);font-size:12.5px;margin:4px 0}}
.edge b{{color:#c9a7ff}}
.selbox{{margin-left:auto;display:flex;gap:6px;font-size:11px;color:var(--mut)}}
.selbox label{{cursor:pointer}}
#selpanel{{position:fixed;right:12px;bottom:12px;width:280px;max-height:45vh;
overflow:auto;background:#0d1119f2;border:1px solid var(--line);border-radius:8px;
padding:10px;font-size:12px;display:none}}
#selpanel h3{{margin:0 0 6px;font-size:13px}}
pub td,pub th{{padding:4px 8px}}
</style></head><body>""")

    dirty_s = (f"code_dirty=<b>{d['code_dirty']}</b> · "
               f"tracked_dirty=<b>{d['tracked_dirty']}</b> · "
               f"untracked_present=<b>{d['untracked_present']}</b>")
    p.append(f"""<div class="top"><h1>Research Evidence Dashboard
<span class="muted">— 연구 증거 인벤토리 (숫자 시각화는 results_dashboard.html)</span></h1>
<div class="snap">HEAD <b>{_E(s['head'][:12])}</b> · branch <b>{_E(s['branch'])}</b>
 · {dirty_s} (R-025 3분할) · generated {_E(m['generated'])}<br>
authority: claim = <b>{_E(s['claim_registry'])}</b> · canonical =
<b>{_E(s['results_registry'])}</b> · freeze = <b>{_E(s['science_freeze'])}</b></div>
<div class="controls"><input id="search" placeholder="검색 (claim ID · 경로 · 문구)…">
<span class="muted">status:</span>""")
    for k in ("ACTIVE", "DOWNGRADED", "RETRACTED", "PENDING", "CONFLICT", "RESOLVED"):
        p.append(f'<span class="chip st" data-v="{k}">{k}</span>')
    p.append('<span class="muted">해상:</span>')
    for k in ("RESOLVED", "NOT_FOUND", "AMBIGUOUS", "NONE", "CANONICAL",
              "SUPERSEDED-FOR-MEASUREMENT", "NO-OP"):
        p.append(f'<span class="chip gr" data-v="{k}">{k.replace("_", " ")}</span>')
    p.append('<span class="chip" id="selshow">선택 패널</span></div></div>')
    p.append(_paper1_section(m["paper1"]))

    # --- warnings / conflicts / open questions -------------------------------
    if m["warnings"]:
        p.append('<section><h2>Generation warnings — drift 는 숨기지 않는다</h2>')
        for w in m["warnings"]:
            p.append(f'<div class="card warn">⚠ {_E(w)}</div>')
        p.append('</section>')
    p.append('<section><h2>Open questions (H-4 + drift check B)</h2>')
    for q in m["open_questions"]:
        p.append(f'<div class="card"><span class="muted">{_E(q["source"])}</span>'
                 f'<div>{_E(q["text"])}</div></div>')
    p.append('</section>')

    # --- claims --------------------------------------------------------------
    n_st = {}
    for c in m["claims"]:
        n_st[c["status_key"]] = n_st.get(c["status_key"], 0) + 1
    stat = " · ".join(f"{k} {v}" for k, v in sorted(n_st.items()))
    p.append(f'<section><h2>Claim registry — {len(m["claims"])} 행 '
             f'<span class="muted">({_E(stat)})</span></h2>')
    conflict_ids = set(m["conflict_ids"])
    for c in m["claims"]:
        p.append(_claim_card(c, conflict_ids, m["conflicts"]))
    p.append('</section>')

    # --- artifacts -----------------------------------------------------------
    canon = [a for a in m["artifacts"] if a["grade"]]
    rest = [a for a in m["artifacts"] if not a["grade"]]
    p.append(f'<section><h2>Artifact browser — results/ '
             f'({len(m["artifacts"])} 파일 · 등급은 results/README.md 계약)</h2>')
    p.append('<h3 class="muted">supersession 계약 대상</h3>')
    for a in canon:
        p.append(_artifact_row(a))
    p.append('<h3 class="muted">기타 (계약 미대상 — 등급 없음이 정상)</h3>')
    for a in rest:
        p.append(_artifact_row(a))
    dirs = " · ".join(f'{_E(d["name"])} ({d["n_files"]})' for d in m["legacy_dirs"])
    p.append(f'<div class="card"><span class="muted">하위 디렉토리 (legacy run 산출물, '
             f'파일 수만 표시):</span><div class="mono">{dirs}</div></div></section>')

    # --- lineage -------------------------------------------------------------
    p.append(f'<section><h2>Lineage / supersession — {len(m["edges"])} edges</h2>'
             '<div class="muted">registry `Superseded by` 열 + results/README.md '
             '블록에서만 도출. 성기게 보이는 것이 현재 리포가 강제하는 관계의 전부다 '
             '— 비연결은 비연결로 남긴다.</div>')
    for old, new, kind in m["edges"]:
        p.append(f'<div class="edge">{_E(old)} <b>→ {_E(kind)} →</b> {_E(new)}</div>')
    p.append('</section>')

    # --- publication ---------------------------------------------------------
    p.append('<section><h2>Publication — docs/84 §2 동결표 (유일한 배정 authority)'
             '</h2><div class="card"><table class="pub">'
             '<tr><th>판정</th><th>항목</th><th>역할</th></tr>')
    for r in m["publication"]:
        p.append(f'<tr><td>{_badge(r["verdict"], "s-res")}</td>'
                 f'<td>{_E(r["item"])}</td><td>{_E(r["role"])}</td></tr>')
    p.append('</table></div>')
    p.append('<h3 class="muted">KSAS 원고 (authority 아님 — 수치 미판독)</h3>')
    for k in m["docs_assets"]:
        tr = _badge("tracked" if k["tracked"] else "untracked",
                    "t-ok" if k["tracked"] else "t-no")
        p.append(f'<div class="card"><span class="mono path">{_E(k["path"])}</span>'
                 f'{_badge(k["badge"], "g-amb")}{tr}'
                 f'<span class="muted"> {_kb(k["size"])} — {_E(k["note"])}</span></div>')
    p.append('<h3 class="muted">Figures (generator = shepherd/scripts/paper_figs.py, '
             'frozen-number assertion 내장 — test_curve_payload_and_figures 가 추적)</h3>')
    for f in m["figure_assets"]:
        tr = _badge("tracked" if f["tracked"] else "untracked",
                    "t-ok" if f["tracked"] else "t-no")
        p.append(f'<div class="card"><span class="mono path">{_E(f["path"])}</span>{tr}'
                 f'<span class="muted"> {_kb(f["size"])}</span>'
                 f'{_sel_boxes("figure:" + f["path"])}</div>')
    p.append('<h3 class="muted">viz/ HTML (뷰어 등급은 results/README.md 계약)</h3>')
    for v in m["viz_assets"]:
        b = _badge(v["grade"], _AGRADE_CLS.get(v["grade"], "a-prov")) if v["grade"] else ""
        tr = _badge("tracked" if v["tracked"] else "untracked",
                    "t-ok" if v["tracked"] else "t-no")
        p.append(f'<div class="card"><span class="mono path">{_E(v["path"])}</span>'
                 f'{b}{tr}<span class="muted"> {_kb(v["size"])}</span></div>')
    p.append('</section>')

    # --- selection panel + JS ------------------------------------------------
    p.append("""<div id="selpanel"><h3>Selected for paper</h3><div id="sellist"></div>
<span class="chip" id="selclear">비우기</span></div>
<script>
(function(){
var KEY='red_paper_selection';
var st=JSON.parse(localStorage.getItem(KEY)||'{}');
var stF='',grF='';
function save(){localStorage.setItem(KEY,JSON.stringify(st));renderSel();}
function renderSel(){
  var by={};Object.keys(st).forEach(function(it){(st[it]||[]).forEach(function(t){
    (by[t]=by[t]||[]).push(it);});});
  var el=document.getElementById('sellist');el.innerHTML='';
  Object.keys(by).sort().forEach(function(t){
    var h='<b>'+t+'</b><ul>'+by[t].sort().map(function(i){return '<li class="mono">'
      +i.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</li>';}).join('')+'</ul>';
    el.insertAdjacentHTML('beforeend',h);});
  if(!Object.keys(by).length)el.textContent='(없음)';}
document.querySelectorAll('.sel').forEach(function(cb){
  var it=cb.dataset.item,t=cb.dataset.target;
  cb.checked=(st[it]||[]).indexOf(t)>=0;
  cb.addEventListener('change',function(){
    var a=st[it]||[];var i=a.indexOf(t);
    if(cb.checked&&i<0)a.push(t);if(!cb.checked&&i>=0)a.splice(i,1);
    if(a.length)st[it]=a;else delete st[it];save();});});
document.getElementById('selclear').onclick=function(){st={};save();};
document.getElementById('selshow').onclick=function(){
  var p=document.getElementById('selpanel');
  p.style.display=p.style.display==='block'?'none':'block';renderSel();};
function apply(){
  var q=document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('.card.claim,.card.art').forEach(function(c){
    var okQ=!q||c.dataset.search.indexOf(q)>=0;
    var okS=!stF||c.dataset.status===stF;
    var okG=!grF||c.dataset.grade===grF;
    c.style.display=(okQ&&okS&&okG)?'':'none';});}
document.getElementById('search').addEventListener('input',apply);
document.querySelectorAll('.chip.st').forEach(function(ch){
  ch.onclick=function(){stF=(stF===ch.dataset.v)?'':ch.dataset.v;
    document.querySelectorAll('.chip.st').forEach(function(x){
      x.classList.toggle('on',x.dataset.v===stF);});apply();};});
document.querySelectorAll('.chip.gr').forEach(function(ch){
  ch.onclick=function(){grF=(grF===ch.dataset.v)?'':ch.dataset.v;
    document.querySelectorAll('.chip.gr').forEach(function(x){
      x.classList.toggle('on',x.dataset.v===grF);});apply();};});
renderSel();
})();
</script></body></html>""")
    return "\n".join(p)


# ------------------------------------------------------------------- main ----

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="research evidence dashboard 생성")
    ap.add_argument("--out", default="viz/research_evidence_dashboard.html")
    ap.add_argument("--now", default=None,
                    help="생성 시각 문자열 (결정론 검증 시 고정값 주입)")
    a = ap.parse_args(argv)
    now = a.now
    if now is None:
        import datetime
        now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    html, model, warnings = build(ROOT, now=now)
    out = ROOT / a.out
    out.write_text(html, encoding="utf-8")
    print(f"claims={len(model['claims'])} artifacts={len(model['artifacts'])} "
          f"edges={len(model['edges'])} warnings={len(warnings)}")
    for w in warnings:
        print("  [warn]", w)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
