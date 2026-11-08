"""Supplementary metrics from the plan's scoring rule, written after freeze and before model output. Deterministic, offline."""
import json,math
from pathlib import Path
R=Path(__file__).resolve().parent
P=json.load(open(R/'PROTOCOL.json')); man=json.load(open(R/'MANIFEST.json'))
lab={l['case_id']:l['verdict'] for l in json.load(open(R/'labels/owner-verdicts.json'))}
O=P['options']; C=P['baseline']['choice']; rev=set(P['strata']['revision'])
def pred(c,a,p):
    f=R/'responses'/f'{c}-{a}-{p}.json'
    try: return json.loads(json.load(open(f))['response']['choices'][0]['message']['content'])['choice']
    except Exception: return None
def mcnemar(b,d):
    n=b+d; return 1.0 if n==0 else min(1,2*sum(math.comb(n,i) for i in range(min(b,d)+1))/2**n)
out={}
for name,ids in [('all',[m['case_id'] for m in man]),('fresh',[m['case_id'] for m in man if m['case_id'] not in rev])]:
    r={}
    for a in ['RAW','HISTORY']:
        for p in ['anthropic','openai']:
            ps={i:pred(i,a,p) for i in ids}
            rec={o:[sum(ps[i]==o and lab[i]==o for i in ids),sum(lab[i]==o for i in ids)] for o in O}
            present=[o for o in O if rec[o][1]]
            b=sum(ps[i]==lab[i] and lab[i]!=C for i in ids); d=sum(ps[i]!=lab[i] and lab[i]==C for i in ids)
            r[f'{a}-{p}']={'correct':sum(ps[i]==lab[i] for i in ids),'n':len(ids),'balanced_accuracy':sum(rec[o][0]/rec[o][1] for o in present)/len(present),'class_recall':rec,'pred_counts':{o:sum(ps[i]==o for i in ids) for o in O},'invalid':sum(ps[i] not in O for i in ids),'vs_constant_model_only':b,'vs_constant_constant_only':d,'vs_constant_exact_mcnemar_p':mcnemar(b,d)}
    for p in ['anthropic','openai']:
        b=sum(pred(i,'HISTORY',p)==lab[i]!=pred(i,'RAW',p) for i in ids); d=sum(pred(i,'RAW',p)==lab[i]!=pred(i,'HISTORY',p) for i in ids)
        r[f'HISTORY-vs-RAW-{p}']={'history_only_correct':b,'raw_only_correct':d,'exact_mcnemar_p':mcnemar(b,d)}
    r['constant_balanced_accuracy']=1/len([o for o in O if any(lab[i]==o for i in ids)])
    out[name]=r
(R/'SUPPLEMENT.json').write_text(json.dumps(out,indent=1)+'\n'); print(json.dumps(out,indent=1))
