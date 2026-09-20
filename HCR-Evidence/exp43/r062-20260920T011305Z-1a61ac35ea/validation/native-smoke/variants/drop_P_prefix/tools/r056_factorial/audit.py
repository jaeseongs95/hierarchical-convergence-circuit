"""Independent R056 replay, provenance audit, and drive-allocation comparisons."""
from __future__ import annotations

import argparse
from math import isfinite
from pathlib import Path
import sys

from hcr.model import Config
from tools.r050_review_boundary.audit import FORBIDDEN as R050_FORBIDDEN
from tools.r050_review_boundary.common import (
    SRC_TREE, TEST_TREE, dump, files, fingerprint, git_tree, load, publish, require, sha, unseal,
)
from tools.r053_feedback.audit import _close, _verify_parent, verify_trajectory
from tools.r054_links.audit import _feedback_id_map


SPEC_FINGERPRINT = "14b1a0d9c411a23f5804f7d964829079b351688afb31a7d1d927c4773027db4e"
CONDITIONS = {
    "startstrong": ([1.0, 0.02], {"e:0": 4.0, "e:1": 0.08, "goal": 0.0}),
    "start_raise_weak": ([1.0, 0.265], {"e:0": 4.0, "e:1": 1.06, "goal": 0.0}),
    "start_lower_strong": ([0.755, 0.02], {"e:0": 3.02, "e:1": 0.08, "goal": 0.0}),
    "startlean": ([0.755, 0.265], {"e:0": 3.02, "e:1": 1.06, "goal": 0.0}),
    "goalstrong": ([0.02, 1.0], {"e:0": 0.08, "e:1": 4.0, "goal": 0.0}),
    "goal_raise_weak": ([0.265, 1.0], {"e:0": 1.06, "e:1": 4.0, "goal": 0.0}),
    "goal_lower_strong": ([0.02, 0.755], {"e:0": 0.08, "e:1": 3.02, "goal": 0.0}),
    "goallean": ([0.265, 0.755], {"e:0": 1.06, "e:1": 3.02, "goal": 0.0}),
}
ORIGINAL_DRIVES = {"e:0": 4.0, "e:1": 0.08, "goal": 0.0}
MASK_REMOVALS = {"full": (), "drop_P_prefix": ("P_prefix",)}
FEEDBACK_LINKS = {
    "E_start": ("p:0:0", "e:0"),
    "E_goal": ("p:0:1", "e:1"),
    "P_prefix": ("p:0:1", "p:0:0"),
    "P_goal": ("goal", "p:0:1"),
}
MATRICES = {
    "start": [["startstrong", "start_raise_weak"], ["start_lower_strong", "startlean"]],
    "goal": [["goalstrong", "goal_raise_weak"], ["goal_lower_strong", "goallean"]],
}
BRIDGE_CONDITIONS = ["startstrong", "startlean", "goallean", "goalstrong"]
STABLE_STATUSES = ("stable_decision", "stable_ambiguous")
TOLERANCE = {"abs_tol": 1e-12, "rel_tol": 1e-12}
THRESHOLD = 0.5
ABSTENTION_BAND = 1e-6
FORBIDDEN = R050_FORBIDDEN | {
    "tools.r052_array_roles.worker",
    "tools.r053_feedback.worker",
    "tools.r054_links.worker",
    "tools.r055_allocation.worker",
    "tools.r056_factorial.worker",
}
HISTORICAL_MANIFESTS = {
    "R055": "f873feb80782eb26ff8adaad01d4a2baf846f4bae8317600ae8d8c61d599befa",
    "R050": "cbd6f138bc8f2318ae5546c0efffe0ce7b4a17bfaab4a0feebbcf7bd33e6d92a",
    "R051": "e705066ade1d954c936aa582ed44a4b0d9a8d776d76fb06e61bee102788088df",
    "R052": "7afe672c30263c87c5d5ca10a17016de8a6ecba4f7894a8a8d61b9eb8accbbba",
    "R053": "3247d77ca829d76ea39ff0f210e8a8ad8e7bd50d1636cb717ea739a81ab66aeb",
    "R054": "88e9f9dae6facc64f424e244cdd5e1001dcabb7460fece81f87b520a5c4c39d3",
}


