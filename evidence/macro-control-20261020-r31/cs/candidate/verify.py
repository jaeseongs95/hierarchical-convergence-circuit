"""Separate saved-event audit; no runtime/activation/expansion/learning invocation."""
from copy import deepcopy
import math
from hcr import codec
from hcr.model import AdaptiveCost,Cost,fingerprint
from hcr.trace import check_chain
from hcr.prior_policy import policy_fields
from hcr.evaluation.reference import assess
from hcr.evaluation.adaptive_audit_support import (scan_patterns,pool_network,decision_network,plan_expansion,expected_learning,circuit_id)
from tools.r26_contraction_warmstart.verify import scalar

def require(v,message):
    if not v:raise ValueError(message)

def timing(x):
    require(set(x)=={'cpu_seconds','wall_seconds'} and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in x.values()),'timing')

def audit(r,public,memory,p,arm,truth,training=False):
    require(r['schema']=='hcr-r31-research-record-v1' and r['arm']==arm and r['training'] is training and r['public']==public,'research input binding')
    require(r['memory_before']==r['memory_after_inference']==memory,'same experience and immutable inference')
    cfg=codec.adaptive_config_from(p['config']);obs=codec.observation_from(public);events=r['records']
    check_chain(events,r['event_count'],r['event_head']);timing(r['session_timing'])
    cost=AdaptiveCost();frontier=[];routes=[];known={()};next_node=1;proposals=None;scan=None;activations=[]
    networks={};last=None;maximum=0.;score_checks=0;settles=0;seen_decision=0;started=False;created=False
    decision=None;assessment=None;feedback=None;learned=False;mismatch=dict(kind='new_input',magnitude=0.0,detail='')
    for event in events:
        name,x=event['event'],event['payload']
        if name=='r02_engine_created':
            require(not created and x['config']==p['config'] and x['config_signature']==cfg.signature and x['memory_document']==memory and x['memory_hash']==fingerprint(memory),'engine binding')
            require(x['use_circuits'] is (arm!='primitive') and x['top_down'] is True and x['allow_reexpansion'] is True and x['prior_policy']==policy_fields('route_only')['prior_policy'],'engine switches');created=True
        elif name=='r02_workspace_created':
            require(created and not frontier and started,'workspace sequence')
            initial=dict(node=dict(node_id='node:'+obs.digest[:20]+':0',semantic_id=obs.start,revision=obs.revision),path=[],visited=[obs.start],uses=[])
            require(x['initial']==initial,'initial workspace');frontier=[initial];cost.graph_nodes_created+=1
        elif name=='r02_attempt_started':
            require(not started and x['observation']==public and x['memory_hash']==fingerprint(memory) and x['mode']==('train' if training else 'frozen_eval') and x['revision_of'] is None,'attempt binding');started=True
        elif name=='r02_binding_scan':
            require(started and arm!='primitive' and x['prefix']==frontier[0],'scan boundary')
            scan=scan_patterns(obs,frontier[0],memory,cfg,max(0,cfg.max_binding_checks-cost.binding_operations))
            require(all(x[k]==v for k,v in scan.items()),'separate matching')
            cost.recall_checks+=len(scan['inspected']);cost.binding_checks+=len(scan['scans']);cost.binding_operations+=len(scan['scans']);cost.candidate_circuits+=len(scan['matched'])
        elif name=='r02_pool_unavailable':
            require(scan and scan['complete'] and scan['matched'],'pool budget without candidates')
            program,_,_,_=pool_network(obs,scan['matched'],memory,cfg)
            require(len(program['groups'])>cfg.kernel.max_groups and x['reason']=='common_kernel_group_budget','pool group fallback')
        elif name=='r02_network':
            require(x['network_id'] not in networks and x['top_down'] is True,'network sequence')
            if x['kind']=='pool':
                require(arm=='hcr' and scan and scan['complete'] and scan['matched'],'native pool boundary')
                program,drives,meta,instantiated=pool_network(obs,scan['matched'],memory,cfg)
                require(x['metadata']==dict(prefix=frontier[0],candidates=meta),'pool metadata')
                cost.dynamic_groups_created+=len(obs.edges)+1;n=len(meta);cost.dynamic_links_created+=2*n+n*(n-1);cost.circuit_groups_instantiated+=instantiated;cost.pool_calls+=1
            else:
                require(x['kind']=='decision' and routes,'decision boundary')
                program,drives=decision_network(obs,routes,cfg,judgment_prior='route_only')
                require(x['metadata']==dict(routes=routes,graph_complete=not frontier,**policy_fields('route_only')),'primitive final network')
                cost.dynamic_groups_created+=len(program['groups']);cost.dynamic_links_created+=len(program['links']);last=x['network_id']
            require(x['program']==program and x['program_digest']==fingerprint(program) and x['drives']==drives,'separate signal grammar and drives')
            require(len(program['groups'])<=cfg.kernel.max_groups and len(program['paths'])<=cfg.kernel.max_paths,'network caps')
            networks[x['network_id']]=dict(payload=x,ticks=[],done=False)
        elif name=='r02_tick':
            n=networks[x['network_id']];require(not n['done'],'tick after settle');n['ticks'].append({k:x[k] for k in ['tick','state','residual','stable_steps']})
        elif name=='r02_settled':
            n=networks[x['network_id']];require(not n['done'],'duplicate settle');pr=n['payload']['program'];count=len(n['ticks'])
            c=Cost(kernel_ticks=count,group_updates=count*len(pr['groups']),normalization_ops=count*len(pr['groups']),signal_transmissions=count*len(pr['links']))
            rec=dict(program=pr,initial={g['id']:.5 for g in pr['groups']},drives=n['payload']['drives'],ticks=n['ticks'],state=x['state'],convergence=x['convergence'],cost=c.snapshot(),adopted=x['state']['goal']>=.5 if x['convergence']['status']=='stable_decision' else None)
            maximum=max(maximum,scalar(rec,p['config']['kernel'],p['scalar_tolerance']));n.update(done=True,state=x['state'],convergence=x['convergence']);settles+=1
            for k in ['kernel_ticks','group_updates','normalization_ops','signal_transmissions']:setattr(cost,k,getattr(cost,k)+getattr(c,k))
        elif name=='r02_pool_result':
            require(arm=='hcr','pool result in conventional arm');n=networks[x['network_id']];require(n['done'],'pool not settled')
            stable=n['convergence']['status'] in ('stable_decision','stable_ambiguous');activations=[]
            for i,meta in enumerate(n['payload']['metadata']['candidates']):
                value=n['state']['c:'+str(i)]
                activations.append(dict(meta,activation=value,eligible=stable and value>=cfg.activation_threshold and meta['mismatch']<=cfg.mismatch_threshold))
            require(x['activations']==activations,'native pool readout')
        elif name=='r31_macro_result':
            require(arm=='macro' and scan and scan['complete'] and scan['matched'],'conventional boundary')
            lookup={circuit_id(c):c for c in memory['circuits']};activations=[];checks=0
            for match in scan['matched']:
                slots=match['binding']['edge_order'];checks+=len(slots)
                activations.append(dict(match,activation=1.0,mismatch=0.0,prior=0.0,circuit_version=lookup[match['circuit_id']]['version'],eligible=all(obs.edges[i].score is not None and obs.edges[i].score>0 for i in slots)))
            group_count=len(obs.edges)+1+sum(len(lookup[m['circuit_id']]['pattern']['program']['groups'])-len(m['binding']['edge_order']) for m in scan['matched'])
            require(x['activations']==activations and x['score_checks']==checks and x['group_allowance_checked']==group_count<=cfg.kernel.max_groups,'conventional applicability')
            score_checks+=checks
        elif name=='r02_proposals':
            require(frontier and x['prefix']==frontier[0] and x['circuits_enabled'] is (arm!='primitive') and x['mismatch']==mismatch,'proposal boundary')
            prefix=frontier[0];slots=[i for i,e in enumerate(obs.edges) if e.source==prefix['visited'][-1] and e.target not in prefix['visited']]
            cs=[dict(edges=a['binding']['edge_order'],source='circuit',activation=a['activation'],mismatch=a['mismatch'],circuit_id=a['circuit_id'],binding=a['binding'],prior=a['prior'],circuit_version=a['circuit_version']) for a in activations if a['eligible']]
            cs.sort(key=lambda c:(-c['activation'],-len(c['edges']),tuple(c['edges']),c['circuit_id']))
            proposals=cs+[dict(edges=[i],source='primitive',activation=0.0,mismatch=0.0,circuit_id=None,binding=None,prior=0.0,circuit_version=0) for i in slots]
            reason='circuit_candidate' if cs else 'circuit_mismatch' if activations else 'no_applicable_circuit'
            require(x['primitive_slots']==slots and x['candidates']==proposals and x['reason']==reason,'candidate ordering and fallback');cost.topology_edge_checks+=len(obs.edges);cost.primitive_candidates+=len(slots)
        elif name=='r02_expansion':
            require(proposals and x['prefix']==frontier[0] and x['candidate']==proposals[0],'unproposed graph edit')
            plan,checks,error=plan_expansion(obs,frontier,routes,known,proposals[0],next_node,cfg);require(error is None,'unexpected graph failure')
            additions,known=plan;require(x['added']==additions,'side branch and role preservation');next_node+=len(additions)
            frontier=[a for a in additions if a['visited'][-1]!=obs.goal]+frontier[1:];routes+=[a for a in additions if a['visited'][-1]==obs.goal]
            require(x['complete'] is (not frontier),'dependency completeness');cost.topology_edge_checks+=checks;cost.expansions+=1;cost.graph_nodes_created+=len(additions);cost.graph_edges_created+=len(additions);cost.circuit_reuses+=int(proposals[0]['source']=='circuit');proposals=None;activations=[];scan=None
        elif name=='r02_dead_end':
            require(proposals==[] and x['prefix']==frontier[0],'false dead end');frontier.pop(0);cost.expansions+=1;cost.frontier_retirements+=1;proposals=None;activations=[];scan=None
        elif name=='r02_progress':
            require(x['graph_complete'] is (not frontier) and x['completed_paths']==[r['path'] for r in routes] and x['network_id']==last,'progress binding')
            n=networks.get(last);negative=n is not None and n['convergence']['status']=='stable_decision' and n['state']['goal']<.5
            mismatch=dict(kind='negative_requires_dependency_coverage' if negative else 'unresolved_or_no_goal_candidate',magnitude=1.0,detail='')
            require(x['mismatch']==mismatch,'progress mismatch')
        elif name=='r02_decision':
            require(seen_decision==0 and last is not None,'decision sequence');seen_decision+=1;decision=codec.adaptive_decision_from(x);n=networks[last]
            value=n['state']['goal']>=.5 if n['convergence']['status']=='stable_decision' else None
            if value is False and frontier:value=None
            require(x==r['decision'] and x['observation_digest']==obs.digest and x['memory_version']==memory['version'] and x['adaptive_config_signature']==cfg.signature and x['mode']==('train' if training else 'frozen_eval'),'decision binding')
            require(x['value'] is value and x['convergence']==n['convergence'] and dict(decision.state)==n['state'] and x['failure_reason'] is None and x['program_digest']==n['payload']['program_digest'],'unmodified final readout')
            uses=sorted({u['circuit_id'] for a in routes for u in a['uses']})
            require(x['expanded_paths']==[a['path'] for a in routes] and x['graph_complete'] is (not frontier) and x['circuit_ids']==uses,'route provenance')
            if value is not None:
                require(x['proof']['paths']==[[obs.edges[i].id for i in path] for path in x['expanded_paths']],'proof route binding')
                for eid,v in decision.proof.assumed_edges:
                    i=next(i for i,e in enumerate(obs.edges) if e.id==eid);require(v is (n['state']['e:'+str(i)]>=.5),'proof signal assumptions')
            cost.proof_nodes_reconstructed=len(decision.proof.nodes);require(math.isfinite(x['cost']['wall_seconds']) and x['cost']['wall_seconds']>=0,'decision time');cost.wall_seconds=x['cost']['wall_seconds']
            require(x['cost']==cost.snapshot(),'independent operation accounting')
        elif name=='r31_external_assessment':
            require(training and decision is not None and x['truth']==truth,'reference boundary');assessment=codec.plain(assess(decision,obs,truth));require(x['assessment']==assessment==r['assessment'],'external assessment')
        elif name=='r02_feedback':
            require(training and assessment is not None and feedback is None and x==r['feedback'],'feedback boundary');feedback=x
            require(x['correct'] is assessment['correct'] and x['proof_valid'] is (assessment['proof_valid'] and assessment['assumption_correct'] is True) and x['observation_digest']==obs.digest and x['decision_id']==decision.id,'feedback contents')
        elif name=='r02_memory_updated':
            require(feedback is not None and not learned,'learning sequence');new,patch,lc=expected_learning(memory,obs,r['decision'],feedback,cfg)
            lc.wall_seconds=x['cost']['wall_seconds'];require(x['memory_document']==new==r['memory_after_learning'] and x['patch']==patch==r['patch'] and x['memory_after']==fingerprint(new) and x['cost']==lc.snapshot(),'separate learning transition');learned=True
        else:raise ValueError('unexpected event '+name)
    require(created and started and seen_decision==1 and all(n['done'] for n in networks.values()) and learned is training,'complete record')
    if training:timing(r['reference_timing']);timing(r['learning_timing'])
    require(r['advances']==cost.expansions<=p['max_advances_per_session'] and cost.kernel_ticks<=p['max_kernel_ticks_per_session'],'session caps')
    require(arm=='hcr' or cost.pool_calls==0,'conventional pool forbidden')
    a=codec.plain(assess(decision,obs,truth));require(decision.value is None or a['proof_valid'],'invalid adopted proof')
    return dict(arm=arm,value=decision.value,assessment=a,strict_correct=a['correct'] is True and a['proof_valid'] and a['assumption_correct'] is True,cost=decision.cost,
        settles=settles,score_checks=score_checks,numeric_replay_max_absolute_error=maximum,expansions=[x['payload']['candidate']['edges'] for x in events if x['event']=='r02_expansion'],learning_cost=None if not training else next(x['payload']['cost'] for x in events if x['event']=='r02_memory_updated'))

