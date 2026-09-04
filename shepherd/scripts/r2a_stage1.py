"""paper-R2a Stage 1 — resolver · injection feasibility · Tier A pathwise · kill screen.

    python -m shepherd.scripts.r2a_stage1 --feasibility          # 주입 실증 (로컬, ~초)
    python -m shepherd.scripts.r2a_stage1 --pathwise             # Tier A 궤적 게이트 + viz
    python -m shepherd.scripts.r2a_stage1 --seal-protocol        # cells·atol·CRN 봉인
    python -m shepherd.scripts.r2a_stage1 --dt-check             # 본 run 전 필수 (감사 r3)
    python -m shepherd.scripts.r2a_stage1 --run --shard 3 --n-shards 8   # kill screen (랩서버)

샤딩 = scenario 단위 (한 scenario 안에서 5 구현 전부 — paired 보존). 전역 STOP =
artifacts/r2a/stage1/HARD_KILL_STOP sentinel (O_EXCL; 전 shard 가 scenario 경계마다 확인).

계약 = artifacts/r2a/lattice_R2a_P.json (hash 3aa3adef77420d12). STAGE1_GATES 준수:
pathwise 불일치 시 kill screen 수치를 읽지 않는다. HARD_KILL 출현 시 STOP.

주입 원리: ledger `inject` 의 차원값을 ① extra_cfg (config 계열: physics/limits/layout/
cone — draw 뒤에 적용되므로 위협 pin 겸용. ★능력비 3종은 draw 가 a_att 기준으로 만든
값을 덮어써야 하므로 반드시 함께 주입) ② AttackerSpec (행동 계열 + fwd_gain = k_f 주입점)
③ SpawnSpec (스폰 기하) ④ SystemSpec (tau_kill · r_nk) 로 나눠 싣는다.

paired CRN: (chi, eta) 를 무차원 공간에서 SHA-256(seed0, ep) 지터로 추첨 (셀 중심
± [chi 0.01 / eta 0.15]) → 구현별 차원값 역산. 스폰 u·jink 위상은 (seed0, ep) 공유 +
길이 co-scale 로 자동 정합 (jink 위상 2*pi*f*t 는 f co-scale 로 시간 불변).
torch-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.agents.attacker_ladder import AttackerSpec                # noqa: E402
from shepherd.env_sys import RewardSpec, ratified_system                # noqa: E402
from shepherd.m4_config import m4_episode_config                        # noqa: E402
from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.mission_rollout import run_episode                # noqa: E402
from shepherd.scripts.r2a_lattice import (TAU_REF, _inject, dims_from,  # noqa: E402
                                          impls)
from shepherd.spawn_rand import SpawnSpec                               # noqa: E402

ART = ROOT / "artifacts/r2a"
LATTICE_P = ART / "lattice_R2a_P.json"
SEED0 = 1000                      # Stage 1 전용 (Stage 0 의 seed0=0 과 분리)
N_CELL = 400                      # Stage 1 kill screen n (재산정 전 초기값)
JITTER_CHI, JITTER_ETA = 0.01, 0.15
MU, NU, ADV_V = 0.35, 1.0, 1.5    # CAPABILITY_RATIOS (conditioning vector)


# ------------------------------------------------------------------ resolver
def resolve(im: dict, chi: float, eta: float) -> dict:
    """구현 im + 무차원 좌표 → build_m4_env kwargs. ledger inject 와 단일 정의원."""
    inj = _inject(im)
    tau, rho = im["tau"], im["rho"]
    a, v = dims_from(chi, eta, tau, rho)
    extra = {
        "physics.dt": inj["dt"], "physics.tau_deploy": tau,
        "physics.tau_lock": inj["tau_lock"], "physics.net_radius": rho,
        "physics.kill_radius": inj["kill_radius"],
        "physics.a_att_max": a, "physics.att_speed": v,
        "physics.a_lim_max": MU * a,                      # ★draw 파생값 덮어쓰기 (mu 보존)
        "train.limits.limiter_v_max": NU * v,
        "train.limits.adversary_v_max": ADV_V * v,
        "train.limits.adversary_omega": inj["omega_att_slew"],
        "train.limits.limiter_omega": 2.5 * TAU_REF / tau,
        "attitude.omega_max": inj["omega_aim"],
        "viability.cone.range_max": inj["R_max"],
        "viability.cone.half_angle": math.atan(rho / inj["R_max"]),
        "train.layout.adversary_start_x": inj["adversary_start_x"],
        "train.layout.ring_center": (inj["ring_center_x"], 0.0, 0.0),
        "train.layout.ring_radius": inj["ring_radius"],
        "train.layout.r_ring": inj["r_ring"],
        "train.layout.finisher_p0": (inj["finisher_x"], 0.0, 0.0),
        "train.layout.x_fire": inj["x_fire"],
        "train.layout.target_radius": inj["target_radius"],
    }
    attacker = AttackerSpec(level="A2", jink_amp=0.6, route_gain=0.5,
                            jink_freq=inj["jink_freq"],
                            jink_terminal_r=inj["jink_terminal_r"],
                            sense_range=inj["sense_range"],
                            homing_gain=inj["homing_gain"],
                            fwd_gain=inj["k_f"], seed=0)
    return dict(system=ratified_system(tau_kill=inj["tau_kill"], r_nk=inj["r_nk"]),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=attacker,
                spawn=SpawnSpec(dx=inj["spawn_dx"], r_lat=inj["spawn_r_lat"]),
                extra_cfg=extra)


def _lattice() -> dict:
    return json.loads(LATTICE_P.read_text(encoding="utf-8"))


def cells_rule(lat: dict) -> list[tuple[float, float]]:
    """봉인 규칙: eta {2.1, 3.0, 3.9} × chi50(eta) 를 감싸는 micro-grid 이웃 2점."""
    st0 = json.loads((ART / "stage0_envelope.json").read_text(encoding="utf-8"))
    out = []
    for eta in (2.1, 3.0, 3.9):
        c50 = st0["rows"][str(eta)]["chi50_isotonic"]
        lo = math.floor(c50 / 0.02) * 0.02
        out += [(round(lo, 3), eta), (round(lo + 0.02, 3), eta)]
    return out


def draw_cell_jitter(seed0: int, ep: int, chi_c: float, eta_c: float) -> tuple[float, float]:
    """무차원 공간 CRN 추첨 (전 구현 공유). SHA-256 — 파이썬 hash() 금지."""
    h = hashlib.sha256(f"r2a_s1|{seed0}|{ep}".encode()).digest()
    u1 = int.from_bytes(h[:8], "big") / 2 ** 64
    u2 = int.from_bytes(h[8:16], "big") / 2 ** 64
    return chi_c + (2 * u1 - 1) * JITTER_CHI, eta_c + (2 * u2 - 1) * JITTER_ETA


# ------------------------------------------------------------- feasibility --
def feasibility(chi: float = 0.55, eta: float = 3.0) -> dict:
    """ledger 주입 22종의 실증: env 를 실제로 조립하고 resolved 값을 되읽어 대조."""
    lat = _lattice()
    report = {}
    for name, im in impls(lat["tau_B"]).items():
        inj = _inject(im)
        kw = resolve(im, chi, eta)
        a, v = dims_from(chi, eta, im["tau"], im["rho"])
        mismatches = []
        # ① config resolve 대조 (dotted key 전수)
        cfg = m4_episode_config(SEED0, 0, kw["extra_cfg"])
        for key, want in kw["extra_cfg"].items():
            cur = cfg
            for part in key.split("."):
                cur = cur[part]
            got = tuple(cur) if isinstance(cur, (list, tuple)) else float(cur)
            want2 = tuple(want) if isinstance(want, tuple) else float(want)
            if got != want2:
                mismatches.append({"key": key, "want": want2, "got": got})
        # ② 실제 스택 조립 + threat readback (draw 덮어쓰기 검증 — mu/nu 누수 방어)
        st = build_m4_env(SEED0, 0, **kw)
        t = st.threat
        for k, want in [("a_att", a), ("att_speed", v), ("a_lim", MU * a),
                        ("v_lim", NU * v), ("tau", im["tau"]), ("net_radius", im["rho"])]:
            if abs(t[k] - want) > 1e-9:
                mismatches.append({"key": f"threat.{k}", "want": want, "got": t[k]})
        # ③ 살아있는 attacker spec (fwd_gain 주입점 실증)
        sp = kw["attacker"]
        if abs(sp.fwd_gain - inj["k_f"]) > 1e-12 or abs(sp.jink_freq - inj["jink_freq"]) > 1e-12:
            mismatches.append({"key": "attacker", "want": [inj["k_f"], inj["jink_freq"]],
                               "got": [sp.fwd_gain, sp.jink_freq]})
        report[name] = {"ok": not mismatches, "mismatches": mismatches,
                        "n_injected": len(kw["extra_cfg"]) + 7}
    out = {"probe_cell": [chi, eta], "lattice_hash": lat["lattice_hash"],
           "all_ok": all(r["ok"] for r in report.values()), "impls": report}
    (ART / "stage1_feasibility.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# ---------------------------------------------------------------- pathwise --
def _rollout_traj(im: dict, chi: float, eta: float, ep: int) -> dict:
    """1 에피소드 실행 + 공격자 궤적 기록 (env.step 래핑 — run_episode 경로 무수정)."""
    kw = resolve(im, chi, eta)
    st = build_m4_env(SEED0, ep, **kw)
    env, rho, tau = st.env, im["rho"], im["tau"]
    traj = []
    orig = env.step

    def step(*a, **k):
        out = orig(*a, **k)
        att = env._states()[2]                     # 9-vec [p(3), v(3), e(3)]
        traj.append([float(x) / rho for x in np.asarray(att, float)[0:3]])
        return out
    env.step = step
    r = run_episode(env, st.scn, st.lay, seed=SEED0 + ep, limiter_mode="hold",
                    fire_mode="clean", policy=None, baseline_commit=False)
    return {"label": r.label, "steps": r.steps, "traj": traj,
            "dt_tau": float(kw["extra_cfg"]["physics.dt"]) / tau}


def pathwise(n_eps: int = 2) -> dict:
    """Tier A 게이트: 정규화 궤적 (p/rho vs t/tau) 이 R-ref 와 atol 내 일치해야 한다.
    dt/tau 가 전 구현 동일 (1/6) 이므로 스텝 인덱스가 곧 t/tau 격자 — 보간 불필요."""
    lat = _lattice()
    st0 = json.loads((ART / "stage0_envelope.json").read_text(encoding="utf-8"))
    chi, eta = st0["rows"]["3.0"]["chi50_isotonic"], 3.0     # 경계 1셀 calibration
    ims = impls(lat["tau_B"])
    out = {"cell": [chi, eta], "eps": {}, "tier_a_max_dev": 0.0}
    for ep in range(n_eps):
        ref = _rollout_traj(ims["R-ref"], chi, eta, ep)
        row = {"R-ref": {"label": ref["label"], "steps": ref["steps"]}}
        for name, im in ims.items():
            if name == "R-ref":
                continue
            r = _rollout_traj(im, chi, eta, ep)
            n = min(len(ref["traj"]), len(r["traj"]))
            dev = float(max(np.abs(np.asarray(r["traj"][:n]) - np.asarray(ref["traj"][:n])).max(axis=1).max(), 0.0)) if n else float("nan")
            row[name] = {"label": r["label"], "steps": r["steps"], "max_dev": dev,
                         "steps_match": r["steps"] == ref["steps"]}
            if name in ("R-tau-SIM", "R-rho-SIM"):
                out["tier_a_max_dev"] = max(out["tier_a_max_dev"], dev)
        out["eps"][ep] = row
        _plot(ep, chi, eta, ims)
    (ART / "stage1_pathwise.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def _plot(ep: int, chi: float, eta: float, ims: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 5))
    for name, im in ims.items():
        t = np.asarray(_rollout_traj(im, chi, eta, ep)["traj"])
        if len(t):
            ax.plot(t[:, 0], t[:, 1], lw=1.2, label=name,
                    ls="-" if im["tier"] == "A" else "--")
    ax.set_xlabel("x/rho"); ax.set_ylabel("y/rho"); ax.legend(fontsize=8)
    ax.set_title(f"Stage 1 viz-first: ep {ep}, cell (chi {chi:.3f}, eta {eta})")
    fig.tight_layout(); fig.savefig(ART / f"stage1_viz_ep{ep}.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------- protocol seal ---
def seal_protocol() -> dict:
    lat = _lattice()
    pw = json.loads((ART / "stage1_pathwise.json").read_text(encoding="utf-8"))
    fz = json.loads((ART / "stage1_feasibility.json").read_text(encoding="utf-8"))
    assert fz["all_ok"], "feasibility 미통과 — 봉인 금지"
    # atol: Tier A 실측 최대 편차의 10배를 십진 자리로 올림 (하한 1e-6)
    atol = max(10 ** math.ceil(math.log10(max(pw["tier_a_max_dev"], 1e-12) * 10)), 1e-6)
    payload = {
        "schema": "r2a-stage1-protocol-v1", "contract": "R2a-P",
        "lattice_hash": lat["lattice_hash"], "seed0": SEED0, "n_per_cell": N_CELL,
        "cells": cells_rule(lat),
        "cells_rule": "eta {2.1, 3.0, 3.9} x two micro-grid neighbors bracketing chi50(eta)",
        "crn": {"jitter": {"chi": JITTER_CHI, "eta": JITTER_ETA},
                "law": "SHA-256('r2a_s1|seed0|ep') -> uniform; dims back-computed per impl; "
                       "spawn u and jink phase shared via (seed0, ep)"},
        "pathwise_atol": atol, "pathwise_calibration": pw["tier_a_max_dev"],
        "gates": lat["stage1_gates"],
        "sharding": "by scenario: s in [0, 2400), cell = s // n_per_cell; ALL 5 impls run "
                    "per scenario inside one shard (paired structure preserved); 8 shards "
                    "= ~300 scenarios (~1,500 ep, ~37 min nominal) each",
        "stop_sentinel": "artifacts/r2a/stage1/HARD_KILL_STOP — atomic create (O_EXCL) by "
                         "the shard observing HARD_KILL; every shard checks before each "
                         "scenario and halts at the next scenario boundary "
                         "(stopped_by_sentinel flag); the sentinel records (shard, "
                         "scenario, impl) so nothing is excluded silently",
        "q_dec_gate": "every implementation and episode runs at q_dec = dt/tau = 1/6 "
                      "(runtime assert). Pre-Stage-1 diagnostic found strong boundary "
                      "sensitivity to normalized decision cadence: q_dec 1/6 -> 1/12 "
                      "shifted chi50 by ~+0.15; q_dec was therefore reclassified from a "
                      "numerical verification ratio to a governing conditioning "
                      "coordinate BEFORE confirmatory execution (A-prime). The dt/2 run "
                      "is published as a sensitivity diagnostic (stage1_dt_check.json), "
                      "not used as a convergence gate.",
        "n_recalc": "paired correlation for Stage 3 n is computed SEPARATELY for "
                    "R-ref<->R-tau-DOM and R-ref<->R-rho-DOM — never pooled with SIM arms "
                    "(near-identical SIM pairs inflate correlation and understate n); "
                    "per-cell variation inspected; the most conservative n is sealed for "
                    "Stage 3 (>=90% expected PASS at true delta = 0)",
        "supersedes_protocol": ["a24fd8ce82afe7c5 (pre-audit-r3)",
                                "93c201cfba2785d2 (pre-A-prime: dt-check as a "
                                "convergence gate)"],
        "status": "kill screen = falsification screen; no representativeness claim",
    }
    payload["protocol_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    (ART / "stage1_protocol.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


# ------------------------------------------------------------- kill screen --
SENTINEL = ART / "stage1" / "HARD_KILL_STOP"


def _sentinel_write(shard: int, scenario: int, impl: str) -> None:
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    try:                                           # atomic — 최초 발생자만 기록
        with open(SENTINEL, "x", encoding="utf-8") as f:
            json.dump({"shard": shard, "scenario": scenario, "impl": impl}, f)
    except FileExistsError:
        pass


def run_shard(shard: int, n_shards: int = 8) -> dict:
    """scenario 샤딩: 한 scenario 안에서 5 구현 전부 실행 (paired 구조 보존).
    전역 STOP: 매 scenario 시작 전 sentinel 확인 — 다른 shard 의 HARD_KILL 도 멈춘다."""
    proto = json.loads((ART / "stage1_protocol.json").read_text(encoding="utf-8"))
    lat = _lattice()
    ims = impls(lat["tau_B"])
    cells, n_cell = proto["cells"], proto["n_per_cell"]
    total = len(cells) * n_cell
    lo, hi = shard * total // n_shards, (shard + 1) * total // n_shards
    out_dir = ART / "stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"shard{shard:02d}.json"
    records = []
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev["protocol_hash"] == proto["protocol_hash"]:
            records = prev["records"]

    def _save(stopped=False):
        path.write_text(json.dumps(
            {"shard": shard, "n_shards": n_shards, "scenario_range": [lo, hi],
             "protocol_hash": proto["protocol_hash"], "lattice_hash": lat["lattice_hash"],
             "stopped_by_sentinel": stopped, "records": records},
            ensure_ascii=False), encoding="utf-8")

    for s in range(lo + len(records) // len(ims), hi):
        if SENTINEL.exists():
            _save(stopped=True)
            print(f"[shard {shard}] sentinel — halt at scenario {s}", flush=True)
            return {"n_done": len(records), "stopped": True}
        chi_c, eta_c = cells[s // n_cell]
        chi, eta = draw_cell_jitter(proto["seed0"], s, chi_c, eta_c)
        for name, im in ims.items():
            kw = resolve(im, chi, eta)
            q = kw["extra_cfg"]["physics.dt"] / kw["extra_cfg"]["physics.tau_deploy"]
            assert abs(q - 1.0 / 6.0) < 1e-12, (name, q)   # q_dec invariant gate (A-prime)
            st = build_m4_env(proto["seed0"], s, **kw)
            r = run_episode(st.env, st.scn, st.lay, seed=proto["seed0"] + s,
                            limiter_mode="hold", fire_mode="clean", policy=None,
                            baseline_commit=False)
            records.append({"s": s, "impl": name, "cell": [chi_c, eta_c],
                            "chi": chi, "eta": eta, "label": r.label})
            if r.label == "HARD_KILL":               # STAGE1_GATES: 전역 STOP
                _sentinel_write(shard, s, name)
                _save(stopped=True)
                raise SystemExit(f"HARD_KILL STOP: shard {shard} scenario {s} impl {name}")
        if (s - lo + 1) % 20 == 0 or s + 1 == hi:
            _save()
            print(f"[shard {shard}] {s - lo + 1}/{hi - lo} scenarios", flush=True)
    _save()
    return {"n_done": len(records), "stopped": False}


# ------------------------------------------------------------- dt 수렴 검사 --
def dt_check(n: int = 50) -> dict:
    """q_dec 민감도 진단 (A-prime 이후 지위): R-ref, 경계 2셀, paired CRN,
    q_dec 1/6 vs 1/12. 실행 gate 아님 — 발견 (chi50 ~+0.15 이동) 은
    stage1_dt_review.json 에 분류·공개된다."""
    from shepherd.stats import wilson
    proto = json.loads((ART / "stage1_protocol.json").read_text(encoding="utf-8"))
    lat = _lattice()
    im = impls(lat["tau_B"])["R-ref"]
    cells = [tuple(proto["cells"][3]), tuple(proto["cells"][4])]  # (0.56, 3.0), (0.54, 3.9)
    out = {"impl": "R-ref", "n": n, "cells": {}, "rule": "discordant <= 0.10 per cell",
           "protocol_hash": proto["protocol_hash"]}
    ok = True
    for chi_c, eta_c in cells:
        disc, labels = 0, []
        for i in range(n):
            ep = 90_000 + i                          # kill-screen CRN 과 분리된 namespace
            chi, eta = draw_cell_jitter(proto["seed0"], ep, chi_c, eta_c)
            got = []
            for half in (False, True):
                kw = resolve(im, chi, eta)
                if half:
                    kw["extra_cfg"]["physics.dt"] = kw["extra_cfg"]["physics.dt"] / 2
                    kw["extra_cfg"]["train.episode_len"] = 320
                st = build_m4_env(proto["seed0"], ep, **kw)
                r = run_episode(st.env, st.scn, st.lay, seed=proto["seed0"] + ep,
                                limiter_mode="hold", fire_mode="clean", policy=None,
                                baseline_commit=False)
                got.append(r.label)
            labels.append(got)
            disc += got[0] != got[1]
        lo_ci, hi_ci = wilson(disc, n)
        cell_ok = disc / n <= 0.10
        ok &= cell_ok
        out["cells"][f"{chi_c},{eta_c}"] = {
            "discordant": [disc, n], "frac": disc / n, "wilson95": [lo_ci, hi_ci],
            "p_dt": sum(g[0] == "NET_CAPTURE" for g in labels) / n,
            "p_dt2": sum(g[1] == "NET_CAPTURE" for g in labels) / n, "ok": cell_ok}
    out["verdict"] = "PASS" if ok else "STOP_AND_REVIEW"
    (ART / "stage1_dt_check.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feasibility", action="store_true")
    ap.add_argument("--pathwise", action="store_true")
    ap.add_argument("--seal-protocol", action="store_true")
    ap.add_argument("--dt-check", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    a = ap.parse_args(argv)
    if a.feasibility:
        r = feasibility()
        print(f"feasibility all_ok={r['all_ok']}")
        for k, v in r["impls"].items():
            print(f"  {k}: {'OK' if v['ok'] else v['mismatches']}")
    if a.pathwise:
        r = pathwise()
        print(f"pathwise tier_a_max_dev {r['tier_a_max_dev']:.3e}  cell {r['cell']}")
    if a.seal_protocol:
        p = seal_protocol()
        print(f"protocol_hash {p['protocol_hash']}  atol {p['pathwise_atol']:.0e}  "
              f"cells {p['cells']}")
    if a.dt_check:
        r = dt_check()
        print(f"dt_check {r['verdict']}")
        for c, v in r["cells"].items():
            print(f"  cell {c}: discordant {v['discordant']}  p_dt {v['p_dt']:.3f}  "
                  f"p_dt/2 {v['p_dt2']:.3f}")
    if a.run:
        run_shard(a.shard, a.n_shards)


if __name__ == "__main__":
    main()
