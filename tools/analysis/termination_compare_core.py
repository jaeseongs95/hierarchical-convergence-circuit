"""고정 실수 모델의 순차 구간·종료 정책. world/future/파일 인수가 숫자 API에 없다."""
from __future__ import annotations
import ast
import builtins
from fractions import Fraction as Q
import hashlib
import json
import re
import time

ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
CADENCE = 16
EPSILON, RADIUS = Q(1, 1000000), Q(1, 100000)
TOLERANCE, MARGIN = Q.from_float(1e-6), Q.from_float(.30)
LIB_PINS = {"check_on_basins.py":"7c9a9b9ae49495b561d0c6a7aaeddfaf7eaf6c892ef34ca261a668f44e0d5bb2","check_on_fixed_points.py":"e23abd2a8fb4e881913a50cc0b810f187b0181ee8f0f712ec5d883fcaecd8663","check_on_convergence_gate.py":"0978b8da49213ca2a22fe4f7fc444cb989f72da0ff9bc52c61004ba7d9e10493","check_on_online_convergence_gate.py":"5258e7f3167e969117f6ed95ed7eb206d3f09ffe6867c4bd289626e5cbc2bf4c"}  # Installed by the source-bound implementation build, never learned from a result.


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def decode(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    def invalid(value):
        raise ValueError('nonfinite JSON')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def binary(value):
    if type(value) not in (int, float):
        raise ValueError('primitive type')
    return Q.from_float(float(value))


def parse_box(encoded):
    if (not isinstance(encoded, list) or len(encoded) != 7
            or any(not isinstance(p, list) or len(p) != 2 for p in encoded)
            or any(not isinstance(v, str) or not re.fullmatch(r'-?\d+\.\d{30}', v)
                   for p in encoded for v in p)):
        raise ValueError('whole7 grid30 box')
    box = [tuple(map(Q, p)) for p in encoded]
    if any(not -1 <= lo <= hi <= 1 for lo, hi in box):
        raise ValueError('state domain/order')
    return box


def grid(value, upper=False):
    value = Q(value)
    n = value.numerator * 10**30
    integer = -((-n)//value.denominator) if upper else n//value.denominator
    whole, part = divmod(abs(integer), 10**30)
    return ('-' if integer < 0 else '') + f'{whole}.{part:030d}'


def encode_box(box):
    return [[grid(lo), grid(hi, True)] for lo, hi in box]


def difference(a, b):
    al, ah = a; bl, bh = b
    return max(Q(0), al-bh, bl-ah), max(abs(al-bh), abs(ah-bl))


def diagnostic(encoded, partial=True):
    box = parse_box(encoded)
    lo, hi = box[6]
    margin = difference((lo, hi), (Q(0), Q(0)))
    candidate = True if lo >= 0 else False if hi < 0 else None
    if margin[0] < MARGIN:
        candidate = None
    return {'candidate': candidate, 'margin_x_interval': list(map(str, margin)),
            'coverage_required': partial and candidate is False,
            'adopted_value': 'NOT_MEASURED'}


class BudgetStop(Exception):
    pass


class Meter:
    def __init__(self, deadline=float('inf'), clock=time.monotonic):
        self.deadline, self.clock = deadline, clock
        self.counts = dict(real_map_steps=0, real_coordinate_updates=0, interval_matrix_terms=0,
                           binding_checks=0, taylor_calls=0, region_proofs=0,
                           residual_calls=0, fraction_observed_max_bits=0)

    def guard(self):
        if self.clock() >= self.deadline:
            raise BudgetStop('policy deadline')

    def taylor(self):
        self.guard()
        self.counts['taylor_calls'] += 1

    def observe(self, values):
        for value in values:
            v = Q(value)
            self.counts['fraction_observed_max_bits'] = max(
                self.counts['fraction_observed_max_bits'],
                abs(v.numerator).bit_length(), v.denominator.bit_length())


def select_defs(source, names, namespace):
    nodes = [n for n in ast.parse(source).body
             if isinstance(n, ast.FunctionDef) and n.name in names]
    if ({n.name for n in nodes} != set(names)
            or any(n.decorator_list for n in nodes)
            or any(isinstance(c, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal))
                   for n in nodes for c in ast.walk(n))):
        raise ValueError('numeric function inventory/syntax')
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 '<pinned-numeric-only>', 'exec'), namespace)
    return namespace


