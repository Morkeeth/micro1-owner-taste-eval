"""Post-run deterministic scoring. Never calls a provider or changes inputs."""
import json, pathlib, math, random, collections, hashlib
from decimal import Decimal
P=pathlib.Path(__file__).resolve().parent
def read(f): return json.loads((P/f).read_text())
def wilson(k,n):
 z=1.959963984540054; q=k/n; d=1+z*z/n; m=(q+z*z/(2*n))/d; h=z*math.sqrt(q*(1-q)/n+z*z/(4*n*n))/d
 return [m-h,m+h]
def main():
 accounting=read('ACCOUNTING.json')
 if accounting['status']=='RUNNING' or (P/'RUN.lock').exists(): raise SystemExit('Refuse scoring while execution is active')
 protocol=read('PROTOCOL.json'); manifest=read('MANIFEST.json'); labels=read('labels/owner-verdicts.json')
 assert hashlib.sha256((P/'labels/owner-verdicts.json').read_bytes()).hexdigest()==protocol['labels_sha256']
 truths={x['case_id']:x['label_exact'] for x in labels}; options=protocol['options']; n=len(manifest)
 constants={o:sum(v==o for v in truths.values()) for o in options}; majority=max(options,key=lambda o:constants[o])
 clusters=collections.defaultdict(list)
 for c in manifest: clusters[c['lineage_cluster']].append(c['case_id'])
 result={'n':n,'constant_correct':constants,'majority_oracle':majority,'development_majority':'N/A: no compatible frozen four-way development cohort','confidence_limits':'Wilson intervals assume independent Bernoulli cases, which related artifacts violate. Cluster bootstrap is descriptive; few heterogeneous clusters and one owner limit generalization.','cluster_n':len(clusters),'protocol_limitations':protocol['limitations'],'design':protocol['study_design'],'routes':{},'accounting':accounting,'method_comparison':'No personalized method arm was run. RAW errors or losses to a constant are not evidence that our method beats frontier models.'}
 total=Decimal('0'); percase=[]
 for route in ['anthropic','openai']:
  rows=[]; costs=Decimal('0')
  for c in manifest:
   cid=c['case_id']; f=P/'responses'/f'{cid}-{route}.json'; row={'case_id':cid,'id':c['id'],'truth':truths[cid],'cluster':c['lineage_cluster'],'choice':None,'valid':False,'reason':None,'error':None}
   if not f.exists(): row['error']='missing response'
   else:
    raw=json.loads(f.read_text()); assert raw['input_sha256']==c['input_sha256'] and raw['poster_sha256']==c['poster_sha256']
    try:
     response=raw['response']; choice=response['choices'][0]; content=json.loads(choice['message']['content']); row['finish_reason']=choice['finish_reason']; row['model']=response['model']; row['choice']=content.get('choice'); row['reason']=content.get('reason'); row['valid']=choice['finish_reason']=='stop' and row['choice'] in options
     if not row['valid']: row['error']='invalid choice or non-stop/truncated completion'
     cost=Decimal(str(raw['actual_reported_cost_usd'])); costs+=cost; row['cost_usd']=str(cost)
    except (KeyError,IndexError,TypeError,ValueError) as e: row['error']=type(e).__name__+': '+str(e)
   row['correct']=row['valid'] and row['choice']==row['truth']; rows.append(row)
  correct=sum(x['correct'] for x in rows); base=constants[majority]
  deltas={x['case_id']:int(x['correct'])-int(x['truth']==majority) for x in rows}
  rng=random.Random(20261108); keys=sorted(clusters); boots=[]
  for _ in range(20000):
   chosen=[rng.choice(keys) for _ in keys]; ids=[cid for key in chosen for cid in clusters[key]]; boots.append(sum(deltas[cid] for cid in ids)/len(ids))
  boots.sort(); b=sum(x['correct'] and x['truth']!=majority for x in rows); d=sum(not x['correct'] and x['truth']==majority for x in rows); discord=b+d
  p=min(1,2*sum(math.comb(discord,i) for i in range(min(b,d)+1))/(2**discord)) if discord else 1
  result['routes'][route]={'model':next((r.get('model') for r in rows if r.get('model')),None),'correct':correct,'n':n,'accuracy':correct/n,'wilson95':wilson(correct,n),'invalid_or_missing':sum(not x['valid'] for x in rows),'difference_from_majority_constant':(correct-base)/n,'cluster_bootstrap_difference95':[boots[499],boots[19499]],'paired_discordant_model_only':b,'paired_discordant_constant_only':d,'exploratory_exact_mcnemar_p':p,'class_recall':{o:{'correct':sum(x['correct'] and x['truth']==o for x in rows),'n':constants[o]} for o in options},'spent_usd':str(costs)}
  percase.extend(dict(x,route=route) for x in rows); total+=costs
 result['known_usage_cost_usd']=str(total); result['accounting_reconciled']=total==Decimal(accounting['spent_usd']); assert result['accounting_reconciled']
 result['routes']['venice']={'status':'NOT_RUN_KEY_NOT_AVAILABLE','n':0,'not_a_model_failure':True}
 (P/'SCORES.json').write_text(json.dumps(result,indent=2)+'\n'); (P/'CASE-SCORES.json').write_text(json.dumps(percase,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__': main()