def _require_inventory(root: Path, expected: dict[str, str], message: str) -> None:
    require(files(root) == expected, message)


def _verify_historical_sources(source: Path) -> None:
    for version, expected in HISTORICAL_MANIFESTS.items():
        path = source / f"{version}_MANIFEST.json"
        require(sha(path.read_bytes().replace(b"\r\n", b"\n")) == expected,
                f"Historical manifest changed: {version}")
        manifest = load(path)
        for name, digest in manifest["files"].items():
            require(sha((source / name).read_bytes().replace(b"\r\n", b"\n")) == digest,
                    f"Protected historical source changed: {name}")


def validate_spec(spec: dict) -> None:
    """Reject a consistently resealed change to the frozen R056 contract."""
    require(fingerprint(spec) == SPEC_FINGERPRINT, "Exact frozen R056 spec")
    require(spec["frozen_before_research_execution"] is True, "Spec was not frozen")
    require(spec["numeric_comparison"] == TOLERANCE, "Numeric comparison drift")
    require(spec["initial_activation"] == 0.5, "Initial activation drift")
    require(spec["program_parent"] == "study/raw/r052-c001/start_edge.json",
            "Program parent drift")
    require(spec["conditions"] == [
        {"id": identity, "input_pair": pair, "drives": drives}
        for identity, (pair, drives) in CONDITIONS.items()
    ], "Condition matrix")
    require(spec["masks"] == [
        {"id": mask, "remove": list(removed)} for mask, removed in MASK_REMOVALS.items()
    ], "Mask matrix")
    require(spec["feedback_links"] == [
        {"id": identity, "source": pair[0], "target": pair[1]}
        for identity, pair in FEEDBACK_LINKS.items()
    ], "Feedback identities")
    require(len(spec["parent_files"]) == 10 and len(spec["anchor_files"]) == 12,
            "Pinned evidence counts")
    require(spec["implementation_validation_conditions"] == BRIDGE_CONDITIONS
            and spec["research_conditions"] == list(CONDITIONS), "Purpose matrices")
    require(spec["bridge_conditions"] == BRIDGE_CONDITIONS, "Bridge matrix")
    require(spec["factorial_matrices"] == MATRICES, "Factorial matrix orientation")
    require(spec["contrast_measures"] == ["full_goal", "dropout_goal", "delta_goal"],
            "Factorial measures")
    require(spec["drive_mapping"] == {
        "scale": 4.0, "strong_levels": [4.0, 3.02], "weak_levels": [.08, 1.06],
        "edge_drive_totals": [4.08, 5.06, 3.10, 4.08],
        "unchanged_goal_drive": 0.0, "fixed_total": False,
    }, "Drive mapping drift")
    require(spec["endpoint_rule"] == {
        "stable_statuses": list(STABLE_STATUSES), "threshold": THRESHOLD,
        "abstention_band": ABSTENTION_BAND,
        "low": "goal < threshold - abstention_band",
        "high": "goal > threshold + abstention_band",
        "otherwise": "inconclusive", "not_an_error_bound": True,
    }, "Endpoint rule drift")


