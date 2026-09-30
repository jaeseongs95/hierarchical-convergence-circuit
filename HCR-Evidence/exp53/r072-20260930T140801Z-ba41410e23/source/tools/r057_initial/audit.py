"""Independent R057 replay, provenance audit, and initial-state comparisons."""
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


SPEC_FINGERPRINT = "02eca0fc3eab156bfe1985ff2af6b8f57df36bb4fb22188a911c38b36cb97e58"
CONDITIONS = {
    f"{orientation}_i{int(initial*10):02}": dict(
        id=f"{orientation}_i{int(initial*10):02}", orientation=orientation,
        initial_activation=initial, input_pair=pair, drives=drives,
    )
    for orientation, pair, drives in (
        ("start", [1.0, .02], {"e:0": 4.0, "e:1": .08, "goal": 0.0}),
        ("goal", [.02, 1.0], {"e:0": .08, "e:1": 4.0, "goal": 0.0}),
    ) for initial in (.1, .5, .9)
}
ORIGINAL_DRIVES = {"e:0": 4.0, "e:1": 0.08, "goal": 0.0}
MASK_REMOVALS = {"full": (), "drop_P_prefix": ("P_prefix",)}
FEEDBACK_LINKS = {
    "E_start": ("p:0:0", "e:0"),
    "E_goal": ("p:0:1", "e:1"),
    "P_prefix": ("p:0:1", "p:0:0"),
    "P_goal": ("goal", "p:0:1"),
}
BRIDGE_CONDITIONS = ["start_i05", "goal_i05"]
ANCHOR_CONDITIONS = {"start_i05": "startstrong", "goal_i05": "goalstrong"}
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
    "tools.r057_initial.worker",
}
HISTORICAL_MANIFESTS = {
    "R056": "a8ad2d4764c4d144af3971abe723d48bbf82e362cf8312543fa2b65835d61764",
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
    """Reject a consistently resealed change to the frozen R057 contract."""
    require(fingerprint(spec) == SPEC_FINGERPRINT, "Exact frozen R057 spec")
    require(spec["frozen_before_research_execution"] is True, "Spec was not frozen")
    require(spec["numeric_comparison"] == TOLERANCE, "Numeric comparison drift")
    require(spec["initial_levels"] == [.1, .5, .9] and spec["baseline_initial"] == .5,
            "Initial activation matrix")
    require(spec["program_parent"] == "study/raw/r052-c001/start_edge.json",
            "Program parent drift")
    require(spec["conditions"] == list(CONDITIONS.values()), "Condition matrix")
    require(spec["masks"] == [
        {"id": mask, "remove": list(removed)} for mask, removed in MASK_REMOVALS.items()
    ], "Mask matrix")
    require(spec["feedback_links"] == [
        {"id": identity, "source": pair[0], "target": pair[1]}
        for identity, pair in FEEDBACK_LINKS.items()
    ], "Feedback identities")
    require(len(spec["parent_files"]) == 10 and len(spec["anchor_files"]) == 8,
            "Pinned evidence counts")
    require(spec["implementation_validation_conditions"] == BRIDGE_CONDITIONS
            and spec["research_conditions"] == list(CONDITIONS), "Purpose matrices")
    require(spec["bridge_conditions"] == BRIDGE_CONDITIONS, "Bridge matrix")
    require(spec["anchor_condition_map"] == ANCHOR_CONDITIONS, "Anchor condition mapping")
    require(spec["endpoint_rule"] == {
        "stable_statuses": list(STABLE_STATUSES), "threshold": THRESHOLD,
        "abstention_band": ABSTENTION_BAND,
        "low": "goal < threshold - abstention_band",
        "high": "goal > threshold + abstention_band",
        "otherwise": "inconclusive", "not_an_error_bound": True,
    }, "Endpoint rule drift")


def verify_record(record: dict, condition: dict, mask: dict, original: dict,
                  parent_file_sha: str, config: dict) -> dict:
    """Verify an R057 record without importing producer execution code."""
    raw = unseal(record, "hcc-r057-kernel-v1")
    expected_fields = {
        "schema", "condition", "mask", "orientation", "initial_activation", "input_pair", "original_drives",
        "parent_record_sha256", "source_program_digest", "program", "drives",
        "initial_state", "active_top_down_links", "removed_top_down_links", "top_down",
        "ticks", "final_state", "convergence", "cost", "counterfactual",
        "native_session_packet", "proof", "support", "raw_decision", "adoption",
        "actual_energy_joules", "termination_scope",
    }
    require(set(raw) == expected_fields, "Kernel record fields")
    require(raw["condition"] in CONDITIONS and condition == CONDITIONS[raw["condition"]],
            "Condition binding")
    require(raw["orientation"] == condition["orientation"]
            and raw["initial_activation"] == condition["initial_activation"],
            "Initial condition metadata binding")
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
    require(raw["initial_state"] == {group["id"]: condition["initial_activation"] for group in original["groups"]},
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
            ("condition", "mask", "orientation", "initial_activation", "input_pair", "final_state", "convergence", "cost")}


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
            condition=condition, input_pair=list(CONDITIONS[condition]["input_pair"]),
            orientation=CONDITIONS[condition]["orientation"],
            initial_activation=CONDITIONS[condition]["initial_activation"],
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


def initial_contrasts(rows: list[dict]) -> list[dict]:
    """Compare each changed uniform initial against .5 without pooling orientations."""
    by = {(r["condition"], r["mask"]): r for r in rows}
    expected = {(c, m) for c in CONDITIONS for m in MASK_REMOVALS}
    require(len(rows) == len(expected) and set(by) == expected,
            "Complete unique research rows required")
    contrasts = []
    for orientation in ("start", "goal"):
        for mask in MASK_REMOVALS:
            baseline = by[(orientation+"_i05", mask)]
            base_regime = classify_endpoint(baseline["final_state"]["goal"],
                                            baseline["convergence"]["status"])
            for suffix, initial in (("01", .1), ("09", .9)):
                changed = by[(orientation+"_i"+suffix, mask)]
                regime = classify_endpoint(changed["final_state"]["goal"],
                                           changed["convergence"]["status"])
                different = (base_regime != regime if base_regime in ("low", "high")
                             and regime in ("low", "high") else None)
                contrasts.append(dict(
                    orientation=orientation, mask=mask, baseline_initial=.5,
                    changed_initial=initial, baseline_condition=baseline["condition"],
                    changed_condition=changed["condition"],
                    delta_goal=changed["final_state"]["goal"]-baseline["final_state"]["goal"],
                    delta_e0=changed["final_state"]["e:0"]-baseline["final_state"]["e:0"],
                    delta_e1=changed["final_state"]["e:1"]-baseline["final_state"]["e:1"],
                    baseline_regime=base_regime, changed_regime=regime,
                    different_stable_regimes=different, status="nondirectional",
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
    from tools.r056_factorial.audit import validate_spec as validate_r056_spec
    from tools.r056_factorial.audit import verify_record as verify_r056_record
    anchor_root = run / "anchors"
    _require_inventory(anchor_root, spec["anchor_files"], "Pinned R056 anchor inventory/hash")
    plan_packet = load(anchor_root / "plan.json")
    plan = unseal(plan_packet, "hcc-r056-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "R056 anchor plan fields")
    source_manifest = load(anchor_root / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r056-source-manifest-v1"
            and plan["source_manifest_sha256"]
            == sha((anchor_root / "source_manifest.json").read_bytes()),
            "R056 anchor plan/source binding")
    validate_r056_spec(plan["spec"])
    require(plan["purpose"] == "research" and plan["automatic_retry"] is False
            and plan["config"] == config and plan["spec"]["parent_files"] == spec["parent_files"],
            "R056 anchor condition/config/parent freeze")
    raw_manifest = load(anchor_root / "raw_manifest.json")
    require(set(raw_manifest) == {"schema", "files"}
            and raw_manifest["schema"] == "hcc-r056-raw-manifest-v1",
            "R056 raw manifest schema")
    anchor_audit = load(anchor_root / "analysis/audit.json")
    require(anchor_audit["schema"] == "hcc-r056-audit-v1"
            and anchor_audit["verified"] is True and anchor_audit["purpose"] == "research"
            and anchor_audit["research_experiment"] is True
            and anchor_audit["plan_sha256"] == plan_packet["sha256"],
            "R056 audit/plan binding")
    conditions = {item["id"]: item for item in plan["spec"]["conditions"]}
    masks = {item["id"]: item for item in plan["spec"]["masks"]}
    audited = {(row["condition"], row["mask"]): row for row in anchor_audit["rows"]}
    records = {}
    parent_path = run / "parents" / spec["program_parent"]
    original = networks["startstrong"]["program"]
    for condition in spec["bridge_conditions"]:
        for mask in MASK_REMOVALS:
            anchor_condition = ANCHOR_CONDITIONS[condition]
            relative = f"study/{anchor_condition}/{mask}.json"
            require(raw_manifest["files"].get(f"{anchor_condition}/{mask}.json")
                    == spec["anchor_files"][relative], "R056 raw-manifest/file binding")
            packet = load(anchor_root / relative)
            row = verify_r056_record(packet, conditions[anchor_condition], masks[mask],
                                     original, sha(parent_path.read_bytes()), config)
            require(_close(row, audited[(anchor_condition, mask)]), "R056 raw/audit row mismatch")
            records[(condition, mask)] = unseal(packet, "hcc-r056-kernel-v1")
    return records


def _bridge(condition: str, mask: str, record: dict, anchor: dict) -> dict:
    checks = dict(
        initial_state_equal=record["initial_state"] == anchor["initial_state"],
        program_equal=record["program"] == anchor["program"],
        drives_close=_close(record["drives"], anchor["drives"]),
        tick_trajectory_close=_close(record["ticks"], anchor["ticks"]),
        final_state_close=_close(record["final_state"], anchor["final_state"]),
        convergence_close=_close(record["convergence"], anchor["convergence"]),
        counters_equal=record["cost"] == anchor["cost"],
    )
    require(all(checks.values()), f"R056 numerical bridge failed: {condition}/{mask}")
    return dict(condition=condition, mask=mask, anchor="R056", **checks, verified=True)


def audit(run: Path) -> dict:
    source_manifest = load(run / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r057-source-manifest-v1",
            "Source manifest fields")
    _require_inventory(run / "source", source_manifest["files"], "Frozen source inventory/hash")
    require(git_tree(run / "source/src") == SRC_TREE
            and git_tree(run / "source/tests") == TEST_TREE, "Core/test tree drift")
    _verify_historical_sources(run / "source")
    plan_packet = load(run / "plan.json")
    plan = unseal(plan_packet, "hcc-r057-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "Plan fields")
    require(plan["source_manifest_sha256"] == sha((run / "source_manifest.json").read_bytes())
            and plan["automatic_retry"] is False, "Plan/source/retry binding")
    spec = load(run / "source/experiments/exp-38-initial-state/frozen_spec.json")
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
            and raw_manifest["schema"] == "hcc-r057-raw-manifest-v1", "Raw manifest fields")
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
            records[(condition, mask)] = unseal(packet, "hcc-r057-kernel-v1")
    bridges = [
        _bridge(condition, mask, records[(condition, mask)], anchors[(condition, mask)])
        for condition in spec["bridge_conditions"] for mask in MASK_REMOVALS
    ]
    comparisons = allocation_comparisons(rows)
    require(len(comparisons) == len(conditions), "Allocation comparison count")
    research = plan["purpose"] == "research"
    contrasts = initial_contrasts(rows) if research else []
    require(not (FORBIDDEN & set(sys.modules)),
            "Auditor imported producer/runtime/session/dynamics")
    return dict(
        schema="hcc-r057-audit-v1", verified=True, purpose=plan["purpose"],
        research_experiment=research, plan_sha256=plan_packet["sha256"], rows=rows,
        bridges=bridges, allocation_comparisons=comparisons, initial_contrasts=contrasts,
        prediction="nondirectional", independent_samples=False, native_outcomes_measured=False,
        inference_scope=spec["inference_scope"],
    )


def render_summary(report: dict) -> bytes:
    require(report["verified"] is True, "Verified audit required for summary")
    lines = ["# EXP-38 / R057 초기 상태 대조", "", f"실행 목적: {report['purpose']}", "",
             "| orientation | initial | mask | goal | e:0 | e:1 | convergence | ticks | transmissions |",
             "|---|---:|---|---:|---:|---:|---|---:|---:|"]
    for row in report["rows"]:
        state, cost = row["final_state"], row["cost"]
        lines.append("| " + " | ".join(map(str, (
            row["orientation"], row["initial_activation"], row["mask"], state["goal"],
            state["e:0"], state["e:1"], row["convergence"]["status"], cost["kernel_ticks"],
            cost["signal_transmissions"],
        ))) + " |")
    lines += ["", "| condition | drop-minus-full goal | full | dropout | necessity |",
              "|---|---:|---|---|---|"]
    for row in report["allocation_comparisons"]:
        lines.append("| " + " | ".join(map(str, (row["condition"], row["delta_goal"],
            row["full_regime"], row["dropout_regime"], row["necessary_for_low_endpoint"]))) + " |")
    if report["initial_contrasts"]:
        lines += ["", "| orientation | mask | initial | goal minus .5 baseline | baseline regime | changed regime | different stable regimes |",
                  "|---|---|---:|---:|---|---|---|"]
        for row in report["initial_contrasts"]:
            lines.append("| " + " | ".join(map(str, (row["orientation"], row["mask"],
                row["changed_initial"], row["delta_goal"], row["baseline_regime"],
                row["changed_regime"], row["different_stable_regimes"]))) + " |")
    lines += ["", f"R056 전체 궤적 bridge {len(report['bridges'])}개가 통과했다.",
              "초기 상태 .1/.9와 .5의 비방향 기술 대조다. 비안정 종료의 범주 차이는 null이다.",
              "같은 범주·작은 차이는 같은 수학적 고정점이나 전역 수렴의 증명이 아니다.",
              "범주가 달라도 basin 경계·attractor·hysteresis·native outcome의 증거로 확장하지 않는다.",
              "결정론적 분기는 독립 표본이 아니다.", ""]
    return "\n".join(lines).encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.run)
    dump(args.run / "analysis/audit.json", report)
    publish(args.run / "analysis/summary.ko.md", render_summary(report))
    print("VERIFIED:", len(report["rows"]), "counterfactual kernels /",
          len(report["bridges"]), "R056 bridges", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