def mutations(r,public,memory,p,arm,truth):
    # Reseal after each mutation so semantic checks, not hash chain, reject it.
    from hcr.trace import Trace
    def reseal(b):
        t=Trace()
        for e in b['records']:t.emit(e['event'],e['payload'])
        b.update(records=t.records,event_count=t.count,event_head=t.head)
    rejected={}
    for name in ['input_revision','memory_version','tick','cost','selection','side_branch','macro_eligible']:
        b=deepcopy(r)
        if name=='input_revision':b['public']['revision']+=1
        elif name=='memory_version':b['memory_before']['version']+=1
        elif name=='cost':b['decision']['cost']['kernel_ticks']+=1
        else:
            target={'tick':'r02_tick','selection':'r02_proposals','side_branch':'r02_expansion','macro_eligible':'r31_macro_result'}[name]
            x=next(e['payload'] for e in b['records'] if e['event']==target)
            if name=='tick':x['state']['goal']+=.01
            elif name=='selection':x['candidates'].reverse()
            elif name=='side_branch':x['added'][0]['visited'][0]='wrong'
            else:x['activations'][0]['eligible']=not x['activations'][0]['eligible']
        reseal(b)
        try:audit(b,public,memory,p,arm,truth)
        except ValueError as exc:rejected[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    return rejected