def verify_record(record: dict, condition: dict, mask: dict, original: dict,
                  parent_file_sha: str, config: dict) -> dict:
    """Verify an R056 record without importing producer execution code."""
    raw = unseal(record, "hcc-r056-kernel-v1")
    expected_fields = {
        "schema", "condition", "mask", "input_pair", "original_drives",
        "parent_record_sha256", "source_program_digest", "program", "drives",
        "initial_state", "active_top_down_links", "removed_top_down_links", "top_down",
        "ticks", "final_state", "convergence", "cost", "counterfactual",
        "native_session_packet", "proof", "support", "raw_decision", "adoption",
        "actual_energy_joules", "termination_scope",
    }
    require(set(raw) == expected_fields, "Kernel record fields")
    require(raw["condition"] in CONDITIONS and condition == {
        "id": raw["condition"], "input_pair": CONDITIONS[raw["condition"]][0],
        "drives": CONDITIONS[raw["condition"]][1],
    }, "Condition binding")
    require(raw["mask"] in MASK_REMOVALS
            and mask == {"id": raw["mask"], "remove": list(MASK_REMOVALS[raw["mask"]])},
            "Mask binding")
    require(raw["input_pair"] == condition["input_pair"], "Input metadata binding")
    require(raw["original_drives"] == ORIGINAL_DRIVES, "Original drive receipt")
    require(raw["drives"] == condition["drives"], "Exact drive override")
    require(raw["parent_record_sha256"] == parent_file_sha, "Parent record binding")
    pair_to_id = _feedback_id_map(original)
    require(raw["source_program_digest"] == fingerprint(original), "Source program digest")
    removed_ids = set(mask["remove"])
    active, removed, kept = [], [], []
    for link in original["links"]:
        if link["kind"] == "top_down":
            identity = pair_to_id[(link["source"], link["target"])]
            if identity in removed_ids:
                removed.append(link)
                continue
            active.append(link)
        kept.append(link)
    require(raw["program"] == {**original, "links": kept},
            "Only the fixed deletion mask may change the program")
    require(raw["active_top_down_links"] == active and raw["removed_top_down_links"] == removed,
            "Feedback deletion receipt/order")
    require(raw["initial_state"] == {group["id"]: 0.5 for group in original["groups"]},
            "Initial state changed")
    require(raw["top_down"] is True and raw["counterfactual"] is True
            and raw["termination_scope"] == "counterfactual_kernel_termination", "Kernel scope")
    require(all(raw[key] is None for key in (
        "native_session_packet", "proof", "support", "raw_decision", "adoption",
        "actual_energy_joules",
    )), "Unmeasured native/outcome claim")
    verify_trajectory(raw["program"], raw["drives"], raw["initial_state"], raw["ticks"],
                      raw["final_state"], raw["convergence"], raw["cost"], config)
    return {key: raw[key] for key in
            ("condition", "mask", "input_pair", "final_state", "convergence", "cost")}


def classify_endpoint(goal: float, status: str) -> str:
    require(type(goal) in (int, float) and isfinite(goal), "Finite goal endpoint")
    require(isinstance(status, str), "Convergence status")
    if status not in STABLE_STATUSES:
        return "inconclusive"
    if goal < THRESHOLD - ABSTENTION_BAND:
        return "low"
    if goal > THRESHOLD + ABSTENTION_BAND:
        return "high"
    return "inconclusive"


def allocation_comparisons(rows: list[dict]) -> list[dict]:
    """Report continuous coordinate deltas before the contextual endpoint predicate."""
    comparisons = []
    for condition in CONDITIONS:
        cells = {row["mask"]: row for row in rows if row["condition"] == condition}
        if not cells:
            continue
        require(set(cells) == set(MASK_REMOVALS), "Incomplete allocation cells")
        full, dropout = cells["full"], cells["drop_P_prefix"]
        full_regime = classify_endpoint(full["final_state"]["goal"],
                                        full["convergence"]["status"])
        dropout_regime = classify_endpoint(dropout["final_state"]["goal"],
                                           dropout["convergence"]["status"])
        necessary = (True if full_regime == "low" and dropout_regime == "high"
                     else False if full_regime == dropout_regime == "low" else None)
        comparisons.append(dict(
            condition=condition, input_pair=list(CONDITIONS[condition][0]),
            mask="drop_P_prefix", full_goal=full["final_state"]["goal"],
            dropout_goal=dropout["final_state"]["goal"],
            delta_goal=dropout["final_state"]["goal"] - full["final_state"]["goal"],
            full_e0=full["final_state"]["e:0"], dropout_e0=dropout["final_state"]["e:0"],
            delta_e0=dropout["final_state"]["e:0"] - full["final_state"]["e:0"],
            full_e1=full["final_state"]["e:1"], dropout_e1=dropout["final_state"]["e:1"],
            delta_e1=dropout["final_state"]["e:1"] - full["final_state"]["e:1"],
            full_regime=full_regime, dropout_regime=dropout_regime,
            necessary_for_low_endpoint=necessary,
        ))
    return comparisons


