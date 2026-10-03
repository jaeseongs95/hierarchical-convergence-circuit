"""Independent R053 kernel replay and frozen R052 bridge verification."""
from __future__ import annotations

import argparse
from math import isclose, isfinite
from pathlib import Path
import sys

from hcr.evaluation.audit import independent_step
from hcr.model import Config
from tools.r050_review_boundary.audit import FORBIDDEN as R050_FORBIDDEN, NativeVerifier
from tools.r050_review_boundary.common import (
    SRC_TREE, TEST_TREE, dump, files, fingerprint, git_tree, load, publish, require, sha, unseal,
)
from tools.r052_array_roles.audit import validate_record as validate_r052_record
from tools.r052_array_roles.audit import validate_spec as validate_r052_spec


SPEC_FINGERPRINT = "6f54881b88c33e8bab231d363601864c283d0223cd2ba1e5c881e62016a55348"
MASKS = ("off", "edge_local_only", "path_internal_only", "full")
CONDITION_PARENT = {"weakweak": "baseline", "startstrong": "start_edge", "goalstrong": "goal_edge"}
PARTITION = {
    "edge_local": (("p:0:0", "e:0"), ("p:0:1", "e:1")),
    "path_internal": (("p:0:1", "p:0:0"), ("goal", "p:0:1")),
}
TOLERANCE = {"abs_tol": 1e-12, "rel_tol": 1e-12}
FORBIDDEN = R050_FORBIDDEN | {
    "tools.r052_array_roles.worker",
    "tools.r053_feedback.worker",
}


def _close(left, right, tolerance=TOLERANCE):
    if type(left) is bool or type(right) is bool or left is None or right is None:
        return type(left) is type(right) and left == right
    if type(left) in (int, float) and type(right) in (int, float):
        return isclose(left, right, rel_tol=tolerance["rel_tol"], abs_tol=tolerance["abs_tol"])
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_close(left[key], right[key], tolerance) for key in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_close(a, b, tolerance) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def validate_spec(spec: dict) -> None:
    """Reject even a consistently resealed change to the frozen experiment contract."""
    require(fingerprint(spec) == SPEC_FINGERPRINT, "Exact frozen R053 spec")
    require(spec["frozen_before_research_execution"] is True, "Spec was not frozen")
    require(spec["numeric_comparison"] == TOLERANCE, "Numeric comparison drift")
    require([item["id"] for item in spec["conditions"]] == list(CONDITION_PARENT), "Condition matrix")
    require([item["id"] for item in spec["masks"]] == list(MASKS), "Mask matrix")
    require(len(spec["parent_files"]) == 10, "Pinned parent file count")


def _validate_program(program: dict, drives: dict, initial_state: dict, config: Config) -> None:
    require(isinstance(program, dict) and set(program) == {"edge_count", "groups", "links", "paths"},
            "Program fields")
    groups = program["groups"]
    require(isinstance(groups, list) and 0 < len(groups) <= config.max_groups, "Program groups")
    require(all(isinstance(group, dict) and set(group) == {"id", "level", "bias"}
                for group in groups), "Group fields")
    names = [group["id"] for group in groups]
    require(len(names) == len(set(names)) and "goal" in names, "Group identities")
    require(all(type(group["level"]) is int and group["level"] in (0, 1)
                and type(group["bias"]) in (int, float) and isfinite(group["bias"])
                for group in groups), "Group values")
    require(isinstance(program["links"], list), "Program links")
    require(all(isinstance(link, dict) and set(link) == {"source", "target", "weight", "kind"}
                and link["source"] in names and link["target"] in names
                and type(link["weight"]) in (int, float) and isfinite(link["weight"])
                and link["kind"] in ("support", "top_down") for link in program["links"]),
            "Link fields/values")
    require(type(program["edge_count"]) is int and 1 <= program["edge_count"] <= config.max_edges,
            "Edge count")
    require(isinstance(program["paths"], list) and 1 <= len(program["paths"]) <= config.max_paths,
            "Program paths")
    require(all(isinstance(path, list) and 1 <= len(path) <= config.max_path_length
                and len(path) == len(set(path))
                and all(type(slot) is int and 0 <= slot < program["edge_count"] for slot in path)
                for path in program["paths"]), "Path values")
    require(set(initial_state) == set(names)
            and all(type(value) in (int, float) and isfinite(value) and 0 <= value <= 1
                    for value in initial_state.values()), "Initial state")
    require(set(drives) <= set(names)
            and all(type(value) in (int, float) and isfinite(value) for value in drives.values()),
            "Drive values")


