from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.r050_review_boundary.common import IntegrityError, seal, sha
from tools.r053_feedback.tests.test_audit import CONFIG, record_fixture as r053_record_fixture
from tools.r054_links.audit import (
    _require_inventory,
    classify_endpoint,
    dropout_comparisons,
    prediction_results,
    validate_spec,
    verify_record,
)


CONDITION = {"id": "startstrong", "parent_label": "start_edge"}
FULL = {"id": "full", "remove": []}


def record_fixture():
    packet, _, _, network = r053_record_fixture()
    body = {key: deepcopy(value) for key, value in packet.items() if key != "sha256"}
    body.update(schema="hcc-r054-kernel-v1", condition="startstrong", mask="full")
    return seal(body), network


def comparison_rows():
    values = {
        "full": (0.1, 0.2, "stable_decision"),
        "off": (0.9, 0.7, "stable_decision"),
        "drop_E_start": (0.2, 0.3, "stable_ambiguous"),
        "drop_E_goal": (0.8, 0.6, "stable_decision"),
        "drop_P_prefix": (0.3, 0.4, "budget_exhausted"),
        "drop_P_goal": (0.499999, 0.5, "stable_decision"),
    }
    return [
        {"condition": "startstrong", "mask": mask,
         "final_state": {"goal": goal, "e:0": 0.9, "e:1": weak},
         "convergence": {"status": status}, "cost": {}}
        for mask, (goal, weak, status) in values.items()
    ]


class AuditTests(unittest.TestCase):
    def test_valid_record_and_resealed_boundary_tampering(self):
        packet, network = record_fixture()
        row = verify_record(packet, CONDITION, FULL, network, "a" * 64, CONFIG)
        self.assertEqual(set(row), {"condition", "mask", "final_state", "convergence", "cost"})

        changes = {
            "mask": lambda body: body.update(mask="drop_E_start"),
            "receipt": lambda body: body["removed_top_down_links"].append(
                body["active_top_down_links"][0]),
            "drive": lambda body: body["drives"].update({"e:0": 0.2}),
            "initial": lambda body: body["initial_state"].update({"goal": 0.4}),
            "native_claim": lambda body: body.update(proof={}),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                altered = {key: deepcopy(value) for key, value in packet.items() if key != "sha256"}
                change(altered)
                with self.assertRaises(IntegrityError):
                    verify_record(seal(altered), CONDITION, FULL, network, "a" * 64, CONFIG)

    def test_wrong_mask_argument_and_parent_binding(self):
        packet, network = record_fixture()
        with self.assertRaises(IntegrityError):
            verify_record(packet, CONDITION, {"id": "drop_E_start", "remove": ["E_start"]},
                          network, "a" * 64, CONFIG)
        with self.assertRaises(IntegrityError):
            verify_record(packet, CONDITION, FULL, network, "b" * 64, CONFIG)

    def test_endpoint_threshold_band_and_nonstable_termination(self):
        self.assertEqual(classify_endpoint(0.499998, "stable_decision"), "low")
        self.assertEqual(classify_endpoint(0.500002, "stable_ambiguous"), "high")
        self.assertEqual(classify_endpoint(0.499999, "stable_decision"), "inconclusive")
        self.assertEqual(classify_endpoint(0.500001, "stable_decision"), "inconclusive")
        self.assertEqual(classify_endpoint(0.1, "budget_exhausted"), "inconclusive")

    def test_continuous_comparisons_necessity_and_predictions(self):
        comparisons = {item["mask"]: item for item in dropout_comparisons(comparison_rows())}
        self.assertEqual(len(comparisons), 4)
        self.assertIs(comparisons["drop_E_goal"]["necessary_for_low_endpoint"], True)
        self.assertIs(comparisons["drop_E_start"]["necessary_for_low_endpoint"], False)
        self.assertIsNone(comparisons["drop_P_prefix"]["necessary_for_low_endpoint"])
        self.assertAlmostEqual(comparisons["drop_P_prefix"]["delta_goal"], 0.2)
        self.assertEqual(comparisons["drop_P_prefix"]["dropout_regime"], "inconclusive")
        predictions = {(item["id"], item["condition"]): item
                       for item in prediction_results(comparison_rows())}
        self.assertEqual(predictions[("P1", "startstrong")]["status"], "support")
        self.assertEqual(predictions[("P2", "startstrong")]["status"], "support")
        self.assertEqual(predictions[("P3", "startstrong")]["status"], "nondirectional")

    def test_inventory_rejects_missing_and_anchor_hash_drift(self):
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
        path = Path(__file__).parents[3] / "experiments/exp-35-feedback-links/frozen_spec.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        validate_spec(spec)
        spec["endpoint_rule"]["abstention_band"] = 0.01
        with self.assertRaises(IntegrityError):
            validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
