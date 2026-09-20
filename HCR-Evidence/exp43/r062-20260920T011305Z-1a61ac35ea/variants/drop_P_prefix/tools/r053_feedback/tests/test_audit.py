from copy import deepcopy
import json
from pathlib import Path
import unittest

from hcr.evaluation.audit import independent_step
from hcr.model import Config
from tools.r050_review_boundary.common import IntegrityError, fingerprint, seal
from tools.r053_feedback.audit import validate_spec, verify_record, verify_trajectory


CONFIG = {
    "evidence_gain": 4.0, "relation_gain": 2.0, "top_down_gain": 0.35,
    "prior_gain": 2.0, "self_excitation": 0.25, "inhibition": 0.2,
    "damping": 0.45, "temperature": 1.0, "residual_tolerance": 1e-6,
    "margin_threshold": 0.3, "patience": 4, "max_ticks": 160,
    "max_edges": 8, "max_paths": 4, "max_path_length": 4, "max_groups": 32,
    "max_search": 2048, "min_valid_episodes": 3, "max_circuits": 16,
    "weakening": 0.2, "learning_rate": 0.25, "max_observation_requests": 2,
}


def one_group_trace():
    program = {"edge_count": 1, "groups": [{"id": "goal", "level": 1, "bias": 0.0}],
               "links": [], "paths": [[0]]}
    ticks = [{"tick": number, "state": {"goal": 0.5}, "residual": 0.0,
              "stable_steps": number} for number in range(1, 5)]
    convergence = {"status": "stable_ambiguous", "ticks": 4, "residual": 0.0,
                   "margin": 0.0, "stable_steps": 4}
    cost = {"kernel_ticks": 4, "group_updates": 4, "normalization_ops": 4,
            "signal_transmissions": 0}
    return program, {}, {"goal": 0.5}, ticks, {"goal": 0.5}, convergence, cost


def original_program():
    groups = [
        {"id": "e:0", "level": 0, "bias": 0.0},
        {"id": "e:1", "level": 0, "bias": 0.0},
        {"id": "p:0:0", "level": 1, "bias": 0.0},
        {"id": "p:0:1", "level": 1, "bias": -2.0},
        {"id": "goal", "level": 1, "bias": 0.0},
    ]
    links = []
    for source, target in (("e:0", "p:0:0"), ("e:1", "p:0:1"),
                           ("p:0:0", "p:0:1"), ("p:0:1", "goal")):
        links += [{"source": source, "target": target, "weight": 2.0, "kind": "support"},
                  {"source": target, "target": source, "weight": 0.35, "kind": "top_down"}]
    return {"edge_count": 2, "groups": groups, "links": links, "paths": [[0, 1]]}


def record_fixture(mask=None):
    mask = mask or {"id": "full", "edge_local": True, "path_internal": True}
    original = original_program()
    levels = {group["id"]: group["level"] for group in original["groups"]}
    active, removed, kept = [], [], []
    for link in original["links"]:
        if link["kind"] == "top_down":
            category = "edge_local" if levels[link["target"]] == 0 else "path_internal"
            if not mask[category]:
                removed.append(link)
                continue
            active.append(link)
        kept.append(link)
    program = {**original, "links": kept}
    drives = {"e:0": 0.08, "e:1": 0.08, "goal": 0.0}
    initial = {group["id"]: 0.5 for group in original["groups"]}
    state, stable, history, ticks = dict(initial), 0, [], []
    config = Config(**CONFIG)
    convergence = None
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
                and max(abs(nxt[key] - history[-1][key]) for key in nxt) < config.residual_tolerance:
            convergence = {"status": "oscillating", "ticks": number, "residual": residual,
                           "margin": margin, "stable_steps": stable}
        history.append(state)
        history = history[-3:]
        state = nxt
        if convergence:
            break
    if convergence is None:
        convergence = {"status": "budget_exhausted", "ticks": config.max_ticks,
                       "residual": ticks[-1]["residual"], "margin": abs(2 * state["goal"] - 1),
                       "stable_steps": stable}
    body = {
        "schema": "hcc-r053-kernel-v1", "condition": "weakweak", "mask": mask["id"],
        "parent_record_sha256": "a" * 64,
        "source_program_digest": fingerprint(original),
        "program": program, "drives": drives, "initial_state": initial,
        "active_top_down_links": active, "removed_top_down_links": removed, "top_down": True,
        "ticks": ticks, "final_state": state, "convergence": convergence,
        "cost": {"kernel_ticks": len(ticks), "group_updates": 5 * len(ticks),
                 "normalization_ops": 5 * len(ticks),
                 "signal_transmissions": len(kept) * len(ticks)},
        "counterfactual": True, "native_session_packet": None, "proof": None, "support": None,
        "raw_decision": None, "adoption": None, "actual_energy_joules": None,
        "termination_scope": "counterfactual_kernel_termination",
    }
    network = {"program": original, "drives": drives}
    condition = {"id": "weakweak", "parent_label": "baseline"}
    return seal(body), condition, mask, network