def verify_trajectory(program: dict, drives: dict, initial_state: dict, ticks: list,
                      final_state: dict, convergence: dict, cost: dict, config: dict) -> None:
    """Replay the synchronous recurrence and independently identify its first stop."""
    native_config = Config(**config)
    _validate_program(program, drives, initial_state, native_config)
    require(isinstance(ticks, list) and 0 < len(ticks) <= native_config.max_ticks, "Tick count")
    state = dict(initial_state)
    history = []
    stable = 0
    expected_convergence = None
    for ordinal, tick in enumerate(ticks, 1):
        require(isinstance(tick, dict) and set(tick) == {"tick", "state", "residual", "stable_steps"},
                "Tick fields")
        require(type(tick["tick"]) is int and tick["tick"] == ordinal, "Tick sequence")
        actual = independent_step(program, state, drives, native_config, True)
        require(_close(actual, tick["state"]), "Independent recurrence mismatch")
        residual = max(abs(actual[key] - state[key]) for key in state)
        require(_close(residual, tick["residual"]), "Residual mismatch")
        stable = stable + 1 if residual <= native_config.residual_tolerance else 0
        require(type(tick["stable_steps"]) is int and tick["stable_steps"] == stable,
                "Stable-step mismatch")
        margin = abs(2 * actual["goal"] - 1)
        status = None
        if stable >= native_config.patience:
            status = "stable_decision" if margin >= native_config.margin_threshold else "stable_ambiguous"
        elif history and residual > native_config.residual_tolerance * 10 \
                and max(abs(actual[key] - history[-1][key]) for key in actual) < native_config.residual_tolerance:
            status = "oscillating"
        if status is not None:
            require(ordinal == len(ticks), "Ticks recorded after first termination")
            expected_convergence = dict(status=status, ticks=ordinal, residual=residual,
                                        margin=margin, stable_steps=stable)
        history.append(state)
        history = history[-3:]
        state = dict(tick["state"])
    if expected_convergence is None:
        require(len(ticks) == native_config.max_ticks, "Trajectory stopped before a kernel terminal")
        expected_convergence = dict(status="budget_exhausted", ticks=native_config.max_ticks,
                                    residual=ticks[-1]["residual"],
                                    margin=abs(2 * state["goal"] - 1), stable_steps=stable)
    require(_close(final_state, state), "Final state mismatch")
    require(isinstance(convergence, dict)
            and set(convergence) == {"status", "ticks", "residual", "margin", "stable_steps"}
            and type(convergence["ticks"]) is int and type(convergence["stable_steps"]) is int
            and _close(convergence, expected_convergence), "Convergence mismatch")
    expected_cost = dict(
        kernel_ticks=len(ticks),
        group_updates=len(program["groups"]) * len(ticks),
        normalization_ops=len(program["groups"]) * len(ticks),
        signal_transmissions=len(program["links"]) * len(ticks),
    )
    require(set(cost) == set(expected_cost)
            and all(type(value) is int and value >= 0 for value in cost.values())
            and cost == expected_cost, "Kernel counters mismatch")


def _feedback_partition(program: dict) -> dict[str, list]:
    levels = {group["id"]: group["level"] for group in program["groups"]}
    support = {(link["source"], link["target"]) for link in program["links"]
               if link["kind"] == "support"}
    result = {"edge_local": [], "path_internal": []}
    seen = set()
    for link in program["links"]:
        if link["kind"] != "top_down":
            continue
        pair = (link["source"], link["target"])
        require(pair not in seen and levels[link["source"]] == 1
                and levels[link["target"]] in (0, 1), "Feedback identity/levels")
        require((link["target"], link["source"]) in support, "Feedback has no reverse support link")
        seen.add(pair)
        result["edge_local" if levels[link["target"]] == 0 else "path_internal"].append(pair)
    require({key: tuple(value) for key, value in result.items()} == PARTITION,
            "Exact feedback partition/order")
    return result


