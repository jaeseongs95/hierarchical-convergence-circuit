from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from hcr.evaluation.audit import independent_step
from hcr.model import Config
from tools.r050_review_boundary.common import IntegrityError, fingerprint, seal, sha
from tools.r053_feedback.tests.test_audit import CONFIG, original_program
from tools.r055_allocation.audit import (
    CONDITIONS,
    ORIGINAL_DRIVES,
    _bridge,
    _require_inventory,
    allocation_comparisons,
    classify_endpoint,
    mirrored_contrasts,
    validate_spec,
    verify_record,
)


CONDITION = {"id": "startstrong", "input_pair": [1.0, 0.02],
             "drives": dict(ORIGINAL_DRIVES)}
FULL = {"id": "full", "remove": []}


def _trajectory(program, drives, initial):
    config = Config(**CONFIG)
    state, stable, history, ticks, convergence = dict(initial), 0, [], [], None
    for number in range(1, config.max_ticks + 1):
        nxt = independent_step(program, state, drives, config, True)
        residual = max(abs(nxt[key] - state[key]) for key in state)
        stable = stable + 1 if residual <= config.residual_tolerance else 0
        ticks.append({"tick": number, "state": nxt, "residual": residual,
                      "stable_steps": stable})
        margin = abs(2 * nxt["goal"] - 1)
        if stable >= config.patience:
            convergence = {"status": "stable_decision" if margin >= config.margin_threshold
                           else "stable_ambiguous", "ticks": number, "residual": residual,
                           "margin": margin, "stable_steps": stable}
        elif history and residual > config.residual_tolerance * 10 \
                and max(abs(nxt[key] - history[-1][key]) for key in nxt) \
                < config.residual_tolerance:
            convergence = {"status": "oscillating", "ticks": number, "residual": residual,
                           "margin": margin, "stable_steps": stable}
        history = (history + [state])[-3:]
        state = nxt
        if convergence:
            break
    if convergence is None:
        convergence = {"status": "budget_exhausted", "ticks": config.max_ticks,
                       "residual": ticks[-1]["residual"],
                       "margin": abs(2 * state["goal"] - 1), "stable_steps": stable}
    cost = {"kernel_ticks": len(ticks), "group_updates": len(program["groups"]) * len(ticks),
            "normalization_ops": len(program["groups"]) * len(ticks),
            "signal_transmissions": len(program["links"]) * len(ticks)}
    return dict(ticks=ticks, final_state=state, convergence=convergence, cost=cost)


def record_fixture(mask=FULL):
    original = original_program()
    removed_ids = set(mask["remove"])
    identities = {
        ("p:0:0", "e:0"): "E_start", ("p:0:1", "e:1"): "E_goal",
        ("p:0:1", "p:0:0"): "P_prefix", ("goal", "p:0:1"): "P_goal",
    }
    active, removed, kept = [], [], []
    for link in original["links"]:
        if link["kind"] == "top_down":
            if identities[(link["source"], link["target"])] in removed_ids:
                removed.append(link)
                continue
            active.append(link)
        kept.append(link)
    program = {**original, "links": kept}
    initial = {group["id"]: 0.5 for group in original["groups"]}
    body = dict(
        schema="hcc-r055-kernel-v1", condition="startstrong", mask=mask["id"],
        input_pair=[1.0, 0.02], original_drives=dict(ORIGINAL_DRIVES),
        parent_record_sha256="a" * 64, source_program_digest=fingerprint(original),
        program=program, drives=dict(ORIGINAL_DRIVES), initial_state=initial, top_down=True,
        active_top_down_links=active, removed_top_down_links=removed, counterfactual=True,
        native_session_packet=None, proof=None, support=None, raw_decision=None, adoption=None,
        actual_energy_joules=None, termination_scope="counterfactual_kernel_termination",
        **_trajectory(program, ORIGINAL_DRIVES, initial),
    )
    return seal(body), original


def comparison_rows():
    rows = []
    for index, (condition, (pair, _)) in enumerate(CONDITIONS.items()):
        full_goal = 0.1 + index * 0.01
        dropout_goal = (0.8 if index == 0 else 0.2 + index * 0.01)
        dropout_status = "budget_exhausted" if condition == "balanced" else "stable_decision"
        for mask, goal, status, offset in (
            ("full", full_goal, "stable_decision", 0.0),
            ("drop_P_prefix", dropout_goal, dropout_status, 0.1),
        ):
            rows.append({"condition": condition, "mask": mask, "input_pair": pair,
                         "final_state": {"goal": goal, "e:0": 0.3 + offset,
                                         "e:1": 0.7 - offset},
                         "convergence": {"status": status}, "cost": {}})
    return rows


