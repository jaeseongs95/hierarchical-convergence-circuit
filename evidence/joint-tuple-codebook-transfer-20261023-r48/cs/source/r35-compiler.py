"""Syntax/count-only bounded graph construction; no role values or truth inputs."""
from itertools import combinations
from tools.r32_semantic_join.runtime import require

class Builder:
    def __init__(self,features,cfg):
        self.cfg=cfg;self.groups=[dict(id=k,level=0,bias=0.) for k in features];self.links=[]
    def node(self,name,op,terms):
        require(op in ['and','or'] and name not in {x['id'] for x in self.groups},'node grammar')
        gain=self.cfg.relation_gain
        bias=(-gain if op=='and' else gain)*(len(terms)-1) if terms else (gain if op=='and' else -gain)
        self.groups.append(dict(id=name,level=1,bias=bias))
        for source,sign in terms:
            self.links.extend([dict(source=source,target=name,weight=sign*gain,kind='support'),dict(source=name,target=source,weight=sign*self.cfg.top_down_gain,kind='top_down')])
        return name
    def document(self):
        require(len(self.groups)<=32,'native group cap')
        return dict(groups=self.groups,links=self.links,paths=[[0,1]],edge_count=2)

def equality(cfg):
    b=Builder([p+str(i) for p in ['x','y'] for i in range(3)],cfg)
    for i in range(3):
        b.node('pos'+str(i),'and',[('x'+str(i),1),('y'+str(i),1)])
        b.node('neg'+str(i),'and',[('x'+str(i),-1),('y'+str(i),-1)])
        b.node('eq'+str(i),'or',[('pos'+str(i),1),('neg'+str(i),1)])
    b.node('goal','and',[('eq'+str(i),1) for i in range(3)]);return b.document()

def expression(tree,cfg):
    b=Builder(['m0','m1','m2'],cfg)
    def walk(t,depth=0,root=False):
        require(depth<=4,'AST depth')
        if type(t) is int:
            require(0<=t<3,'AST leaf');return b.node('goal','and',[('m'+str(t),1)]) if root else 'm'+str(t)
        require(type(t) is list and len(t) in [2,3] and t[0] in ['not','and','or'],'AST node')
        op=t[0];require(len(t)==(2 if op=='not' else 3),'AST arity')
        terms=[(walk(child,depth+1),-1 if op=='not' else 1) for child in t[1:]]
        return b.node('goal' if root else 'op'+str(len(b.groups)),'and' if op=='not' else op,terms)
    walk(tree,root=True);return b.document()

def feasible(n,cfg):
    require(type(n) is int and 1<=n<=4,'candidate capacity')
    b=Builder(['e'+str(i) for i in range(n)]+['complete'],cfg)
    b.node('goal','or',[('e'+str(i),1) for i in range(n)])
    pairs=[b.node('pair'+str(i)+'_'+str(j),'and',[('e'+str(i),1),('e'+str(j),1)]) for i,j in combinations(range(n),2)]
    b.node('at_least_two','or',[(k,1) for k in pairs]);b.node('one','and',[('goal',1),('at_least_two',-1)])
    b.node('none','and',[('complete',1),('goal',-1)]);b.node('unique','and',[('complete',1),('one',1)])
    b.node('many','and',[('complete',1),('at_least_two',1)]);b.node('incomplete','and',[('complete',-1)])
    return b.document()

def query(n,cfg):
    require(type(n) is int and 1<=n<=4,'candidate capacity')
    b=Builder([p+str(i) for p in ['e','t'] for i in range(n)]+['complete'],cfg)
    b.node('goal','or',[('e'+str(i),1) for i in range(n)])
    for i in range(n):
        b.node('g'+str(i),'and',[('e'+str(i),1),('t'+str(i),1)])
        b.node('b'+str(i),'and',[('e'+str(i),1),('t'+str(i),-1)])
    b.node('good','or',[('g'+str(i),1) for i in range(n)]);b.node('bad','or',[('b'+str(i),1) for i in range(n)])
    b.node('qtrue','and',[('complete',1),('goal',1),('bad',-1)])
    b.node('qfalse','and',[('complete',1),('goal',1),('good',-1)])
    b.node('empty','and',[('complete',1),('goal',-1)]);b.node('mixed','and',[('complete',1),('good',1),('bad',1)])
    b.node('incomplete','and',[('complete',-1)]);return b.document()

def documents(expressions,cfg):
    return dict(role=equality(cfg),**{'expr'+str(i):expression(e,cfg) for i,e in enumerate(expressions)},**{'feasible'+str(n):feasible(n,cfg) for n in range(1,5)},**{'query'+str(n):query(n,cfg) for n in range(1,5)})
