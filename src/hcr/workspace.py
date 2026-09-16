"""공개 topology에서 후보 경로를 형성하고 같은 신호 커널의 회로로 전개한다.
관측 score나 숨은 passability로 경로를 선택하는 전역 정답 solver가 아니다.
"""
from .model import Config, Cost, Group, Link, Program, ContractError, ExpansionLimit
from .binding import Topology


def discover_paths(topology: Topology, config: Config, cost: Cost):
    topology.validate(config)
    results=[];checks=0
    def walk(node, visited, path):
        nonlocal checks
        if node==topology.goal:
            results.append(tuple(path))
            if len(results)>config.max_paths: raise ExpansionLimit('path budget exhausted; incomplete set not used')
            return
        for i,(a,b) in enumerate(topology.edges):
            cost.search_edge_checks+=1;checks+=1
            if checks>config.max_search: raise ExpansionLimit('search budget exhausted')
            if a!=node or b in visited: continue
            if len(path)>=config.max_path_length: raise ExpansionLimit('path length limit; not silently discarded')
            walk(b,visited|{b},path+[i])
    walk(topology.start,{topology.start},[])
    return tuple(results)


def make_program(edge_count: int, paths: tuple[tuple[int,...],...], config: Config,
                 cost: Cost | None=None) -> Program:
    groups=[Group('e:'+str(i),0) for i in range(edge_count)]
    links=[];finals=[];gain=config.relation_gain
    for pi,path in enumerate(paths):
        previous=None
        for position,edge in enumerate(path):
            key=f'p:{pi}:{position}'
            parents=['e:'+str(edge)]+([previous] if previous is not None else [])
            groups.append(Group(key,1,-gain*(len(parents)-1)))
            for parent in parents:
                links.append(Link(parent,key,gain,'support'))
                links.append(Link(key,parent,config.top_down_gain,'top_down'))
            previous=key
        if previous is not None: finals.append(previous)
    # OR of route hypotheses. Same kernel as edge and prefix groups.
    groups.append(Group('goal',1,gain*(len(finals)-1)))
    for last in finals:
        links.append(Link(last,'goal',gain,'support'))
        links.append(Link('goal',last,config.top_down_gain,'top_down'))
    program=Program(tuple(groups),tuple(links),paths,edge_count);program.validate(config)
    if cost is not None:
        cost.dynamic_groups_created+=len(groups)
        cost.dynamic_links_created+=len(links)
    return program


def expand(topology: Topology, config: Config, cost: Cost, emit=None) -> Program | None:
    paths=discover_paths(topology,config,cost)
    if not paths: return None
    program=make_program(len(topology.edges),paths,config,cost)
    if emit:
        emit('graph_expanded',{'paths':[list(x) for x in paths],'groups':len(program.groups),
                             'links':len(program.links),'program_digest':program.digest})
    return program
