"""Analytic one-step Jacobian; no numerical differentiation or new dependencies."""
from math import exp


def jacobian(program, state, drives, config, coordinates):
    damping, temperature = config['damping'], config['temperature']
    excitation = config['self_excitation'] + config['inhibition']
    matrix = []
    groups = {g['id']: g for g in program['groups']}
    for target in coordinates:
        incoming = [link for link in program['links'] if link['target'] == target]
        drive = groups[target]['bias'] + drives.get(target, 0.0)
        drive += sum(link['weight'] * (2 * state[link['source']] - 1) for link in incoming)
        z = (2 * drive + excitation * (2 * state[target] - 1)) / temperature
        p = 1 / (1 + exp(-z)) if z >= 0 else exp(z) / (1 + exp(z))
        row = []
        for source in coordinates:
            slope = 4 * sum(link['weight'] for link in incoming if link['source'] == source)
            if source == target:
                slope += 2 * excitation
            row.append((1 - damping if source == target else 0) + damping * p * (1 - p) * slope / temperature)
        matrix.append(row)
    return matrix