def verify_record(record: dict, condition: dict, mask: dict, network: dict,
                  parent_file_sha: str, config: dict) -> dict:
    raw = unseal(record, "hcc-r053-kernel-v1")
    expected_fields = {
        "schema", "condition", "mask", "parent_record_sha256", "source_program_digest",
        "program", "drives", "initial_state", "active_top_down_links",
        "removed_top_down_links", "top_down", "ticks", "final_state", "convergence", "cost",
        "counterfactual", "native_session_packet", "proof", "support", "raw_decision",
        "adoption", "actual_energy_joules", "termination_scope",
    }
    require(set(raw) == expected_fields, "Kernel record fields")
    require(condition == {"id": raw["condition"], "parent_label": CONDITION_PARENT[raw["condition"]]},
            "Condition binding")
    require(mask["id"] == raw["mask"] and mask["id"] in MASKS
            and set(mask) == {"id", "edge_local", "path_internal"}
            and type(mask["edge_local"]) is bool and type(mask["path_internal"]) is bool,
            "Mask binding")
    require(raw["parent_record_sha256"] == parent_file_sha, "Parent record binding")
    original = network["program"]
    _feedback_partition(original)
    require(raw["source_program_digest"] == fingerprint(original), "Source program digest")
    active, removed, kept = [], [], []
    levels = {group["id"]: group["level"] for group in original["groups"]}
    for link in original["links"]:
        if link["kind"] == "top_down":
            category = "edge_local" if levels[link["target"]] == 0 else "path_internal"
            if not mask[category]:
                removed.append(link)
                continue
            active.append(link)
        kept.append(link)
    expected_program = {**original, "links": kept}
    require(raw["program"] == expected_program, "Only the fixed feedback mask may change the program")
    require(raw["active_top_down_links"] == active and raw["removed_top_down_links"] == removed,
            "Feedback mask receipt/order")
    require(raw["drives"] == network["drives"], "Drives changed")
    expected_initial = {group["id"]: 0.5 for group in original["groups"]}
    require(raw["initial_state"] == expected_initial, "Initial state changed")
    require(raw["top_down"] is True and raw["counterfactual"] is True
            and raw["termination_scope"] == "counterfactual_kernel_termination", "Kernel scope")
    require(all(raw[key] is None for key in ("native_session_packet", "proof", "support",
                                              "raw_decision", "adoption", "actual_energy_joules")),
            "Unmeasured native/outcome claim")
    verify_trajectory(raw["program"], raw["drives"], raw["initial_state"], raw["ticks"],
                      raw["final_state"], raw["convergence"], raw["cost"], config)
    return {key: raw[key] for key in ("condition", "mask", "final_state", "convergence", "cost")}


def _parent_path(label: str, case_id: str) -> str:
    return (f"study/baselines/{case_id}.json" if label == "baseline"
            else f"study/raw/{case_id}/{label}.json")


def _parent_trajectory(execution: dict) -> dict:
    events = execution["packet"]["document"]["events"]
    networks = [event["payload"] for event in events if event["event"] == "r02_network"]
    ticks = [event["payload"] for event in events if event["event"] == "r02_tick"]
    settled = [event["payload"] for event in events if event["event"] == "r02_settled"]
    require(len(networks) == len(settled) == 1 and bool(ticks), "Exactly one R02 network/settlement")
    network, terminal = networks[0], settled[0]
    require(all(tick["network_id"] == network["network_id"]
                and tick["decision_id"] == network["decision_id"] for tick in ticks),
            "Parent tick/network binding")
    require(terminal["network_id"] == network["network_id"]
            and terminal["decision_id"] == network["decision_id"]
            and terminal["convergence"]["ticks"] == len(ticks), "Parent settlement binding")
    pending = execution["packet"]["document"]["engine"]["pending"]
    require(_close(pending["state"], terminal["state"])
            and _close(pending["convergence"], terminal["convergence"]), "Parent pending/settled mismatch")
    return dict(
        network=network,
        ticks=[{key: tick[key] for key in ("tick", "state", "residual", "stable_steps")} for tick in ticks],
        final_state=terminal["state"], convergence=terminal["convergence"],
        cost={key: pending["cost"][key] for key in
              ("kernel_ticks", "group_updates", "normalization_ops", "signal_transmissions")},
    )


