#!/usr/bin/env python3
"""기존 R0.2 run과 그 실행 소스를 읽기 전용으로 동결·집계한다. 엔진을 import/실행하지 않는다."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys

ALIASES = {
    "signal_events": "signal_transmissions",
    "convergence_ticks": "kernel_ticks",
    "proof_reconstruction_cost": "proof_nodes_reconstructed",
    "storage_cost": "storage_bytes",
}
MAX_FILE = 128 * 1024 * 1024
MAX_BUNDLE = 512 * 1024 * 1024


class BaselineError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BaselineError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def loads(data: bytes | str):
    require(len(data) <= MAX_FILE, "파일 크기 한도 초과")
    def unique(pairs):
        out = {}
        for key, val in pairs:
            require(key not in out, "중복 JSON key: " + key)
            out[key] = val
        return out
    def bad(val):
        raise BaselineError("비유한 JSON 값: " + str(val))
    def floating(val):
        value = float(val)
        return value if math.isfinite(value) else bad(val)
    return json.loads(data, object_pairs_hook=unique, parse_constant=bad, parse_float=floating)


def relative(name: str) -> PurePosixPath:
    require(isinstance(name, str) and bool(name), "빈 경로")
    rel = PurePosixPath(name)
    require(bool(rel.parts) and not rel.is_absolute() and rel.as_posix() == name and ".." not in rel.parts
            and "\\" not in name and ":" not in name and rel.parts[0] != ".git", "안전하지 않은 경로: " + name)
    return rel


def linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def safe(root: Path, name: str) -> Path:
    require(not linked(root), "루트 링크/junction 금지")
    p = root
    for part in relative(name).parts:
        p = p / part
        require(not linked(p), "링크/junction 금지: " + str(p))
    require(p.resolve().is_relative_to(root.resolve()), "루트 경계 이탈")
    return p


def read(path: Path) -> bytes:
    require(path.is_file() and not linked(path), "파일 누락/링크: " + str(path))
    require(path.stat().st_size <= MAX_FILE, "파일 크기 한도 초과: " + str(path))
    return path.read_bytes()


def inventory(root: Path, exclude=()) -> set[str]:
    require(root.is_dir() and not linked(root), "디렉터리 누락/링크")
    names = set()
    for path in root.rglob("*"):
        require(not linked(path), "파일 트리의 링크/junction 금지")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            relative(name)
            if name not in exclude:
                names.add(name)
    return names


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def canonical_cost(cost: dict) -> dict:
    require(isinstance(cost, dict), "cost 객체 필요")
    for alias, primary in ALIASES.items():
        require(alias in cost and primary in cost and cost[alias] == cost[primary], "비용 별칭 불일치: " + alias)
    for key, value in cost.items():
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0, "잘못된 비용: " + key)
        if key != "wall_seconds":
            require(type(value) is int, "연산 카운터는 정수여야 함: " + key)
    return {k: v for k, v in cost.items() if k not in ALIASES}


def check_chain(events: list[dict], status: dict) -> None:
    previous = "0" * 64
    require(len(events) == status["event_count"], "이벤트 수 불일치")
    for seq, event in enumerate(events):
        require(set(event) == {"seq", "previous", "event", "payload", "sha256"}, "이벤트 필드 불일치")
        body = {k: event[k] for k in ("seq", "previous", "event", "payload")}
        require(event["seq"] == seq and event["previous"] == previous
                and sha(canonical(body)) == event["sha256"], "이벤트 chain 불일치")
        previous = event["sha256"]
    require(previous == status["event_head"], "이벤트 head 불일치")


def count_rows(rows: list[dict]) -> dict:
    return dict(attempts=len(rows), correct=sum(r["assessment"]["correct"] is True for r in rows),
        incorrect=sum(r["assessment"]["correct"] is False for r in rows),
        unresolved=sum(r["assessment"]["correct"] is None for r in rows),
        strict_correct=sum(r["assessment"]["correct"] is True and r["assessment"]["proof_valid"]
                           and r["assessment"]["assumption_correct"] is True for r in rows),
        wrong_stable=sum(r["assessment"]["wrong_stable"] for r in rows),
        circuit_reuse=sum(bool(r["decision"]["circuit_ids"]) for r in rows))


def examine(run: Path, repo: Path) -> dict:
    manifest_raw = read(safe(run, "manifest.json"))
    manifest = loads(manifest_raw)
    require(manifest["schema"] == "hcr-run-manifest-r02" and manifest["state"] == "complete", "완료된 R0.2 run 필요")
    require(inventory(run, {"manifest.json"}) == set(manifest["files"]), "원본 run 파일 누락/추가")
    run_bytes = {"manifest.json": manifest_raw}
    for name, expected in manifest["files"].items():
        raw = read(safe(run, name))
        require(sha(raw) == expected, "run 해시 불일치: " + name)
        run_bytes[name] = raw
    require(sum(map(len, run_bytes.values())) <= MAX_BUNDLE, "run 전체 크기 한도 초과")
    plan, status = loads(run_bytes["plan.json"]), loads(run_bytes["status.json"])
    require(plan["schema"] == "hcr-plan-r02" and plan["protocol"] == "r02-authored-path-motifs-v1", "계획/protocol 불일치")
    require(status["state"] == "complete" and plan["evaluation_labels_passed_to_engine"] is False, "완료/평가 경계 불일치")
    require(sha(canonical(plan["config"])) == plan["config_signature"], "설정 서명 불일치")
    source_bytes = {}
    expected_sources = {p.relative_to(repo).as_posix() for p in (repo / "src/hcr").rglob("*.py")}
    expected_sources |= {"hcr.py", "configs/r01.toml", "configs/r02.toml"}
    require(expected_sources == set(plan["source_hashes"]), "기록된 실행 소스의 파일 집합과 현재 소스가 다름")
    for name, expected in plan["source_hashes"].items():
        raw = read(safe(repo, name))
        require(sha(raw) == expected, "당시 실행 소스와 다름; 과거 hash를 수정하지 말 것: " + name)
        source_bytes[name] = raw
    require(sum(map(len, source_bytes.values())) <= MAX_BUNDLE, "소스 크기 한도 초과")
    events = [loads(line) for line in run_bytes["events.jsonl"].splitlines() if line.strip()]
    rows = [loads(line) for line in run_bytes["episodes.jsonl"].splitlines() if line.strip()]
    summary = loads(run_bytes["summary.json"])
    check_chain(events, status)
    require(len(rows) == status["episode_records"], "판단 행 수 불일치")
    grouped, original_costs = defaultdict(list), defaultdict(Counter)
    rowmap = {r["decision"]["id"]: r for r in rows}
    require(len(rowmap) == len(rows), "중복 decision id")
    for row in rows:
        key = row["phase"] + "/" + row["arm"]
        canonical_cost(row["decision"]["cost"])
        grouped[key].append(row)
        original_costs[key].update(row["decision"]["cost"])
        original_costs[key]["verification_checks"] += row["assessment"]["verification_checks"]
        require(row["memory_before"] == row["memory_after_inference"], "추론이 memory를 변경함")
    require(summary["groups"] == {k: count_rows(v) for k, v in grouped.items()}, "요약 판단 집계 불일치")
    require(summary["costs"] == {k: dict(v) for k, v in original_costs.items()}, "요약 비용 집계 불일치")
    learning_costs = Counter()
    trace_decisions = {}
    for event in events:
        p = event["payload"]
        if event["event"] == "r02_decision":
            require(p["id"] not in trace_decisions, "중복 trace decision")
            trace_decisions[p["id"]] = p
        if event["event"] == "r02_memory_updated":
            canonical_cost(p["cost"])
            learning_costs.update(p["cost"])
    require(trace_decisions == {k: r["decision"] for k, r in rowmap.items()}, "trace/episode 판단 불일치")
    require(summary["learning_costs"] == dict(learning_costs), "학습 비용 집계 불일치")
    require(summary["event_counts"] == dict(Counter(e["event"] for e in events)), "이벤트 종류 집계 불일치")
    return dict(plan=plan, status=status, manifest=manifest, rows=rows, events=events,
                summary=summary, run_bytes=run_bytes, source_bytes=source_bytes)


def pattern_id(circuit: dict) -> str:
    return "pattern-" + sha(canonical(circuit["pattern"]))[:24]


def analyze(data: dict) -> dict:
    rows, events = data["rows"], data["events"]
    rowmap = {r["decision"]["id"]: r for r in rows}
    networks, network_costs = {}, defaultdict(Counter)
    learning_by_decision, patches, candidates, requested = {}, [], [], []
    current_memory, memory_at = None, {}
    for event in events:
        p, name = event["payload"], event["event"]
        if name == "r02_engine_created":
            current_memory = p["memory_document"]
        elif name == "r02_attempt_started":
            memory_at[p["decision_id"]] = current_memory
        elif name == "r02_network":
            networks[p["network_id"]] = p
        elif name == "r02_tick":
            n = networks[p["network_id"]]
            nc = network_costs[(p["decision_id"], n["kind"])]
            nc["kernel_ticks"] += 1
            nc["signal_transmissions"] += sum(n["top_down"] or link["kind"] != "top_down" for link in n["program"]["links"])
            nc["group_updates"] += len(n["program"]["groups"])
        elif name == "r02_pool_result":
            did = p["decision_id"]
            memory = memory_at[did]
            for a in p["activations"]:
                cid = a["circuit_id"]
                matches = [c for c in memory["circuits"] if pattern_id(c) == cid]
                require(len(matches) == 1, "후보 회로의 memory 대응 누락")
                c = matches[0]
                candidates.append(dict(decision_id=did, network_id=p["network_id"],
                    phase=rowmap[did]["phase"], arm=rowmap[did]["arm"], case=rowmap[did]["case"],
                    circuit_id=cid, pattern_length=len(c["pattern"]["relations"]), strength=c["strength"],
                    failures=c["failures"], evidence_count=len(c["evidence_episodes"]),
                    balance=len(c["evidence_episodes"]) / (len(c["evidence_episodes"]) + 1),
                    activation=a["activation"], prior=a["prior"], mismatch=a["mismatch"], eligible=a["eligible"],
                    binding=a["binding"], present_in_final_decision=cid in rowmap[did]["decision"]["circuit_ids"]))
        elif name == "r02_memory_updated":
            current_memory = p["memory_document"]
            did = p["patch"]["decision_id"]
            learning_by_decision[did] = canonical_cost(p["cost"])
            patches.append(dict(decision_id=did, phase=rowmap[did]["phase"], arm=rowmap[did]["arm"],
                                patch=p["patch"], memory_after=p["memory_after"]))
        elif name == "r02_observation_requested":
            requested.append(p)
    costs, pair_rows = [], []
    for row in rows:
        d, a = row["decision"], row["assessment"]
        cost = canonical_cost(d["cost"])
        for field in ("kernel_ticks", "signal_transmissions", "group_updates"):
            require(sum(network_costs[(d["id"], k)][field] for k in ("pool", "decision")) == cost[field], "신호 역할별 카운터 불일치")
        costs.append(dict(phase=row["phase"], arm=row["arm"], case=row["case"], decision_id=d["id"],
                          attempt=d["attempt"], value=d["value"], correct=a["correct"],
                          primitive_D=d["proof"]["primitive_depth"], **cost,
                          external_verification_checks=a["verification_checks"],
                          pool_ticks=network_costs[(d["id"], "pool")]["kernel_ticks"],
                          decision_ticks=network_costs[(d["id"], "decision")]["kernel_ticks"],
                          pool_signals=network_costs[(d["id"], "pool")]["signal_transmissions"],
                          decision_signals=network_costs[(d["id"], "decision")]["signal_transmissions"]))
    for case in sorted({r["case"] for r in rows if r["phase"] == "familiarity"}):
        cs = [r for r in rows if r["phase"] == "familiarity" and r["case"] == case and r["arm"] == "cold"]
        ws = [r for r in rows if r["phase"] == "familiarity" and r["case"] == case and r["arm"] == "warm"]
        require(len(cs) == len(ws) == 1, "cold/warm 일대일 쌍 누락")
        c, w = cs[0], ws[0]
        require(c["observation"] == w["observation"] and c["external_truth"] == w["external_truth"], "쌍의 입력/정답 불일치")
        cc, wc = canonical_cost(c["decision"]["cost"]), canonical_cost(w["decision"]["cost"])
        pair_rows.append(dict(case=case, cold_correct=c["assessment"]["correct"], warm_correct=w["assessment"]["correct"],
            cold_D=c["decision"]["proof"]["primitive_depth"], warm_D=w["decision"]["proof"]["primitive_depth"],
            **{"delta_" + k: wc[k] - cc[k] for k in cc}))
    packets = {}
    for name in ("memory_after_training.json", "memory_after_adaptation.json", "memory_training_3.json", "memory_training_9.json"):
        packet = loads(data["run_bytes"][name])
        require(sha(canonical(packet["document"])) == packet["sha256"], "memory packet 해시 불일치")
        packets[name] = packet
    delta = []
    before = {pattern_id(c): c for c in packets["memory_after_training.json"]["document"]["circuits"]}
    after = {pattern_id(c): c for c in packets["memory_after_adaptation.json"]["document"]["circuits"]}
    for cid in sorted(set(before) | set(after)):
        b, a = before.get(cid), after.get(cid)
        delta.append(dict(circuit_id=cid, before_strength=b["strength"] if b else None,
            after_strength=a["strength"] if a else None, before_failures=b["failures"] if b else None,
            after_failures=a["failures"] if a else None, before_active=b["active"] if b else None,
            after_active=a["active"] if a else None,
            before_evidence=len(b["evidence_episodes"]) if b else None, after_evidence=len(a["evidence_episodes"]) if a else None))
    return dict(schema="hcr-r02-baseline-analysis-v1", groups=data["summary"]["groups"],
        costs=costs, familiarity_pairs=pair_rows, memory_delta=delta, candidate_trace=candidates,
        learning_by_decision=learning_by_decision, learning_patches=patches, observation_requests=requested,
        original_adaptation=data["summary"]["adaptation"],
        boundaries=dict(numerical_tick_replay_performed=False, inference_performed=False,
                        aggregation_and_hash_checks_performed=True, hypothesis_proved=False),
        unmeasured=["원 실행의 엔진 생성/메모리 load wall time", "원 실행의 전체 실험 end-to-end wall time",
                    "개별 입력 측정의 실제 자원 비용", "원 실행 당시 RAM memory와 save/load memory의 행동 동등성"],
        cost_note="별칭 제외. pool/decision 분해는 전체 카운터의 내역이므로 다시 합산하지 않는다. 서로 다른 단위의 단일 비용점수를 만들지 않는다.")


def render(report: dict) -> str:
    lines = ["# R0.2 원시 실행 기준선 분석", "", "새 추론 없이 기존 run을 읽어 만든 집계다. 수치 tick 재연산 감사와는 구분한다.", "",
             "## Familiarity — warm − cold", "", "| 사례 | 정답 cold/warm | primitive D | 확장 Δ | binding Δ | 신호 Δ | tick Δ | infer wall Δ(s) |",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    for p in report["familiarity_pairs"]:
        lines.append(f'| {p["case"]} | {p["cold_correct"]}/{p["warm_correct"]} | {p["cold_D"]}/{p["warm_D"]} | '
                     f'{p["delta_expansions"]} | {p["delta_binding_operations"]} | {p["delta_signal_transmissions"]} | '
                     f'{p["delta_kernel_ticks"]} | {p["delta_wall_seconds"]:.9f} |')
    lines += ["", "음수는 해당 항목 감소다. 이 표만으로 end-to-end 가속을 주장하지 않는다.", "",
              "## 저장 전후 회로 상태", "", "| 회로 | 강도 전/후 | 실패 전/후 | 활성 전/후 |", "|---|---|---|---|"]
    for p in report["memory_delta"]:
        lines.append(f'| {p["circuit_id"]} | {p["before_strength"]}/{p["after_strength"]} | '
                     f'{p["before_failures"]}/{p["after_failures"]} | {p["before_active"]}/{p["after_active"]} |')
    lines += ["", "## 해석 경계", "",
              "retention/reload의 재오답은 그대로 보존한다. candidate_trace.json의 후보·선택·prior와 learning_patches를 연결해 읽는다. 동반된 상태 변화는 관측이며, 원인 분리는 별도 paired probe가 필요하다.", "",
              "비용은 costs.csv의 판단별 카운터, analysis.json의 learning_by_decision으로 분리된다. training3/9은 해당 arm의 최초 판단·수정 판단·feedback 비용을 각각 비교한다.", "",
              "원 실행에서 측정하지 않은 항목:", *["- " + s for s in report["unmeasured"]], ""]
    return "\n".join(lines)


def verify_bundle(root: Path) -> dict:
    manifest = loads(read(safe(root, "bundle_manifest.json")))
    require(manifest["schema"] == "hcr-r02-baseline-bundle-v1" and manifest["state"] == "complete", "완료된 기준선 bundle 필요")
    require(inventory(root, {"bundle_manifest.json"}) == set(manifest["files"]), "bundle 파일 누락/추가")
    for name, expected in manifest["files"].items():
        require(sha(read(safe(root, name))) == expected, "bundle 해시 불일치: " + name)
    return manifest


def collect(repo: Path, run: Path, out: Path) -> dict:
    require(not linked(repo) and not linked(run), "입력 루트 링크 금지")
    repo, run, out = repo.resolve(), run.resolve(), out.resolve()
    require(not out.exists() and not out.is_relative_to(repo) and not out.is_relative_to(run),
            "출력은 기존 저장소/run 밖의 새 폴더여야 한다")
    data = examine(run, repo)
    report = analyze(data)
    out.mkdir(parents=True, exist_ok=False)
    try:
        for sub, values in (("source", data["source_bytes"]), ("run", data["run_bytes"])):
            for name, raw in values.items():
                dest = safe(out, sub + "/" + name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as stream:
                    stream.write(raw)
        write_json(out / "analysis.json", report)
        write_json(out / "candidate_trace.json", report["candidate_trace"])
        write_csv(out / "costs.csv", report["costs"])
        write_csv(out / "familiarity_pairs.csv", report["familiarity_pairs"])
        write_csv(out / "memory_delta.csv", report["memory_delta"])
        with (out / "analysis.ko.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(render(report))
        receipt = dict(schema="hcr-r02-baseline-capture-v1", collected_at_utc=datetime.now(timezone.utc).isoformat(),
            source_files=len(data["source_bytes"]), run_files=len(data["run_bytes"]),
            source_plan_sha256=sha(data["run_bytes"]["plan.json"]),
            run_manifest_sha256=sha(data["run_bytes"]["manifest.json"]),
            repository_modified=False, original_run_modified=False, inference_executed=False,
            project_tests_executed=False, independent_numerical_audit_executed=False,
            integrity_and_aggregation_checked=True, remote_head_verified=False)
        # 수집 중 입력 변경도 거부한다. 원본/과거 plan은 절대로 수정하지 않는다.
        for root, values in ((run, data["run_bytes"]), (repo, data["source_bytes"])):
            for name, raw in values.items():
                require(read(safe(root, name)) == raw, "수집 중 입력 변경 감지: " + name)
        require(inventory(run) == set(data["run_bytes"]), "수집 중 run 파일 집합 변경")
        write_json(out / "capture_receipt.json", receipt)
        files = {name: sha(read(safe(out, name))) for name in sorted(inventory(out))}
        write_json(out / "bundle_manifest.json", dict(schema="hcr-r02-baseline-bundle-v1", state="complete", files=files))
        verify_bundle(out)
        return dict(state="complete", output=str(out), **receipt)
    except BaseException as error:
        if not (out / "bundle_manifest.json").exists():
            write_json(out / "FAILED.json", dict(state="failed", error=str(error)))
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--run", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify-bundle", type=Path, help="기준선 bundle 해시만 다시 확인")
    args = parser.parse_args(argv)
    try:
        if args.verify_bundle:
            require(args.run is None and args.out is None, "verify-bundle과 수집 인수 혼용 금지")
            result = verify_bundle(args.verify_bundle.resolve())
            print(json.dumps(dict(state="complete", integrity_verified=True, files=len(result["files"])), ensure_ascii=False))
        else:
            require(args.run is not None and args.out is not None, "--run과 --out 필요")
            run = args.run if args.run.is_absolute() else args.repo / args.run
            print(json.dumps(collect(args.repo, run, args.out), ensure_ascii=False, indent=2))
        return 0
    except (BaselineError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(state="failed", error=type(error).__name__ + ": " + str(error)), ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