class AuditTests(unittest.TestCase):
    def test_handmade_single_group_trace_and_termination_tampering(self):
        values = one_group_trace()
        verify_trajectory(*values, CONFIG)

        early = list(deepcopy(values))
        early[3].pop()
        early[4] = early[3][-1]["state"]
        early[5] = {**early[5], "ticks": 3, "stable_steps": 3}
        early[6] = {**early[6], "kernel_ticks": 3, "group_updates": 3,
                    "normalization_ops": 3}
        with self.assertRaises(IntegrityError):
            verify_trajectory(*early, CONFIG)

        extra = list(deepcopy(values))
        extra[3].append({"tick": 5, "state": {"goal": 0.5}, "residual": 0.0,
                         "stable_steps": 5})
        extra[4] = extra[3][-1]["state"]
        extra[5] = {**extra[5], "ticks": 5, "stable_steps": 5}
        extra[6] = {"kernel_ticks": 5, "group_updates": 5, "normalization_ops": 5,
                    "signal_transmissions": 0}
        with self.assertRaises(IntegrityError):
            verify_trajectory(*extra, CONFIG)

    def test_trajectory_tampering(self):
        changes = [
            (3, lambda value: value[0].update(state={"goal": 0.6})),
            (3, lambda value: value[0].update(residual=0.1)),
            (2, lambda value: value.update(goal=0.4)),
            (6, lambda value: value.update(kernel_ticks=5)),
        ]
        for index, change in changes:
            with self.subTest(index=index, change=change):
                values = list(deepcopy(one_group_trace()))
                change(values[index])
                with self.assertRaises(IntegrityError):
                    verify_trajectory(*values, CONFIG)

    def test_budget_and_oscillation_termination(self):
        program = {"edge_count": 1,
                   "groups": [{"id": "goal", "level": 1, "bias": 0.0}],
                   "links": [], "paths": [[0]]}
        budget_config = {**CONFIG, "damping": 0.5, "self_excitation": 0.0,
                         "inhibition": 0.0, "max_ticks": 4, "patience": 4}
        states = (0.75, 0.875, 0.9375, 0.96875)
        residuals = (0.25, 0.125, 0.0625, 0.03125)
        ticks = [{"tick": number, "state": {"goal": state}, "residual": residual,
                  "stable_steps": 0}
                 for number, (state, residual) in enumerate(zip(states, residuals), 1)]
        verify_trajectory(program, {"goal": 1e6}, {"goal": 0.5}, ticks,
                          {"goal": states[-1]},
                          {"status": "budget_exhausted", "ticks": 4,
                           "residual": residuals[-1], "margin": 0.9375, "stable_steps": 0},
                          {"kernel_ticks": 4, "group_updates": 4, "normalization_ops": 4,
                           "signal_transmissions": 0}, budget_config)

        oscillating = {**program, "links": [
            {"source": "goal", "target": "goal", "weight": -1e6, "kind": "support"}]}
        oscillation_config = {**CONFIG, "damping": 1.0, "self_excitation": 0.0,
                              "inhibition": 0.0, "max_ticks": 4, "patience": 4}
        oscillation_ticks = [
            {"tick": 1, "state": {"goal": 0.0}, "residual": 1.0, "stable_steps": 0},
            {"tick": 2, "state": {"goal": 1.0}, "residual": 1.0, "stable_steps": 0},
        ]
        verify_trajectory(oscillating, {}, {"goal": 1.0}, oscillation_ticks,
                          {"goal": 1.0},
                          {"status": "oscillating", "ticks": 2, "residual": 1.0,
                           "margin": 1.0, "stable_steps": 0},
                          {"kernel_ticks": 2, "group_updates": 2, "normalization_ops": 2,
                           "signal_transmissions": 2}, oscillation_config)

    def test_record_accepts_valid_packet(self):
        packet, condition, mask, network = record_fixture()
        row = verify_record(packet, condition, mask, network, "a" * 64, CONFIG)
        self.assertEqual(set(row), {"condition", "mask", "final_state", "convergence", "cost"})

    def test_resealed_record_tampering(self):
        changes = [
            lambda body: body["program"]["links"].pop(),
            lambda body: body["drives"].update({"e:0": 0.2}),
            lambda body: body["initial_state"].update({"goal": 0.4}),
            lambda body: body.update(proof={}),
            lambda body: body["removed_top_down_links"].append(body["active_top_down_links"][0]),
        ]
        for change in changes:
            with self.subTest(change=change):
                packet, condition, mask, network = record_fixture()
                body = {key: deepcopy(value) for key, value in packet.items() if key != "sha256"}
                change(body)
                with self.assertRaises(IntegrityError):
                    verify_record(seal(body), condition, mask, network, "a" * 64, CONFIG)

    def test_frozen_spec_rejects_resealed_semantic_change(self):
        path = Path(__file__).parents[3] / "experiments/exp-34-feedback-factorial/frozen_spec.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        validate_spec(spec)
        spec["initial_activation"] = 0.4
        with self.assertRaises(IntegrityError):
            validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