def _verify_parent(run: Path, spec: dict) -> tuple[dict, dict]:
    require(files(run / "parents") == spec["parent_files"], "Pinned parent inventory/hash")
    parent_plan_packet = load(run / "parents/plan.json")
    parent_plan = unseal(parent_plan_packet, "hcc-r052-plan-v1")
    parent_source = load(run / "parents/source_manifest.json")
    parent_raw = load(run / "parents/raw_manifest.json")
    parent_audit = load(run / "parents/analysis/audit.json")
    require(parent_source["schema"] == "hcc-r052-source-manifest-v1"
            and parent_plan["source_manifest_sha256"] == sha((run / "parents/source_manifest.json").read_bytes()),
            "Parent plan/source binding")
    require(parent_raw["schema"] == "hcc-r052-raw-manifest-v1", "Parent raw manifest schema")
    require(parent_audit["schema"] == "hcc-r052-audit-v1" and parent_audit["verified"] is True
            and parent_audit["research_experiment"] is True
            and parent_audit["plan_sha256"] == parent_plan_packet["sha256"], "Parent audit/plan binding")
    validate_r052_spec(parent_plan["spec"])
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.model import AdaptiveConfig
    require(parent_plan["config"] == parent_plan["spec"]["config"] == codec.plain(AdaptiveConfig())
            and parent_plan["empty_memory"] == AdaptiveMemory.empty(AdaptiveConfig()).document(),
            "Parent default config/memory")
    verifier = NativeVerifier(parent_plan)
    by_condition, by_case = {}, {}
    cases = {case["id"]: case for case in parent_plan["spec"]["cases"]}
    for case_id in ("r052-c000", "r052-c001"):
        case = cases[case_id]
        require(case["top_down"] is (case_id == "r052-c001"), "Pinned bridge case switch")
        baseline_path = _parent_path("baseline", case_id)
        baseline_packet = load(run / "parents" / baseline_path)
        baseline = unseal(baseline_packet, "hcc-r052-baseline-v1")
        require(set(baseline) == {"schema", "case", "execution"} and baseline["case"] == case,
                "Parent baseline fields/case")
        raw_key = baseline_path.removeprefix("study/")
        require(parent_raw["files"].get(raw_key) == spec["parent_files"][baseline_path],
                "Parent baseline/raw-manifest binding")
        verifier.execution(baseline["execution"], case, case["observation"], 0, "baseline")
        by_case[(case_id, "baseline")] = _parent_trajectory(baseline["execution"])
        for label in ("start_edge", "goal_edge"):
            path = _parent_path(label, case_id)
            packet = load(run / "parents" / path)
            raw = validate_r052_record(packet, baseline_packet, case, label)
            require(parent_raw["files"].get(path.removeprefix("study/")) == spec["parent_files"][path],
                    "Parent arm/raw-manifest binding")
            verifier.execution(raw["execution"], case, raw["observation"], 1, label)
            by_case[(case_id, label)] = _parent_trajectory(raw["execution"])
    for condition, label in CONDITION_PARENT.items():
        left, right = by_case[("r052-c000", label)], by_case[("r052-c001", label)]
        require(left["network"]["program"] == right["network"]["program"]
                and left["network"]["drives"] == right["network"]["drives"],
                "Bridge pair changed non-feedback inputs")
        by_condition[condition] = right["network"]
    return by_condition, by_case


def _bridge(condition: str, mask: str, record: dict, parent: dict, case_id: str) -> dict:
    checks = dict(
        tick_trajectory_close=_close(record["ticks"], parent["ticks"]),
        final_state_close=_close(record["final_state"], parent["final_state"]),
        convergence_close=_close(record["convergence"], parent["convergence"]),
        counters_equal=record["cost"] == parent["cost"],
    )
    require(all(checks.values()), f"R052 numerical bridge failed: {condition}/{mask}")
    return dict(condition=condition, mask=mask, parent_case=case_id,
                parent_label=CONDITION_PARENT[condition], **checks, verified=True)


def _factorial(rows: list[dict]) -> list[dict]:
    effects = []
    for condition in CONDITION_PARENT:
        cells = {row["mask"]: row for row in rows if row["condition"] == condition}
        if not cells:
            continue
        require(set(cells) == set(MASKS), "Incomplete factorial cells")
        coordinates = {}
        for coordinate in ("goal", "e:0", "e:1"):
            values = {mask: cells[mask]["final_state"][coordinate] for mask in MASKS}
            coordinates[coordinate] = dict(
                **{
                    "E|P0": values["edge_local_only"] - values["off"],
                    "E|P1": values["full"] - values["path_internal_only"],
                    "P|E0": values["path_internal_only"] - values["off"],
                    "P|E1": values["full"] - values["edge_local_only"],
                },
                edge_local=((values["edge_local_only"] - values["off"])
                            + (values["full"] - values["path_internal_only"])) / 2,
                path_internal=((values["path_internal_only"] - values["off"])
                               + (values["full"] - values["edge_local_only"])) / 2,
                interaction=(values["full"] - values["edge_local_only"]
                             - values["path_internal_only"] + values["off"]),
            )
        effects.append(dict(condition=condition, signed_effects=coordinates))
    return effects


