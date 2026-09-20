"""Two explicit, pre-execution edits in an isolated source copy only."""
from tools.r050_review_boundary.common import require

PATCHES = {
    'src/hcr/workspace.py': (
        "                links.append(Link(key,parent,config.top_down_gain,'top_down'))",
        "                # EXP-43: predeclared structural intervention, before execution.\n"
        "                if (key, parent) != ('p:0:1', 'p:0:0'):\n"
        "                    links.append(Link(key,parent,config.top_down_gain,'top_down'))"),
    'src/hcr/evaluation/adaptive_audit_support.py': (
        "                links.append(dict(source=key, target=source, weight=k.top_down_gain, kind='top_down'))",
        "                # EXP-43: independent expected-grammar exclusion.\n"
        "                if not (number == 0 and depth == 1 and source == 'p:0:0'):\n"
        "                    links.append(dict(source=key, target=source, weight=k.top_down_gain, kind='top_down'))"),
}


def patched(path, raw):
    before, after = PATCHES[path]
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    before = before.encode().replace(b'\n', newline)
    after = after.encode().replace(b'\n', newline)
    require(raw.count(before) == 1, 'Exact unique source preimage required: '+path)
    return raw.replace(before, after)
