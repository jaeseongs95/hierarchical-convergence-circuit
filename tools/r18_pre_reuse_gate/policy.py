"""A bounded observational prefilter; never reads world truth or runs inference."""
def preflight(observation, has_memory, motif_length=2):
    cost=dict(metadata_reads=1, edge_records_read=0, chain_links_followed=0)
    def result(enabled,reason):return dict(enabled=enabled,reason=reason,**cost)
    if not has_memory:return result(False,'no_compiled_memory')
    edges=observation['edges']
    if len(edges)<2*motif_length:return result(False,'insufficient_span')
    by_source={}
    for edge in edges:
        cost['edge_records_read']+=1
        if edge['score']!=1:return result(False,'measurement_not_certain_positive')
        if edge['source'] in by_source:return result(False,'branching')
        by_source[edge['source']]=edge['target']
    vertex=observation['start'];seen=set()
    for _ in edges:
        cost['chain_links_followed']+=1
        if vertex in seen or vertex not in by_source:return result(False,'not_single_chain')
        seen.add(vertex);vertex=by_source[vertex]
    return result(vertex==observation['goal'],'single_chain_two_macros' if vertex==observation['goal'] else 'wrong_endpoint')


def independent_allow(observation, has_memory):
    # Audit-only expression, separate from the policy's early-return implementation.
    es=observation['edges']
    if not has_memory or len(es)<4 or not all(e['score']==1 for e in es):return False
    if len({e['source'] for e in es})!=len(es):return False
    paths=[(observation['start'],set(),set())]
    for _ in es:
        v,seen,used=paths.pop()
        choices=[(i,e) for i,e in enumerate(es) if e['source']==v and i not in used and e['target'] not in seen|{v}]
        if len(choices)!=1:return False
        i,e=choices[0];paths.append((e['target'],seen|{v},used|{i}))
    return paths[0][0]==observation['goal']