def audit(run: Path) -> dict:
    source_manifest = load(run / "source_manifest.json")
    require(set(source_manifest) == {"schema", "files", "parent_commit", "checkout_commit"}
            and source_manifest["schema"] == "hcc-r053-source-manifest-v1"
            and files(run / "source") == source_manifest["files"], "Frozen source inventory/hash")
    require(git_tree(run / "source/src") == SRC_TREE and git_tree(run / "source/tests") == TEST_TREE,
            "Core/test tree drift")
    plan_packet = load(run / "plan.json")
    plan = unseal(plan_packet, "hcc-r053-plan-v1")
    require(set(plan) == {"schema", "purpose", "spec", "config", "source_manifest_sha256",
                          "created_at_utc", "automatic_retry"}, "Plan fields")
    require(plan["source_manifest_sha256"] == sha((run / "source_manifest.json").read_bytes())
            and plan["automatic_retry"] is False, "Plan/source/retry binding")
    spec_path = run / "source/experiments/exp-34-feedback-factorial/frozen_spec.json"
    spec = load(spec_path)
    require(plan["spec"] == spec, "Plan/spec binding")
    validate_spec(spec)
    from hcr import codec
    require(fingerprint(plan["config"]) == fingerprint(codec.plain(Config())), "Exact default kernel config")
    require(plan["purpose"] in ("implementation_validation", "research"), "Purpose")
    conditions = (spec["implementation_validation_conditions"] if
                  plan["purpose"] == "implementation_validation" else spec["research_conditions"])
    require(conditions == (["weakweak"] if plan["purpose"] == "implementation_validation"
                           else list(CONDITION_PARENT)), "Purpose/condition matrix")
    root = run / ("smoke" if plan["purpose"] == "implementation_validation" else "study")
    raw_manifest = load(run / "raw_manifest.json")
    require(set(raw_manifest) == {"schema", "files"}
            and raw_manifest["schema"] == "hcc-r053-raw-manifest-v1"
            and files(root) == raw_manifest["files"], "Raw inventory/hash")
    expected_names = {f"{condition}/{mask}.json" for condition in conditions for mask in MASKS}
    require(set(files(root)) == expected_names, "Raw branch inventory")
    networks, parents = _verify_parent(run, spec)
    condition_specs = {item["id"]: item for item in spec["conditions"]}
    mask_specs = {item["id"]: item for item in spec["masks"]}
    rows, records = [], {}
    for condition in conditions:
        label = CONDITION_PARENT[condition]
        parent_path = run / "parents" / _parent_path(label, "r052-c001")
        for mask in MASKS:
            record = unseal(load(root / condition / (mask + ".json")), "hcc-r053-kernel-v1")
            packet = {**record, "sha256": fingerprint(record)}
            rows.append(verify_record(packet, condition_specs[condition], mask_specs[mask],
                                      networks[condition], sha(parent_path.read_bytes()), plan["config"]))
            records[(condition, mask)] = record
    bridges = []
    for condition in conditions:
        label = CONDITION_PARENT[condition]
        bridges.append(_bridge(condition, "off", records[(condition, "off")],
                               parents[("r052-c000", label)], "r052-c000"))
        bridges.append(_bridge(condition, "full", records[(condition, "full")],
                               parents[("r052-c001", label)], "r052-c001"))
    require(not (FORBIDDEN & set(sys.modules)), "Auditor imported producer/runtime/session/dynamics")
    research = plan["purpose"] == "research"
    return dict(schema="hcc-r053-audit-v1", verified=True, purpose=plan["purpose"],
                research_experiment=research, plan_sha256=plan_packet["sha256"], rows=rows,
                bridges=bridges, factorial_effects=_factorial(rows), independent_samples=False,
                native_outcomes_measured=False)


def render_summary(report: dict) -> bytes:
    require(report["verified"] is True, "Verified audit required for summary")
    lines = [
        "# EXP-34 / R053 feedback factorial", "", f"실행 목적: {report['purpose']}", "",
        "| condition | mask | goal | e:0 | e:1 | ticks | transmissions |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        state, cost = row["final_state"], row["cost"]
        lines.append("| " + " | ".join(map(str, (
            row["condition"], row["mask"], state["goal"], state["e:0"], state["e:1"],
            cost["kernel_ticks"], cost["signal_transmissions"],
        ))) + " |")
    lines += [
        "", f"R052 numerical bridge {len(report['bridges'])}개가 모두 통과했다.",
        "이 표는 counterfactual numerical kernel 결과이며 native proof, support, adoption은 측정하지 않았다.",
        "결정론적 분기들은 독립 표본이 아니다.", "",
    ]
    return "\n".join(lines).encode("utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args(argv)
    report = audit(args.run)
    dump(args.run / "analysis/audit.json", report)
    publish(args.run / "analysis/summary.ko.md", render_summary(report))
    print("VERIFIED:", len(report["rows"]), "counterfactual kernels /",
          len(report["bridges"]), "R052 bridges", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
