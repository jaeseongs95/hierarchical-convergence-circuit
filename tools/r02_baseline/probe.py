#!/usr/bin/env python3
"""EXP-09: 동결된 R0.2 소스로 persistence/memory/측정/routing의 기여를 짝지어 비교한다.
기본은 계획 확인뿐이다. --execute를 직접 지정해야 새 추론을 실행한다.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter

# 수집 도구는 표준 라이브러리만 사용한다. HCR import는 execute() 내부에 한정한다.
from collect import (BaselineError, require, loads, read, canonical, sha, safe, inventory,
                     verify_bundle, canonical_cost, check_chain, write_json, write_csv)


def semantic_decision(raw: dict) -> dict:
    """같은 공개 입력/같은 memory의 행동 비교. ID와 wall time만 제외한다."""
    out = deepcopy(raw)
    out.pop("id")
    out["cost"].pop("wall_seconds")
    return out


def make_plan(bundle: Path) -> dict:
    manifest = verify_bundle(bundle)
    original = loads(read(bundle / "run/plan.json"))
    return dict(schema="hcr-r02-exp09-plan-v1", protocol="exp09-baseline-paired-v1",
        baseline_bundle_manifest_sha256=sha(read(bundle / "bundle_manifest.json")),
        original_plan_sha256=sha(read(bundle / "run/plan.json")),
        source_hashes=original["source_hashes"], config=original["config"],
        config_signature=original["config_signature"],
        training_counts=[3, 6, 9],
        matrix=dict(memory=["before", "after"], measurement=["weak", "measured"], circuits=[True, False]),
        persistence="새로 재현한 adaptation 직후 RAM memory와 그 객체의 save/load 쌍. 원 사용자 세션 RAM을 복구한 것이 아님.",
        fixed_input="각 짝은 동일한 공개 입력과 외부 truth. 새 episode ID는 조건을 담지 않는 고정 식별자.",
        learning="frozen matrix에서는 feedback 없음. trajectory에서만 기존 외부 feedback/요청 측정 계약 사용.",
        equality_exclusions=["decision.id", "decision.cost.wall_seconds", "도구가 별도로 측정한 wall time"],
        exclusions_not_allowed=["proof", "state", "primitive_depth", "circuit_ids", "memory_version", "operation counters"],
        expected_success_not_forced=True, output_is_development_diagnostic=True,
        original_protocol_audit_required=True, full_independent_probe_audit_available=False,
        engine_execution_requested=False, engine_version="0.2.0", hypothesis_proved=False,
        preserved_files=len(manifest["files"]))


def execute(bundle: Path, out: Path, plan: dict) -> dict:
    require(not out.exists() and not out.is_relative_to(bundle), "probe 출력은 bundle 밖의 새 폴더여야 함")
    source = bundle / "source"
    # bundle hash 외에도 원 plan의 source hash와 현재 snapshot을 다시 연결한다.
    for name, expected in plan["source_hashes"].items():
        require(sha(read(safe(source, name))) == expected, "snapshot 소스 불일치: " + name)
    sys.dont_write_bytecode = True
    require("hcr" not in sys.modules, "다른 HCR 모듈이 이미 로드됨; 별도 프로세스에서 실행")
    sys.path.insert(0, str(source / "src"))
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.runtime import AdaptiveEngine
    from hcr.model import Feedback, Mode
    from hcr.trace import Trace
    from hcr.tasks.toy_world import World
    from hcr.evaluation.reference import assess
    from hcr.evaluation.adaptive_audit import verify_run
    import hcr
    require(Path(hcr.__file__).resolve().is_relative_to(source.resolve()), "의도하지 않은 HCR import 경로")
    config = codec.adaptive_config_from(plan["config"])
    source_audit = verify_run(bundle / "run", check_source=True)
    require(source_audit["verified"] is True and source_audit["differences"] == [], "원 run 독립 감사 실패")
    original_rows = [loads(line) for line in read(bundle / "run/episodes.jsonl").splitlines() if line.strip()]
    conflict_rows = [r for r in original_rows if r["phase"] == "misconvergence" and r["arm"] == "full"]
    require(conflict_rows, "원 run에 full conflict 없음")
    conflict_rows.sort(key=lambda r: r["decision"]["attempt"])
    initial, final = conflict_rows[0], conflict_rows[-1]
    require(final["decision"]["attempt"] > initial["decision"]["attempt"], "강한 측정 대조를 위한 실제 revision이 없음; 값을 만들어 채우지 않음")
    require(initial["external_truth"] == final["external_truth"], "revision 간 외부 truth 변경")
    weak_raw, strong_raw = deepcopy(initial["observation"]), deepcopy(final["observation"])
    # 이는 통제된 새 episode 입력이다. 실제 revision을 요청한 것처럼 꾸미지 않는다.
    for raw in (weak_raw, strong_raw):
        raw["episode_id"], raw["revision"] = "e900001", 0
    require([(e["id"], e["source"], e["target"]) for e in weak_raw["edges"]]
            == [(e["id"], e["source"], e["target"]) for e in strong_raw["edges"]], "입력 topology 불일치")
    require(weak_raw != strong_raw, "측정 조건이 같음")
    truth = tuple(sorted(initial["external_truth"].items()))
    weak = World(codec.observation_from(weak_raw), truth)
    strong = World(codec.observation_from(strong_raw), truth)
    retest_weak = replace(weak, observation=replace(weak.observation, episode_id="e900002"))
    retest_strong = replace(strong, observation=replace(strong.observation, episode_id="e900002"))
    memory = {
        "before": AdaptiveMemory.load(bundle / "run/memory_after_training.json", config),
        "after": AdaptiveMemory.load(bundle / "run/memory_after_adaptation.json", config),
        "training_3": AdaptiveMemory.load(bundle / "run/memory_training_3.json", config),
        "training_9": AdaptiveMemory.load(bundle / "run/memory_training_9.json", config),
    }
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "plan.json", dict(plan, engine_execution_requested=True,
        tool_source_hashes={p.name: sha(read(p)) for p in (Path(__file__), Path(__file__).with_name("collect.py"))}))
    write_json(out / "original_run_audit.json", source_audit)
    trace = Trace(out / "events.jsonl")
    rows, initializations, trajectories, matrix = [], [], {}, {}
    started = perf_counter()

    def make_engine(mem, key, **switches):
        t = perf_counter()
        cloned = deepcopy(mem)
        copy_seconds = perf_counter() - t
        t = perf_counter()
        engine = AdaptiveEngine(config, cloned, trace, **switches)
        initializations.append(dict(key=key, memory_digest=mem.digest,
                                   memory_copy_seconds=copy_seconds, engine_init_seconds=perf_counter() - t))
        return engine

    def record(engine, world, phase, arm, mode=Mode.FROZEN_EVAL, revision_of=None):
        before = engine.memory.digest
        t = perf_counter()
        decision = engine.infer(world.observation, mode, revision_of=revision_of)
        infer_call_seconds = perf_counter() - t
        require(before == engine.memory.digest, "추론이 memory 변경")
        raw = codec.plain(decision)
        canonical_cost(raw["cost"])
        t = perf_counter()
        assessment = assess(decision, world.observation, dict(world.hidden))
        assessment_seconds = perf_counter() - t
        trace.emit("r02_external_assessment", dict(decision_id=decision.id, assessment=codec.plain(assessment)))
        row = dict(phase=phase, arm=arm, observation=codec.plain(world.observation),
                   external_truth=dict(world.hidden), decision=raw, assessment=codec.plain(assessment),
                   memory_before=before, memory_after_inference=engine.memory.digest,
                   infer_call_seconds=infer_call_seconds, external_assessment_seconds=assessment_seconds)
        rows.append(row)
        with (out / "episodes.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(codec.dumps(row) + "\n")
        return decision, assessment, row

    def adapt(mem, key):
        engine = make_engine(mem, key)
        item, prior, related = weak, None, []
        while True:
            decision, assessment, row = record(engine, item, "adaptation", key, Mode.ADAPT, prior)
            related.append(row)
            engine.feedback(Feedback("f-" + decision.id, decision.id, decision.observation_digest,
                assessment.correct, assessment.proof_valid and assessment.assumption_correct is True))
            if assessment.correct is not False:
                break
            request = engine.request_revision(decision.id)
            if request is None:
                break
            obs = item.measure(request)
            trace.emit("r02_measurement_delivered", dict(request=codec.plain(request), observation=codec.plain(obs)))
            item, prior = replace(item, observation=obs), decision.id
        trajectories[key] = related
        return engine

    try:
        # A: 사용자 세션의 RAM을 가정하지 않고 지금 재현한 live 객체를 정확히 round-trip한다.
        live = adapt(memory["before"], "persistence_replay")
        live_digest = live.memory.digest
        t = perf_counter()
        live.memory.save(out / "live_after_adaptation.json")
        save_seconds = perf_counter() - t
        t = perf_counter()
        restored = AdaptiveMemory.load(out / "live_after_adaptation.json", config)
        load_seconds = perf_counter() - t
        require(live.memory.digest == restored.digest == live_digest, "live save/load digest 불일치")
        _, _, direct = record(make_engine(live.memory, "persistence/direct"), retest_weak, "persistence", "direct")
        _, _, reload_row = record(make_engine(restored, "persistence/reload"), retest_weak, "persistence", "reload")
        behavior_equal = semantic_decision(direct["decision"]) == semantic_decision(reload_row["decision"])
        persistence = dict(memory_equal=True, behavior_equal=behavior_equal,
            assessment_equal=direct["assessment"] == reload_row["assessment"],
            both_correct=[direct["assessment"]["correct"], reload_row["assessment"]["correct"]],
            save_seconds=save_seconds, load_seconds=load_seconds,
            note="동등성과 정답은 독립 판정이다. 둘 다 오답이어도 동등할 수 있다.")
        # B/C: 같은 입력에서 memory 변화와 정보량, 회로 사용 여부를 각각 바꾼다.
        for mem_name in ("before", "after"):
            for profile, item in (("weak", retest_weak), ("measured", retest_strong)):
                for circuits in (True, False):
                    key = mem_name + "/" + profile + "/" + ("circuits" if circuits else "graph_only")
                    engine = make_engine(memory[mem_name], "factorial/" + key, use_circuits=circuits)
                    _, _, row = record(engine, item, "factorial", key)
                    matrix[key] = row
        # E: 이미 존재하는 3/6/9회 checkpoint를 동일한 새 conflict에 적용한다.
        for count in (3, 6, 9):
            mem = memory["before"] if count == 6 else memory["training_" + str(count)]
            adapt(mem, "training_" + str(count))
        trace.close()
        events = trace.records
        check_chain(events, dict(event_count=trace.count, event_head=trace.head))
        learning = {e["payload"]["patch"]["decision_id"]: canonical_cost(e["payload"]["cost"])
                    for e in events if e["event"] == "r02_memory_updated"}
        trajectory_summary = {}
        for key, group in trajectories.items():
            costs = {}
            for row in group:
                for field, value in canonical_cost(row["decision"]["cost"]).items():
                    costs[field] = costs.get(field, 0) + value
            learning_totals = {}
            for row in group:
                for field, value in learning.get(row["decision"]["id"], {}).items():
                    learning_totals[field] = learning_totals.get(field, 0) + value
            trajectory_summary[key] = dict(attempts=len(group), initial=group[0]["assessment"],
                final=group[-1]["assessment"], inference_cost=costs, feedback_cost=learning_totals)
        factorial = []
        for key, row in matrix.items():
            factorial.append(dict(condition=key, value=row["decision"]["value"], correct=row["assessment"]["correct"],
                proof_valid=row["assessment"]["proof_valid"], wrong_stable=row["assessment"]["wrong_stable"],
                circuit_ids=";".join(row["decision"]["circuit_ids"]),
                primitive_D=row["decision"]["proof"]["primitive_depth"], **canonical_cost(row["decision"]["cost"])))
        summary = dict(schema="hcr-r02-exp09-summary-v1", execution_complete=True,
            inferences=len(rows), persistence=persistence, factorial=factorial,
            adaptation=trajectory_summary, initializations=initializations,
            source_run_independent_audit_passed=True, probe_hash_chain_checked=True,
            full_independent_probe_audit_performed=False, hypothesis_proved=False,
            measured_probe_seconds=perf_counter() - started,
            limitations=["새 paired 진단은 원 r02 demo protocol과 달라 원 독립 auditor 전체의 적용 대상이 아니다.",
                         "판정은 기존 외부 proof/reference를 사용한다. 새 진단의 kernel 수치 전량 재검산은 수행하지 않는다.",
                         "기존 checkpoint 재사용이므로 신규 학습 corpus/일반화 표본 실험이 아니다.",
                         "세기 비교는 단일 weight뿐 아니라 경험 수/balance/다른 회로의 가용성도 달라진다.",
                         "계측 wall time은 trace/검증/직렬화 오버헤드가 포함된 해당 호출의 관측값이다."])
        write_json(out / "summary.json", summary)
        write_csv(out / "factorial.csv", factorial)
        write_csv(out / "initializations.csv", initializations)
        text = ["# EXP-09 짝지은 기준선 진단", "",
                "새 추론 실행 결과다. 기존 R0.2 run을 덮어쓰지 않는다.", "",
                "## 저장·복원", "",
                f"memory 동등: {persistence['memory_equal']}; 행동 동등: {behavior_equal}; 두 조건 정답 여부: {persistence['both_correct']}", "",
                "## memory × 측정 × routing", "", "| 조건 | 출력 | 정답 | 안정 오답 | 회로 | 확장 | 신호 |", "|---|---|---|---|---|---:|---:|"]
        for r in factorial:
            text.append(f"| {r['condition']} | {r['value']} | {r['correct']} | {r['wrong_stable']} | {r['circuit_ids']} | {r['expansions']} | {r['signal_transmissions']} |")
        text += ["", "## 해석 경계", "", *["- " + s for s in summary["limitations"]], ""]
        with (out / "summary.ko.md").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(text))
        verify_bundle(bundle)  # inference 과정에서 동결본이 바뀌지 않았는지도 검사한다.
        file_hashes = {name: sha(read(safe(out, name))) for name in sorted(inventory(out))}
        write_json(out / "manifest.json", dict(schema="hcr-r02-exp09-manifest-v1", state="complete",
            source_bundle_manifest_sha256=plan["baseline_bundle_manifest_sha256"], files=file_hashes))
        return summary
    except BaseException as error:
        trace.close()
        if not (out / "manifest.json").exists():
            write_json(out / "FAILED.json", dict(state="failed", error=str(error), inferences=len(rows)))
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--execute", action="store_true", help="동결된 소스로 실제 새 추론/측정/feedback 실행")
    args = parser.parse_args(argv)
    try:
        bundle = args.bundle.resolve()
        plan = make_plan(bundle)
        if not args.execute:
            print(canonical(dict(state="planned", plan=plan, engine_executed=False)).decode("utf-8"))
        else:
            require(args.out is not None, "실행 시 --out 필요")
            summary = execute(bundle, args.out.resolve(), plan)
            print(canonical(dict(state="complete", inferences=summary["inferences"],
                persistence=summary["persistence"], output=str(args.out.resolve()),
                full_independent_probe_audit_performed=False)).decode("utf-8"))
        return 0
    except (BaselineError, OSError, ValueError, KeyError, TypeError) as error:
        print(canonical(dict(state="failed", error=type(error).__name__ + ": " + str(error))).decode("utf-8"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
