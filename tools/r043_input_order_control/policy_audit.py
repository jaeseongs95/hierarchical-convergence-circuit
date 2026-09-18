"""Independent head-slot and accounting check; does not import the production chooser."""
from copy import deepcopy
from .storage import digest, require


def check(base: dict) -> dict:
    requests = [e for e in base['events'] if e['event'] == 'schedule_requested']
    decisions = [e['decision'] for e in base['events'] if e['event'] == 'schedule_decided']
    require(base['scheduler'] == 'input_order', 'negative-control scheduler changed')
    require(len(requests) == len(decisions), 'schedule request/decision inventory')
    totals = dict(decision_calls=0,frontier_items_examined=0,edge_id_reads=0,
                  key_comparisons=0,priority_transitions=0,priority_match_scans=0)
    rows = []
    for ordinal, (request, decision) in enumerate(zip(requests, decisions)):
        view = request['view']
        require(set(view) == {'schema','edge_ids','frontier_paths'} and
                view['schema'] == 'hcr-frontier-view-r041-v1', 'scheduler projection boundary')
        require(request['scheduler'] == 'input_order' and request['input_sha256'] == digest(view), 'schedule binding')
        ids, paths = view['edge_ids'], view['frontier_paths']
        require(type(ids) is list and 1 <= len(ids) <= 8 and
                all(type(e) is str and 0 < len(e) <= 128 for e in ids) and len(set(ids)) == len(ids), 'edge ID inventory')
        require(type(paths) is list and len(paths) <= 32 and all(type(p) is list and len(p) <= 4 and
                all(type(i) is int and 0 <= i < len(ids) for i in p) for p in paths), 'frontier slot inventory')
        require(len({tuple(p) for p in paths}) == len(paths), 'duplicate frontier path')
        selected = None if not paths else deepcopy(paths[0])
        selected_ids = None if selected is None else [ids[i] for i in selected]
        usage = dict(decision_calls=1,frontier_items_examined=int(bool(paths)),
            edge_id_reads=0 if selected is None else len(selected),key_comparisons=0,
            priority_transitions=0,priority_match_scans=0)
        expected = dict(schema='hcr-frontier-choice-r041-v1',scheduler='input_order',input_sha256=digest(view),
            selected_index=None if not paths else 0,selected_path=selected,selected_edge_ids=selected_ids,
            priority_required=False,usage=usage)
        require(digest(decision) == digest(expected), 'input_order decision/usage differs from head-slot rule')
        for key,value in usage.items(): totals[key] += value
        rows.append(dict(ordinal=ordinal,frontier_slots=deepcopy(paths),selected_slot_index=None if not paths else 0,
                         selected_slot_path=selected,selected_native_IDs=selected_ids,usage=usage))
    require(digest(base['scheduler_usage']) == digest(totals), 'input_order aggregate accounting mismatch')
    require(not any(e['event'] in ('priority_requested','priority_committed') for e in base['events']),
            'input_order must not issue priority changes')
    return dict(verified=True,decisions=len(decisions),usage=totals,slot_decisions=rows,
                decision_uses_ID_ranking=False,logging_ID_reads_retained=True,
                scheduler_view_still_contains_IDs=True, whole_runtime_ID_independence_claimed=False)
