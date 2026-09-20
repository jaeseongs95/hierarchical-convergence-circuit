"""Independent R054 replay, provenance audit, and single-link comparisons."""
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
from tools.r053_feedback.audit import (
    _close,
    _feedback_partition,
    _verify_parent,
    validate_spec as validate_r053_spec,
    verify_record as verify_r053_record,
    verify_trajectory,
)


SPEC_FINGERPRINT = "6234658560d0a292978cb7e5398fcfc77f0c185c65f7aed730fb9a0d9a44f8a4"
CONDITION_PARENT = {"startstrong": "start_edge", "goalstrong": "goal_edge"}
MASK_REMOVALS = {
    "full": (),
    "off": ("E_start", "E_goal", "P_prefix", "P_goal"),
    "drop_E_start": ("E_start",),
    "drop_E_goal": ("E_goal",),
    "drop_P_prefix": ("P_prefix",),
    "drop_P_goal": ("P_goal",),
}
FEEDBACK_LINKS = {
    "E_start": ("p:0:0", "e:0"),
    "E_goal": ("p:0:1", "e:1"),
    "P_prefix": ("p:0:1", "p:0:0"),
    "P_goal": ("goal", "p:0:1"),
}
DROP_MASKS = tuple(mask for mask in MASK_REMOVALS if mask.startswith("drop_"))
STABLE_STATUSES = ("stable_decision", "stable_ambiguous")
TOLERANCE = {"abs_tol": 1e-12, "rel_tol": 1e-12}
THRESHOLD = 0.5
ABSTENTION_BAND = 1e-6
FORBIDDEN = R050_FORBIDDEN | {
    "tools.r052_array_roles.worker",
    "tools.r053_feedback.worker",
    "tools.r054_links.worker",
}
HISTORICAL_MANIFESTS = {
    "R050": "cbd6f138bc8f2318ae5546c0efffe0ce7b4a17bfaab4a0feebbcf7bd33e6d92a",
    "R051": "e705066ade1d954c936aa582ed44a4b0d9a8d776d76fb06e61bee102788088df",
    "R052": "7afe672c30263c87c5d5ca10a17016de8a6ecba4f7894a8a8d61b9eb8accbbba",
    "R053": "3247d77ca829d76ea39ff0f210e8a8ad8e7bd50d1636cb717ea739a81ab66aeb",
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
    """Reject a consistently resealed change to the frozen R054 contract."""
    require(fingerprint(spec) == SPEC_FINGERPRINT, "Exact frozen R054 spec")
    require(spec["frozen_before_research_execution"] is True, "Spec was not frozen")
    require(spec["numeric_comparison"] == TOLERANCE, "Numeric comparison drift")
    require(spec["initial_activation"] == 0.5, "Initial activation drift")
    require(spec["conditions"] == [
        {"id": condition, "parent_label": parent}
        for condition, parent in CONDITION_PARENT.items()
    ], "Condition matrix")
    require(spec["masks"] == [
        {"id": mask, "remove": list(removed)} for mask, removed in MASK_REMOVALS.items()
    ], "Mask matrix")
    require(spec["feedback_links"] == [
        {"id": identity, "source": pair[0], "target": pair[1]}
        for identity, pair in FEEDBACK_LINKS.items()
    ], "Feedback identities")
    require(len(spec["parent_files"]) == 10 and len(spec["anchor_files"]) == 8,
            "Pinned evidence counts")
    require(spec["implementation_validation_conditions"] == ["startstrong"]
            and spec["research_conditions"] == list(CONDITION_PARENT), "Purpose matrices")
    require(spec["endpoint_rule"] == {
        "stable_statuses": list(STABLE_STATUSES), "threshold": THRESHOLD,
        "abstention_band": ABSTENTION_BAND,
        "low": "goal < threshold - abstention_band",
        "high": "goal > threshold + abstention_band",
        "otherwise": "inconclusive", "not_an_error_bound": True,
    }, "Endpoint rule drift")


def _feedback_id_map(program: dict) -> dict[tuple[str, str], str]:
    _feedback_partition(program)
    pairs = [(link["source"], link["target"]) for link in program["links"]
             if link["kind"] == "top_down"]
    expected = {pair: identity for identity, pair in FEEDBACK_LINKS.items()}
    require(len(pairs) == len(set(pairs)) and set(pairs) == set(expected),
            "Exact feedback identity set")
    return expected


def verify_record(record: dict, condition: dict, mask: dict, network: dict,
                  parent_file_sha: str, config: dict) -> dict:
    """Verify an R054 record without importing producer execution code."""
    raw = unseal(record, "hcc-r054-kernel-v1")
    expected_fields = {
        "schema", "condition", "mask", "parent_record_sha256", "source_program_digest",
        "program", "drives", "initial_state", "active_top_down_links",
        "removed_top_down_links", "top_down", "ticks", "final_state", "convergence", "cost",
        "counterfactual", "native_session_packet", "proof", "support", "raw_decision",
        "adoption", "actual_energy_joules", "termination_scope",
    }
    require(set(raw) == expected_fields, "Kernel record fields")
    require(raw["condition"] in CONDITION_PARENT
            and condition == {"id": raw["condition"],
                          "parent_label": CONDITION_PARENT.get(raw["condition"])},
            "Condition binding")
    require(raw["mask"] in MASK_REMOVALS
            and mask == {"id": raw["mask"], "remove": list(MASK_REMOVALS[raw["mask"]])},
            "Mask binding")
    require(raw["parent_record_sha256"] == parent_file_sha, "Parent record binding")
    original = network["program"]
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
    require(raw["drives"] == network["drives"], "Drives changed")
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
    return {key: raw[key] for key in ("condition", "mask", "final_state", "convergence", "cost")}


def classify_endpoint(goal: float, status: str) -> str:
    """Apply the frozen endpoint predicate; the band is not an error bound."""
    require(type(goal) in (int, float) and isfinite(goal), "Finite goal endpoint")
    require(isinstance(status, str), "Convergence status")
    if status not in STABLE_STATUSES:
        return "inconclusive"
    if goal < THRESHOLD - ABSTENTION_BAND:
        return "low"
    if goal > THRESHOLD + ABSTENTION_BAND:
        return "high"
    return "inconclusive"


def dropout_comparisons(rows: list[dict]) -> list[dict]:
    """Report continuous deltas first, then the contextual endpoint predicate."""
    comparisons = []
    for condition in CONDITION_PARENT:
        cells = {row["mask"]: row for row in rows if row["condition"] == condition}
        if not cells:
            continue
        require(set(cells) == set(MASK_REMOVALS), "Incomplete single-link matrix")
        full = cells["full"]
        weak_coordinate = "e:1" if condition == "startstrong" else "e:0"
        full_regime = classify_endpoint(full["final_state"]["goal"],
                                        full["convergence"]["status"])
        for mask in DROP_MASKS:
            dropout = cells[mask]
            dropout_regime = classify_endpoint(dropout["final_state"]["goal"],
                                               dropout["convergence"]["status"])
            necessary = (True if full_regime == "low" and dropout_regime == "high"
                         else False if full_regime == dropout_regime == "low" else None)
            identity = MASK_REMOVALS[mask][0]
            comparisons.append(dict(
                condition=condition,
                mask=mask,
                removed_link={"id": identity, "source": FEEDBACK_LINKS[identity][0],
                              "target": FEEDBACK_LINKS[identity][1]},
                full_goal=full["final_state"]["goal"],
                dropout_goal=dropout["final_state"]["goal"],
                delta_goal=dropout["final_state"]["goal"] - full["final_state"]["goal"],
                weak_edge_coordinate=weak_coordinate,
                full_weak_edge=full["final_state"][weak_coordinate],
                dropout_weak_edge=dropout["final_state"][weak_coordinate],
                delta_weak_edge=(dropout["final_state"][weak_coordinate]
                                 - full["final_state"][weak_coordinate]),
                full_regime=full_regime,
                dropout_regime=dropout_regime,
                necessary_for_low_endpoint=necessary,
            ))
    return comparisons


def prediction_results(rows: list[dict]) -> list[dict]:
    cells = {(row["condition"], row["mask"]): row for row in rows}
    results = []
    p1_masks = {"startstrong": "drop_E_goal", "goalstrong": "drop_E_start"}
    p2_masks = {"startstrong": "drop_E_start", "goalstrong": "drop_E_goal"}
    present = {row["condition"] for row in rows}
    for prediction, masks, expected in (("P1", p1_masks, "high"), ("P2", p2_masks, "low")):
        for condition in CONDITION_PARENT:
            if condition not in present:
                continue
            mask = masks[condition]
            row = cells[(condition, mask)]
            regime = classify_endpoint(row["final_state"]["goal"], row["convergence"]["status"])
            status = ("support" if regime == expected else
                      "inconclusive" if regime == "inconclusive" else "refuted")
            results.append(dict(id=prediction, condition=condition, mask=mask,
                                expected_regime=expected, observed_regime=regime, status=status))
    for condition in CONDITION_PARENT:
        if condition not in present:
            continue
        results.append(dict(
            id="P3", condition=condition, status="nondirectional",
            masks=[
                {"id": mask, "goal": cells[(condition, mask)]["final_state"]["goal"],
                 "convergence_status": cells[(condition, mask)]["convergence"]["status"]}
                for mask in ("drop_P_prefix", "drop_P_goal")
            ],
        ))
    return results


def _parent_record_path(condition: str) -> str:
    return f"study/raw/r052-c001/{CONDITION_PARENT[condition]}.json"


def _verify_anchors(run: Path, spec: dict, config: dict, networks: dict) -> dict:
    anchor_root = run / "anchors"
    _require_inventory(anchor_root, spec["anchor_files"], "Pinned R053 anchor inventory/hash")
    plan_packet = load(anchor_root / "plan.json")
    plan = unseal(plan_packet, "hcc-r053-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "R053 anchor plan fields")
    source_manifest = load(anchor_root / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r053-source-manifest-v1"
            and plan["source_manifest_sha256"] == sha((anchor_root / "source_manifest.json").read_bytes()),
            "R053 anchor plan/source binding")
    validate_r053_spec(plan["spec"])
    require(plan["purpose"] == "research" and plan["automatic_retry"] is False
            and plan["config"] == config and plan["spec"]["parent_files"] == spec["parent_files"],
            "R053 anchor condition/config/parent freeze")
    raw_manifest = load(anchor_root / "raw_manifest.json")
    require(set(raw_manifest) == {"schema", "files"}
            and raw_manifest["schema"] == "hcc-r053-raw-manifest-v1", "R053 raw manifest schema")
    anchor_audit = load(anchor_root / "analysis/audit.json")
    require(anchor_audit["schema"] == "hcc-r053-audit-v1"
            and anchor_audit["verified"] is True
            and anchor_audit["purpose"] == "research"
            and anchor_audit["research_experiment"] is True
            and anchor_audit["plan_sha256"] == plan_packet["sha256"],
            "R053 audit/plan binding")
    conditions = {item["id"]: item for item in plan["spec"]["conditions"]}
    masks = {item["id"]: item for item in plan["spec"]["masks"]}
    audited = {(row["condition"], row["mask"]): row for row in anchor_audit["rows"]}
    records = {}
    for condition in CONDITION_PARENT:
        parent_path = run / "parents" / _parent_record_path(condition)
        for mask in ("full", "off"):
            relative = f"study/{condition}/{mask}.json"
            require(raw_manifest["files"].get(f"{condition}/{mask}.json")
                    == spec["anchor_files"][relative], "R053 raw-manifest/file binding")
            packet = load(anchor_root / relative)
            row = verify_r053_record(packet, conditions[condition], masks[mask], networks[condition],
                                     sha(parent_path.read_bytes()), config)
            require(_close(row, audited[(condition, mask)]), "R053 raw/audit row mismatch")
            records[(condition, mask)] = unseal(packet, "hcc-r053-kernel-v1")
    return records


def _bridge(condition: str, mask: str, record: dict, anchor: dict) -> dict:
    checks = dict(
        tick_trajectory_close=_close(record["ticks"], anchor["ticks"]),
        final_state_close=_close(record["final_state"], anchor["final_state"]),
        convergence_close=_close(record["convergence"], anchor["convergence"]),
        counters_equal=record["cost"] == anchor["cost"],
    )
    require(all(checks.values()), f"R053 numerical bridge failed: {condition}/{mask}")
    return dict(condition=condition, mask=mask, anchor="R053", **checks, verified=True)


def audit(run: Path) -> dict:
    source_manifest = load(run / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r054-source-manifest-v1", "Source manifest fields")
    _require_inventory(run / "source", source_manifest["files"], "Frozen source inventory/hash")
    require(git_tree(run / "source/src") == SRC_TREE
            and git_tree(run / "source/tests") == TEST_TREE, "Core/test tree drift")
    _verify_historical_sources(run / "source")
    plan_packet = load(run / "plan.json")
    plan = unseal(plan_packet, "hcc-r054-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "Plan fields")
    require(plan["source_manifest_sha256"] == sha((run / "source_manifest.json").read_bytes())
            and plan["automatic_retry"] is False, "Plan/source/retry binding")
    spec = load(run / "source/experiments/exp-35-feedback-links/frozen_spec.json")
    require(plan["spec"] == spec, "Plan/spec binding")
    validate_spec(spec)
    from hcr import codec
    require(plan["config"] == codec.plain(Config()), "Exact default kernel config")
    require(plan["purpose"] in ("implementation_validation", "research"), "Purpose")
    conditions = (spec["implementation_validation_conditions"] if
                  plan["purpose"] == "implementation_validation" else spec["research_conditions"])
    require(conditions == (["startstrong"] if plan["purpose"] == "implementation_validation"
                            else list(CONDITION_PARENT)), "Purpose/condition matrix")
    root = run / ("smoke" if plan["purpose"] == "implementation_validation" else "study")
    raw_manifest = load(run / "raw_manifest.json")
    require(set(raw_manifest) == {"schema", "files"}
            and raw_manifest["schema"] == "hcc-r054-raw-manifest-v1", "Raw manifest fields")
    _require_inventory(root, raw_manifest["files"], "Raw inventory/hash")
    expected = {f"{condition}/{mask}.json" for condition in conditions for mask in MASK_REMOVALS}
    require(set(raw_manifest["files"]) == expected, "Raw branch inventory")

    networks, _ = _verify_parent(run, spec)
    anchors = _verify_anchors(run, spec, plan["config"], networks)
    condition_specs = {item["id"]: item for item in spec["conditions"]}
    mask_specs = {item["id"]: item for item in spec["masks"]}
    rows, records = [], {}
    for condition in conditions:
        parent_path = run / "parents" / _parent_record_path(condition)
        for mask in MASK_REMOVALS:
            packet = load(root / condition / (mask + ".json"))
            rows.append(verify_record(packet, condition_specs[condition], mask_specs[mask],
                                      networks[condition], sha(parent_path.read_bytes()), plan["config"]))
            records[(condition, mask)] = unseal(packet, "hcc-r054-kernel-v1")
    bridges = [
        _bridge(condition, mask, records[(condition, mask)], anchors[(condition, mask)])
        for condition in conditions for mask in ("full", "off")
    ]
    comparisons = dropout_comparisons(rows)
    require(len(comparisons) == 4 * len(conditions), "Single-link comparison count")
    require(not (FORBIDDEN & set(sys.modules)), "Auditor imported producer/runtime/session/dynamics")
    research = plan["purpose"] == "research"
    return dict(
        schema="hcc-r054-audit-v1", verified=True, purpose=plan["purpose"],
        research_experiment=research, plan_sha256=plan_packet["sha256"], rows=rows,
        bridges=bridges, dropout_comparisons=comparisons, predictions=prediction_results(rows),
        independent_samples=False, native_outcomes_measured=False,
        inference_scope="fixed-context contextual numerical endpoint predicate; not sufficiency, "
                        "native proof/adoption, or basin evidence",
    )


def render_summary(report: dict) -> bytes:
    require(report["verified"] is True, "Verified audit required for summary")
    lines = [
        "# EXP-35 / R054 single feedback links", "", f"실행 목적: {report['purpose']}", "",
        "| condition | mask | goal | convergence | ticks | transmissions |",
        "|---|---|---:|---|---:|---:|",
    ]
    for row in report["rows"]:
        lines.append("| " + " | ".join(map(str, (
            row["condition"], row["mask"], row["final_state"]["goal"],
            row["convergence"]["status"], row["cost"]["kernel_ticks"],
            row["cost"]["signal_transmissions"],
        ))) + " |")
    lines += ["", "| condition | removed link | delta goal | weak edge | delta weak | full | dropout | necessity |",
              "|---|---|---:|---|---:|---|---|---|"]
    for item in report["dropout_comparisons"]:
        lines.append("| " + " | ".join(map(str, (
            item["condition"], item["removed_link"]["id"], item["delta_goal"],
            item["weak_edge_coordinate"], item["delta_weak_edge"], item["full_regime"],
            item["dropout_regime"], item["necessary_for_low_endpoint"],
        ))) + " |")
    lines += ["", f"R053 full/off numerical bridge {len(report['bridges'])}개가 모두 통과했다.",
              "비안정 종료도 연속값과 delta를 보고하지만 endpoint 판정은 inconclusive다.",
              "이 결과는 고정 맥락의 수치 endpoint 술어이며 sufficiency, native proof/adoption, basin 증거가 아니다.",
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
          len(report["bridges"]), "R053 bridges", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
