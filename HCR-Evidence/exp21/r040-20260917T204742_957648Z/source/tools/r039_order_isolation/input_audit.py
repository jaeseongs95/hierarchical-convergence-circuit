"""생산 spec.make_cases를 호출하지 않는 입력 개입 검산. 교정/재명명은 하지 않는다."""
from copy import deepcopy
from .contracts import demand, digest
# 별도 수작업 명세: EXP19 원자료에서 확인된 l3 early의 고정된 관계/관측.
EDGES = (('e0','s','a0',.92),('e1','a0','g',.92),('e2','s','b0',None),
         ('e3','b0','g',.92),('e4','s','c0',-.92),('e5','c0','c1',.92),('e6','c1','g',.92))
BLOCKS = {'S':['e0','e1'], 'M':['e2','e3'], 'D':['e4','e5','e6']}
EXPECTED_ORDERS = ('SMD','SDM','MSD','MDS','DSM','DMS')
PUBLIC_KEYS = {'name','family','cohort','observation','manipulation'}


def canonical_observation():
    return dict(episode_id='exp19-input-10',revision=0,start='s',goal='g',
        edges=[dict(id=eid,source=a,target=b,score=score) for eid,a,b,score in EDGES])


def canonical_worlds():
    out={}
    for name,value in (('missing_closed',False),('missing_open',True)):
        out[name]={eid:(value if eid=='e2' else False if eid=='e4' else True) for eid,*_ in EDGES}
    return out


def check_canonical(parent_case):
    demand(parent_case['name']=='three_branch_l3_early','원 입력 case identity 변경')
    demand(digest(parent_case['observation'])==digest(canonical_observation()),'원 입력의 ID/관계/score 변경')
    demand(digest(parent_case['worlds'])==digest(canonical_worlds()),'원 평가 world 변경')


def check_cases(public, worlds, parent_case):
    check_canonical(parent_case)
    demand(isinstance(public,list) and len(public)==6,'6개 순열 전부 보존해야 합니다.')
    demand(set(worlds)=={'order_'+x for x in EXPECTED_ORDERS},'world population 불일치')
    original=parent_case['observation'];lookup={e['id']:e for e in original['edges']}
    reports=[]
    for case,order in zip(public,EXPECTED_ORDERS):
        demand(set(case)==PUBLIC_KEYS,'입력 case 필드/비공개 혼입')
        demand(case['name']=='order_'+order and case['family']=='fixed_identity_branch_order'
               and case['cohort']=='order_only','입력 population/order 라벨 변경')
        obs=case['observation'];ids=[eid for ch in order for eid in BLOCKS[ch]]
        expected=deepcopy(original);expected['edges']=[deepcopy(lookup[e]) for e in ids]
        demand(digest(obs)==digest(expected),'배열 외 변화 또는 내부 edge 순서 변경')
        m=case['manipulation']
        demand(m==dict(branch_order=order,edge_id_order=ids,
            new_to_canonical_slot=[next(i for i,e in enumerate(original['edges']) if e['id']==eid) for eid in ids],
            canonical_observation_sha256=digest(original)),'순열/slot 대응표 변조')
        demand(digest(worlds[case['name']])==digest(parent_case['worlds']),'ID별 world 대응을 재할당했습니다.')
        reports.append(dict(case=case['name'],branch_order=order,edge_id_order=ids,
            observation_sha256=digest(obs),fixed_semantic_sha256=digest({**obs,'edges':sorted(obs['edges'],key=lambda e:e['id'])}),
            episode_id=obs['episode_id'],verified=True))
    demand(len({r['observation_sha256'] for r in reports})==6,'배열 순열 중복')
    demand(len({r['fixed_semantic_sha256'] for r in reports})==1,'관계 의미 불변성 실패')
    return reports


def check_trial_schedule(rows):
    expected=[]
    arms=['native','posthoc_support','online_support']
    for i,order in enumerate(EXPECTED_ORDERS):
        for j,scope in enumerate(['legacy','route_only']):
            for n in range(3):
                expected.append(dict(id='t%04d'%len(expected),case='order_'+order,scope=scope,arm=arms[(i+j+n)%3]))
    demand(rows==expected,'미등록/누락/중복 trial 또는 실행 순서 변경')
