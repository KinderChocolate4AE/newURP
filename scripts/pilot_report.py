import json
import math
import pathlib

ROOT = pathlib.Path("results/m4_pilot")
HOURS_PER_RUN = 5.0          # 파일럿 실측 (3런 동시 / 3코어)
JOBS = 3

base = json.loads(pathlib.Path("results/hold_baseline.json").read_text())
ref = json.loads(pathlib.Path("results/intercept_baseline.json").read_text())
bs = base["by_regime"]["SHAPING_NEEDED"]
rs = ref["by_regime"]["SHAPING_NEEDED"]

print("=" * 78)
print("파일럿 3런 — docs/32 [3] 계산자원 게이트  (판정식이 아니다)")
print("=" * 78)
print(f"기준선  hold      SHAPING 무력화 {bs['neutralized_rate']:.4f} "
      f"(0/{bs['n']})  Wilson 상한 {bs['wilson_hi']:.4f}   <- 1차 판정의 상대")
print(f"        intercept SHAPING 무력화 {rs['neutralized_rate']:.4f} "
      f"({int(round(rs['neutralized_rate'] * rs['n']))}/{rs['n']})  "
      f"Wilson 상한 {rs['wilson_hi']:.4f}   <- 2차 참조 (전부 하드킬)")
print(f"        BAND_AIM  hold 네트 {base['bands']['BAND_AIM']['net_capture']['p']:.4f} / "
      f"intercept 무력화 {ref['bands']['BAND_AIM']['neutralized']['p']:.4f}")
print()

go, rows, dead = False, [], []
# ★ train_m4 는 `--output` **아래에 `seed<N>/`** 를 하나 더 만든다
#   (train_m4.py: out_dir = out_root / f"seed{s}").  즉 실제 경로는
#   results/m4_pilot/s0/seed0/summary.json 이다. glob 한 겹으로는 못 찾는다.
for d in sorted(ROOT.rglob("summary.json")):
    rel = d.relative_to(ROOT).parts
    tag = rel[0] if len(rel) > 1 else d.parent.name
    s = json.loads(d.read_text())
    cf = d.parent / "mission_curve.json"
    hk = cap = 0.0
    if cf.exists():
        curve = json.loads(cf.read_text())
        if curve:
            hk = max((c.get("regime/shape/hard_kill") or 0.0) for c in curve)
            cap = max((c.get("regime/shape/captured") or 0.0) for c in curve)
    fe = s["final_eval"]
    sh = (fe.get("by_regime") or {}).get("SHAPING_NEEDED", {})
    bands = s.get("final_eval_bands") or {}
    aim = bands.get("BAND_AIM") or {}
    aim_n = (aim.get("neutralized") or {}).get("p", 0.0) or 0.0
    aim_c = (aim.get("net_capture") or {}).get("p", 0.0) or 0.0
    hit = hk > 0 or aim_n > 0
    go = go or hit
    rows.append((tag, hk, cap, sh, aim_n, aim_c, aim.get("n", 0), fe, hit,
                 s.get("resumed_from", 0)))

if not rows:
    print("!! summary.json 이 하나도 없다.  아래를 먼저 볼 것:")
    print(f"     find {ROOT} -name '*.json' | head")
    print(f"     for f in {ROOT}/*/*.log; do echo \"-- $f\"; tail -n 3 \"$f\"; done")
    raise SystemExit(1)

print(f"{'런':>4}  {'shape_hk':>9} {'shape_cap':>9} | "
      f"{'SHAPING 무력화':>14} | {'BAND_AIM 무력화':>15} {'네트':>7} | "
      f"{'전체':>6} {'비손실':>7}   게이트")
print("-" * 78)
for tag, hk, cap, sh, aim_n, aim_c, an, fe, hit, res in rows:
    shr = sh.get("neutralized_rate", 0.0)
    print(f"{tag:>4}  {hk:9.3f} {cap:9.3f} | {shr:9.3f} (n={sh.get('n', 0):3d}) | "
          f"{aim_n:10.3f} (n={an:3d}) {aim_c:7.3f} | "
          f"{fe['neutralized_rate']:6.3f} {fe['nondestructive_frac']:7.3f}   "
          f"{'HIT' if hit else '-'}"
          + ("   [resume]" if res else ""))

print()
beat_hold = [r[0] for r in rows
             if r[3].get("neutralized_rate", 0.0) > bs["wilson_hi"]]
print(f"참고: SHAPING 에서 hold Wilson 상한({bs['wilson_hi']:.4f}) 을 넘은 런 = "
      f"{len(beat_hold)}/{len(rows)}  {beat_hold if beat_hold else ''}")
print("      (파일럿은 판정이 아니다. 1차 판정은 [4] 50런 + --aggregate 로만 낸다)")
print()

waves = math.ceil(50 / JOBS)
print("=" * 78)
if go:
    print("판정: GO — [4] 50런 진행")
    print("  근거: shape_hk > 0 또는 BAND_AIM 무력화 > 0 인 런이 있다")
    print(f"  비용: {waves} 웨이브 x {HOURS_PER_RUN:.0f}시간 = 약 "
          f"{waves * HOURS_PER_RUN:.0f}시간 ({waves * HOURS_PER_RUN / 24:.1f}일), --jobs {JOBS}")
else:
    print("판정: STOP — 50런 태우지 않는다")
    print("  근거: 3런 전부 shape_hk = 0 이고 BAND_AIM 무력화 = 0")
    print("  나오는 것은 '협력이 안 된다' 가 아니라 '학습이 안 됐다' 이고 그건 못 쓴다")
    print("  다음: 탐색을 먼저 고친다 (하드킬 커리큘럼 / 요격 시연 warm-start)")
print("=" * 78)