def factorial_contrasts(comparisons: list[dict]) -> list[dict]:
    """Predeclared single-drive effects and difference of effects, by orientation."""
    by_condition = {item["condition"]: item for item in comparisons}
    require(len(comparisons) == len(CONDITIONS) and set(by_condition) == set(CONDITIONS),
            "Complete unique research comparisons required")
    contrasts = []
    for orientation, matrix in MATRICES.items():
        for measure in ("full_goal", "dropout_goal", "delta_goal"):
            a, b = [by_condition[name][measure] for name in matrix[0]]
            c, d = [by_condition[name][measure] for name in matrix[1]]
            contrasts.append(dict(
                orientation=orientation, measure=measure, matrix=[[a, b], [c, d]],
                weak_increase_at_strong_4=b-a,
                weak_increase_at_strong_3_02=d-c,
                strong_decrease_at_weak_0_08=c-a,
                strong_decrease_at_weak_1_06=d-b,
                interaction=(d-c)-(b-a), status="nondirectional",
            ))
    return contrasts


def _verify_original_program(run: Path, spec: dict) -> tuple[dict, dict]:
    networks, _ = _verify_parent(run, spec)
    start, goal = networks["startstrong"], networks["goalstrong"]
    require(start["program"] == goal["program"],
            "R052 strengthened conditions changed the original program")
    require(start["drives"] == ORIGINAL_DRIVES, "R052 start-edge original drives changed")
    return start["program"], networks