class Arithmetic:
    def __init__(self, sources, meter):
        if set(sources) != set(LIB_PINS):
            raise ValueError('arithmetic source inventory')
        for name, source in sources.items():
            if hashlib.sha256(source.encode('utf-8')).hexdigest() != LIB_PINS[name]:
                raise ValueError('arithmetic source pin')
        safe = {n: getattr(builtins, n) for n in ('abs','all','any','bool','dict','divmod',
                'enumerate','int','isinstance','len','list','map','max','min','range','set',
                'sorted','str','sum','tuple','type','zip','next','ValueError')}
        temporary = {'__builtins__': dict(safe, getattr=getattr, exec=exec, compile=compile),
                     'Q': Q, 'ast': ast, 'builtins': builtins}
        # Only the operational hook moves to actual Taylor calls; numerical expressions stay pinned.
        builder = sources['check_on_online_convergence_gate.py'].replace(
            "count_tanh and node.name == 'tanh_bounds'", "count_tanh and node.name == 'exp_positive'")
        select_defs(builder,
                    ('require', 'build_arithmetic'), temporary)
        self.numeric = temporary['build_arithmetic'](sources['check_on_fixed_points.py'],
                        sources['check_on_convergence_gate.py'], meter.taylor)
        pure = {'__builtins__': safe, 'Q': Q, 're': re,
                'PAYLOAD_FIELDS': {'model','current_x_box','radius_x_exact','epsilon_p_exact'}}
        select_defs(sources['check_on_online_convergence_gate.py'],
            ('require','outward','rational','validatepayload','solve_comparison','gatebound',
             'informationaudit','current_residual','local_certificate'), pure)
        self.local = pure['local_certificate']
        pure['informationaudit'](self.numeric)
        forward = {'__builtins__': safe, 'Q': Q,
                   'tanh_enclosure': self.numeric['tanh_bounds']}
        select_defs(sources['check_on_basins.py'], ('advance',), forward)
        self.advance = forward['advance']
        self.meter = meter

    def step(self, model, encoded):
        self.meter.guard()
        if set(model) != {'b','G','d'}:
            raise ValueError('model fields')
        box = parse_box(encoded)
        b = list(map(Q, model['b'])); G = [list(map(Q, row)) for row in model['G']]
        lo, hi = self.advance(b, G, Q(model['d']), [p[0] for p in box], [p[1] for p in box])
        self.meter.guard()
        result = encode_box(list(zip(lo, hi)))
        checked = parse_box(result)
        if not all(a <= l <= h <= z for (a,z),l,h in zip(checked,lo,hi)):
            raise ValueError('outward transition')
        self.meter.observe(b + [v for row in G for v in row] + lo + hi)
        self.meter.counts['real_map_steps'] += 1
        self.meter.counts['real_coordinate_updates'] += 7
        self.meter.counts['interval_matrix_terms'] += 49
        return result

    def certificate(self, model, encoded):
        self.meter.guard()
        self.meter.counts['region_proofs'] += 1
        self.meter.counts['residual_calls'] += 1
        result = self.local({'model': model, 'current_x_box': encoded,
                            'radius_x_exact': str(RADIUS),
                            'epsilon_p_exact': [str(EPSILON)]}, self.numeric)
        self.meter.guard()
        return result


class Legacy:
    """Every-tick counters; no earlier stable candidate is latched across cadence16."""
    def __init__(self):
        self.stable = 0

    def update(self, tick, previous, current, older=None):
        a, b = parse_box(previous), parse_box(current)
        ds = [difference(x,y) for x,y in zip(b,a)]
        residual = max(v[0] for v in ds)/2, max(v[1] for v in ds)/2
        if residual[1] <= TOLERANCE:
            self.stable += 1
        elif residual[0] > TOLERANCE:
            self.stable = 0
        else:
            raise ValueError('residual threshold overlaps')
        detail = {'stable_steps': self.stable, 'residual_p_interval': list(map(str,residual)),
                  'checked': tick % CADENCE == 0, 'status': None}
        if tick % CADENCE:
            return detail
        if self.stable >= 4:
            margin = difference(b[6], (Q(0),Q(0)))
            if margin[0] >= MARGIN:
                detail['status'] = 'stable_decision'
            elif margin[1] < MARGIN:
                detail['status'] = 'stable_ambiguous'
            else:
                raise ValueError('margin threshold overlaps')
        elif older is not None:
            ds = [difference(x,y) for x,y in zip(b,parse_box(older))]
            two = max(v[0] for v in ds)/2, max(v[1] for v in ds)/2
            if residual[0] > 10*TOLERANCE and two[1] < TOLERANCE:
                detail['status'] = 'oscillating'
            elif residual[1] <= 10*TOLERANCE or two[0] >= TOLERANCE:
                pass
            else:
                raise ValueError('oscillation threshold overlaps')
        return detail