class AuditTests(unittest.TestCase):
    def test_valid_record_and_resealed_boundary_tampering(self):
        packet, original = record_fixture()
        row = verify_record(packet, CONDITION, FULL, original, "a" * 64, CONFIG)
        self.assertEqual(set(row), {"condition", "mask", "input_pair", "final_state",
                                    "convergence", "cost"})

        changes = {
            "drives": lambda body: body["drives"].update({"e:0": 3.9}),
            "native_claim": lambda body: body.update(proof={}),
            "mask": lambda body: body.update(mask="drop_P_prefix"),
            "source": lambda body: body.update(source_program_digest="b" * 64),
            "input_metadata": lambda body: body.update(input_pair=[0.99, 0.03]),
            "program": lambda body: body["program"]["links"].pop(),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                altered = {key: deepcopy(value) for key, value in packet.items()
                           if key != "sha256"}
                change(altered)
                with self.assertRaises(IntegrityError):
                    verify_record(seal(altered), CONDITION, FULL, original, "a" * 64, CONFIG)

    def test_original_drive_and_parent_receipts(self):
        packet, original = record_fixture()
        body = {key: deepcopy(value) for key, value in packet.items() if key != "sha256"}
        body["original_drives"]["e:0"] = 3.9
        with self.assertRaises(IntegrityError):
            verify_record(seal(body), CONDITION, FULL, original, "a" * 64, CONFIG)
        with self.assertRaises(IntegrityError):
            verify_record(packet, CONDITION, FULL, original, "b" * 64, CONFIG)

    def test_endpoint_guard_and_nonstable_termination(self):
        self.assertEqual(classify_endpoint(0.499998, "stable_decision"), "low")
        self.assertEqual(classify_endpoint(0.500002, "stable_ambiguous"), "high")
        self.assertEqual(classify_endpoint(0.499999, "stable_decision"), "inconclusive")
        self.assertEqual(classify_endpoint(0.500001, "stable_decision"), "inconclusive")
        self.assertEqual(classify_endpoint(0.1, "budget_exhausted"), "inconclusive")

    def test_continuous_comparisons_and_mirrored_contrasts(self):
        comparisons = allocation_comparisons(comparison_rows())
        by_condition = {item["condition"]: item for item in comparisons}
        self.assertIs(by_condition["startstrong"]["necessary_for_low_endpoint"], True)
        self.assertIs(by_condition["startlean"]["necessary_for_low_endpoint"], False)
        self.assertIsNone(by_condition["balanced"]["necessary_for_low_endpoint"])
        self.assertAlmostEqual(by_condition["startstrong"]["delta_e0"], 0.1)
        self.assertAlmostEqual(by_condition["startstrong"]["delta_e1"], -0.1)

        contrasts = mirrored_contrasts(comparisons)
        self.assertEqual(len(contrasts), 2)
        self.assertEqual(contrasts[0]["status"], "nondirectional")
        self.assertAlmostEqual(
            contrasts[0]["difference"],
            by_condition["goalstrong"]["delta_goal"]
            - by_condition["startstrong"]["delta_goal"],
        )
        altered = deepcopy(comparisons)
        altered.pop()
        with self.assertRaises(IntegrityError):
            mirrored_contrasts(altered)

    def test_bridge_includes_drive_and_full_numerical_receipts(self):
        packet, _ = record_fixture()
        record = {key: deepcopy(value) for key, value in packet.items() if key != "sha256"}
        result = _bridge("startstrong", "full", record, deepcopy(record))
        self.assertTrue(result["verified"])
        anchor = deepcopy(record)
        anchor["drives"]["e:0"] = 3.9
        with self.assertRaises(IntegrityError):
            _bridge("startstrong", "full", record, anchor)

    def test_inventory_rejects_hash_drift_and_missing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            anchor = root / "study/startstrong/full.json"
            anchor.parent.mkdir(parents=True)
            anchor.write_bytes(b"anchor")
            expected = {"study/startstrong/full.json": sha(b"anchor")}
            _require_inventory(root, expected, "anchor")
            anchor.write_bytes(b"changed")
            with self.assertRaises(IntegrityError):
                _require_inventory(root, expected, "anchor")
            anchor.unlink()
            with self.assertRaises(IntegrityError):
                _require_inventory(root, expected, "anchor")

    def test_frozen_spec_rejects_resealed_semantic_change(self):
        path = Path(__file__).parents[3] / "experiments/exp-36-drive-allocation/frozen_spec.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        validate_spec(spec)
        spec["conditions"][1]["drives"]["e:0"] = 3.01
        with self.assertRaises(IntegrityError):
            validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