def _verify_anchors(run: Path, spec: dict, config: dict, networks: dict) -> dict:
    from tools.r055_allocation.audit import validate_spec as validate_r055_spec
    from tools.r055_allocation.audit import verify_record as verify_r055_record
    anchor_root = run / "anchors"
    _require_inventory(anchor_root, spec["anchor_files"], "Pinned R055 anchor inventory/hash")
    plan_packet = load(anchor_root / "plan.json")
    plan = unseal(plan_packet, "hcc-r055-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "R055 anchor plan fields")
    source_manifest = load(anchor_root / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r055-source-manifest-v1"
            and plan["source_manifest_sha256"]
            == sha((anchor_root / "source_manifest.json").read_bytes()),
            "R055 anchor plan/source binding")
    validate_r055_spec(plan["spec"])
    require(plan["purpose"] == "research" and plan["automatic_retry"] is False
            and plan["config"] == config and plan["spec"]["parent_files"] == spec["parent_files"],
            "R055 anchor condition/config/parent freeze")
    raw_manifest = load(anchor_root / "raw_manifest.json")
    require(set(raw_manifest) == {"schema", "files"}
            and raw_manifest["schema"] == "hcc-r055-raw-manifest-v1",
            "R055 raw manifest schema")
    anchor_audit = load(anchor_root / "analysis/audit.json")
    require(anchor_audit["schema"] == "hcc-r055-audit-v1"
            and anchor_audit["verified"] is True and anchor_audit["purpose"] == "research"
            and anchor_audit["research_experiment"] is True
            and anchor_audit["plan_sha256"] == plan_packet["sha256"],
            "R055 audit/plan binding")
    conditions = {item["id"]: item for item in plan["spec"]["conditions"]}
    masks = {item["id"]: item for item in plan["spec"]["masks"]}
    audited = {(row["condition"], row["mask"]): row for row in anchor_audit["rows"]}
    records = {}
    parent_path = run / "parents" / spec["program_parent"]
    original = networks["startstrong"]["program"]
    for condition in spec["bridge_conditions"]:
        for mask in MASK_REMOVALS:
            relative = f"study/{condition}/{mask}.json"
            require(raw_manifest["files"].get(f"{condition}/{mask}.json")
                    == spec["anchor_files"][relative], "R055 raw-manifest/file binding")
            packet = load(anchor_root / relative)
            row = verify_r055_record(packet, conditions[condition], masks[mask],
                                     original, sha(parent_path.read_bytes()), config)
            require(_close(row, audited[(condition, mask)]), "R055 raw/audit row mismatch")
            records[(condition, mask)] = unseal(packet, "hcc-r055-kernel-v1")
    return records


def _bridge(condition: str, mask: str, record: dict, anchor: dict) -> dict:
    checks = dict(
        drives_close=_close(record["drives"], anchor["drives"]),
        tick_trajectory_close=_close(record["ticks"], anchor["ticks"]),
        final_state_close=_close(record["final_state"], anchor["final_state"]),
        convergence_close=_close(record["convergence"], anchor["convergence"]),
        counters_equal=record["cost"] == anchor["cost"],
    )
    require(all(checks.values()), f"R055 numerical bridge failed: {condition}/{mask}")
    return dict(condition=condition, mask=mask, anchor="R055", **checks, verified=True)


def audit(run: Path) -> dict:
    source_manifest = load(run / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r056-source-manifest-v1",
            "Source manifest fields")
    _require_inventory(run / "source", source_manifest["files"], "Frozen source inventory/hash")
    require(git_tree(run / "source/src") == SRC_TREE
            and git_tree(run / "source/tests") == TEST_TREE, "Core/test tree drift")
    _verify_historical_sources(run / "source")
    plan_packet = load(run / "plan.json")
    plan = unseal(plan_packet, "hcc-r056-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "Plan fields")
    require(plan["source_manifest_sha256"] == sha((run / "source_manifest.json").read_bytes())
            and plan["automatic_retry"] is False, "Plan/source/retry binding")
    spec = load(run / "source/experiments/exp-37-drive-factorial/frozen_spec.json")
    require(plan["spec"] == spec, "Plan/spec binding")
    validate_spec(spec)
    from hcr import codec
    require(plan["config"] == codec.plain(Config()), "Exact default kernel config")
    require(plan["purpose"] in ("implementation_validation", "research"), "Purpose")
    conditions = (spec["implementation_validation_conditions"] if
                  plan["purpose"] == "implementation_validation" else spec["research_conditions"])
    expected_conditions = (BRIDGE_CONDITIONS if
                           plan["purpose"] == "implementation_validation" else list(CONDITIONS))
    require(conditions == expected_conditions, "Purpose/condition matrix")
    root = run / ("smoke" if plan["purpose"] == "implementation_validation" else "study")
    raw_manifest = load(run / "raw_manifest.json")
    require(set(raw_manifest) == {"schema", "files"}
            and raw_manifest["schema"] == "hcc-r056-raw-manifest-v1", "Raw manifest fields")
    _require_inventory(root, raw_manifest["files"], "Raw inventory/hash")
    expected = {f"{condition}/{mask}.json" for condition in conditions for mask in MASK_REMOVALS}
    require(set(raw_manifest["files"]) == expected, "Raw branch inventory")

    original, networks = _verify_original_program(run, spec)
    anchors = _verify_anchors(run, spec, plan["config"], networks)
    condition_specs = {item["id"]: item for item in spec["conditions"]}
    mask_specs = {item["id"]: item for item in spec["masks"]}
    parent_path = run / "parents" / spec["program_parent"]
    parent_sha = sha(parent_path.read_bytes())
    rows, records = [], {}
    for condition in conditions:
        for mask in MASK_REMOVALS:
            packet = load(root / condition / (mask + ".json"))
            rows.append(verify_record(packet, condition_specs[condition], mask_specs[mask],
                                      original, parent_sha, plan["config"]))
            records[(condition, mask)] = unseal(packet, "hcc-r056-kernel-v1")
    bridges = [
        _bridge(condition, mask, records[(condition, mask)], anchors[(condition, mask)])
        for condition in spec["bridge_conditions"] for mask in MASK_REMOVALS
    ]
    comparisons = allocation_comparisons(rows)
    require(len(comparisons) == len(conditions), "Allocation comparison count")
    research = plan["purpose"] == "research"
    contrasts = factorial_contrasts(comparisons) if research else []
    require(not (FORBIDDEN & set(sys.modules)),
            "Auditor imported producer/runtime/session/dynamics")
    return dict(
        schema="hcc-r056-audit-v1", verified=True, purpose=plan["purpose"],
        research_experiment=research, plan_sha256=plan_packet["sha256"], rows=rows,
        bridges=bridges, allocation_comparisons=comparisons, factorial_contrasts=contrasts,
        prediction="nondirectional", independent_samples=False, native_outcomes_measured=False,
        inference_scope=spec["inference_scope"],
    )


def render_summary(report: dict) -> bytes:
    require(report["verified"] is True, "Verified audit required for summary")
    lines = [
        "# EXP-37 / R056 국소 drive 2×2 대조", "",
        f"실행 목적: {report['purpose']}", "",
        "| condition | input pair | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |",
        "|---|---|---|---:|---:|---:|---|---:|---:|",
    ]
    for row in report["rows"]:
        state, cost = row["final_state"], row["cost"]
        lines.append("| " + " | ".join(map(str, (
            row["condition"], row["input_pair"], row["mask"], state["goal"], state["e:0"],
            state["e:1"], row["convergence"]["status"], cost["kernel_ticks"],
            cost["signal_transmissions"],
        ))) + " |")
    lines += ["", "| condition | delta goal | delta e:0 | delta e:1 | full | dropout | necessity |",
              "|---|---:|---:|---:|---|---|---|"]
    for item in report["allocation_comparisons"]:
        lines.append("| " + " | ".join(map(str, (
            item["condition"], item["delta_goal"], item["delta_e0"], item["delta_e1"],
            item["full_regime"], item["dropout_regime"],
            item["necessary_for_low_endpoint"],
        ))) + " |")
    if report["factorial_contrasts"]:
        lines += ["", "| orientation | measure | weak increase at S=4 | weak increase at S=3.02 | strong decrease at W=.08 | strong decrease at W=1.06 | interaction |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for item in report["factorial_contrasts"]:
            lines.append("| " + " | ".join(map(str, (
                item["orientation"], item["measure"], item["weak_increase_at_strong_4"],
                item["weak_increase_at_strong_3_02"], item["strong_decrease_at_weak_0_08"],
                item["strong_decrease_at_weak_1_06"], item["interaction"],
            ))) + " |")
    lines += ["", f"R055 전체 궤적 bridge {len(report['bridges'])}개가 모두 통과했다.",
              "약한 drive 증가와 강한 drive 감소는 각각 다른 drive를 고정한 기술 대조다.",
              "방향별 결과를 합치지 않는다. 총량이 함께 변하므로 별도의 총량 원인을 분리하지 않는다.",
              "비안정 종료도 연속값을 보고하지만 endpoint는 inconclusive다.",
              "고정 numerical kernel 결과이며 native outcome, sufficiency, basin, 일반성 증거가 아니다.",
              "결정론적 분기들은 독립 표본이 아니다.", ""]
    return "\n".join(lines).encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.run)
    dump(args.run / "analysis/audit.json", report)
    publish(args.run / "analysis/summary.ko.md", render_summary(report))
    print("VERIFIED:", len(report["rows"]), "counterfactual kernels /",
          len(report["bridges"]), "R055 bridges", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
