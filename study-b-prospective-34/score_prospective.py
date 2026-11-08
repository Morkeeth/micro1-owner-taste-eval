"""Deterministic scorer. Works with zero responses (constant only)."""
import json,random,math
from pathlib import Path
ROOT=Path(__file__).parent
P=json.load(open(ROOT/'PROTOCOL.json')); man=json.load(open(ROOT/'MANIFEST.json'))
lab={l['case_id']:l['verdict'] for l in json.load(open(ROOT/'labels/owner-verdicts.json'))}
CONST=P['baseline']['choice']; rev=set(P['strata']['revision']); cl=P['clusters']
def pred(cid,arm,pin):
    f=ROOT/'responses'/f'{cid}-{arm}-{pin}.json'
    if not f.exists(): return None
    try: return json.loads(json.load(open(f))['response']['choices'][0]['message']['content'])['choice']
    except Exception: return 'INVALID'
def wilson(k,n,z=1.96):
    if n==0: return None
    p=k/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)); return [(c-h)/d,(c+h)/d]
def boot(diff):  # diff: case->(a,b) correctness; cluster resample
    groups={}
    for c,v in diff.items(): groups.setdefault(cl[c],[]).append(v)
    g=list(groups.values()); rng=random.Random(20261108); out=[]
    for _ in range(10000):
        s=[x for _ in g for x in rng.choice(g)]; out.append(sum(a-b for a,b in s)/len(s))
    out.sort(); return [out[249],out[9749]]
ids=[m['case_id'] for m in man]; res={'n':len(ids),'constant':CONST}
for name,subset in [('all',ids),('fresh',[i for i in ids if i not in rev]),('revision',[i for i in ids if i in rev])]:
    r={'n':len(subset),'constant_correct':sum(lab[i]==CONST for i in subset),'label_counts':{o:sum(lab[i]==o for i in subset) for o in P['options']}}
    for arm in ['RAW','HISTORY']:
        for pin in ['anthropic','openai']:
            ps={i:pred(i,arm,pin) for i in subset}
            if any(v is None for v in ps.values()): r[f'{arm}-{pin}']='NOT RUN'; continue
            k=sum(ps[i]==lab[i] for i in subset)
            r[f'{arm}-{pin}']={'correct':k,'wilson95':wilson(k,len(subset)),'invalid':sum(v=='INVALID' for v in ps.values()),
              'minus_constant_cluster95':boot({i:(ps[i]==lab[i],lab[i]==CONST) for i in subset})}
        if name=='all' and all(isinstance(r.get(f'{a}-{p}'),dict) for a in ['RAW','HISTORY'] for p in ['anthropic','openai']):
            for pin in ['anthropic','openai']:
                r[f'HISTORY-minus-RAW-{pin}_cluster95']=boot({i:(pred(i,'HISTORY',pin)==lab[i],pred(i,'RAW',pin)==lab[i]) for i in subset})
    res[name]=r
(ROOT/'SCORES.json').write_text(json.dumps(res,indent=1)+'\n'); print(json.dumps(res,indent=1))
