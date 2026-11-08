"""Post-hoc, exploratory: how far does simply following the proposing agent's own recommendation go? Keyword rule, written after model output."""
import json,re
from pathlib import Path
R=Path(__file__).resolve().parent
lab={l['case_id']:l['verdict'] for l in json.load(open(R/'labels/owner-verdicts.json'))}
P=json.load(open(R/'PROTOCOL.json')); rev=set(P['strata']['revision'])
def rule(t):
    t=t.lower()
    if re.search(r'\bkill\b',t): return 'KILL THIS ONE'
    if re.search(r'needs new content',t): return 'NEEDS NEW CONTENT'
    if re.search(r'\bedit\b|recolou?r',t): return 'EDIT THIS ONE'
    if re.search(r'\buse it\b|\bgood\b|\bstrong\b|\bbest\b|\bfits?\b|\bclean\b|replaces|drop-in',t): return 'AWESOME, USE IT'
    return None
rows=[]
for f in sorted((R/'inputs').glob('*.json')):
    c=json.load(open(f)); r=c['shown_card_text'].get('recommendation') or ''; p=rule(r) or 'AWESOME, USE IT'
    rows.append({'case_id':c['case_id'],'recommendation':r,'cue':rule(r),'pred':p,'truth':lab[c['case_id']],'correct':p==lab[c['case_id']]})
def acc(ids): return sum(x['correct'] for x in rows if x['case_id'] in ids)
allids={x['case_id'] for x in rows}; fresh=allids-rev
def agree(arm,pin):
    n=0
    for x in rows:
        d=json.loads(json.load(open(R/'responses'/f"{x['case_id']}-{arm}-{pin}.json"))['response']['choices'][0]['message']['content'])['choice']; n+=d==x['pred']
    return n
out={'rule':'kill>KILL; needs new content>NEEDS NEW CONTENT; edit/recolour>EDIT; use it/good/strong/best/fit/clean/replaces/drop-in>AWESOME; no cue>AWESOME',
 'status':'EXPLORATORY, POST-HOC (written after model output)','all':[acc(allids),len(allids)],'fresh':[acc(fresh),len(fresh)],
 'non_awesome_cues':sum(1 for x in rows if x['cue'] and x['cue']!='AWESOME, USE IT'),
 'model_agreement_with_cue':{f'{a}-{p}':agree(a,p) for a in ['RAW','HISTORY'] for p in ['anthropic','openai']},'rows':rows}
(R/'RECOMMENDATION-CUE.json').write_text(json.dumps(out,indent=1)+'\n')
print({k:v for k,v in out.items() if k!='rows'})
for x in rows:
    if x['cue'] and x['cue']!='AWESOME, USE IT': print(x['case_id'],x['cue'],'truth',x['truth'])
