"""Prospective replication. Refuses to run without an Oscar YES verdict on the spend card. Sequential, no retries."""
import base64,decimal,hashlib,json,os,sys,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).parent; D=decimal.Decimal
CARD='micro1-prospective-34-spend-8nov'
CAP=D('3')
PRICE={'anthropic':(D('0.000008'),D('0.00002')),'openai':(D('0.000004'),D('0.000015'))}  # highest input category, output (catalog in ../MICRO1-OWNER-WINDOW-FROZEN-e87f7594)
ROUTES=[{'pin':'anthropic','model':'anthropic/claude-opus-5.5','allowed':['anthropic/claude-opus-5.5','anthropic/claude-opus-5.5-20260921'],'max_price':{'prompt':4,'completion':20,'request':0,'image':0}},
        {'pin':'openai','model':'openai/gpt-6.1-sol','allowed':['openai/gpt-6.1-sol','openai/gpt-6.1-sol-20260929'],'max_price':{'prompt':4,'completion':15,'request':0,'image':0}}]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def save(p,x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n'); os.replace(t,p)
def authorized():
    for l in open(Path.home()/'.local/state/fleet/review-queue/verdicts.jsonl'):
        try:d=json.loads(l)
        except Exception:continue
        if d.get('id')==CARD and d.get('verdict','').startswith('YES'): return d
    return None
def main():
    v=authorized(); assert v, 'No Oscar YES verdict on '+CARD
    fr=json.load(open(ROOT/'FREEZE.json'))
    for f in ['PROTOCOL.json','MANIFEST.json','run_prospective.py','HISTORY-BLOCK.json']: assert sha(ROOT/f)==fr[f],f
    proto=json.load(open(ROOT/'PROTOCOL.json')); man=json.load(open(ROOT/'MANIFEST.json'))
    key=os.environ['OPENROUTER_API_KEY']; (ROOT/'responses').mkdir(exist_ok=True)
    acct_p=ROOT/'ACCOUNTING.json'; assert not acct_p.exists(),'accounting exists: no rerun'
    lock=ROOT/'RUN.lock'; lock.mkdir()
    acct={'at':now(),'authority_verdict':v,'cap_usd':str(CAP),'spent_usd':'0','reserved_usd':'0','completed':0,'status':'RUNNING'}; save(acct_p,acct)
    def stop(s,**k): acct.update(status=s,at=now(),**k); save(acct_p,acct); sys.exit(s)
    try:
        for case in man:
            ip=Path(case['input']); assert sha(ip)==case['input_sha256']
            inp=json.load(open(ip)); img=Path(inp['poster']); assert sha(img)==inp['poster_sha256']
            mime='image/png' if img.suffix=='.png' else 'image/webp' if img.suffix=='.webp' else 'image/jpeg'
            casetext='\n\nCASE\n'+json.dumps({'case_id':inp['case_id'],'card':inp['shown_card_text'],'visual_input_policy':inp['visual_input_policy']},ensure_ascii=False)
            for arm in ['RAW','HISTORY']:
                text=proto['arms'][arm]['prompt']+casetext
                content=[{'type':'text','text':text},{'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(img.read_bytes()).decode()}}]
                for r in ROUTES:
                    out=ROOT/'responses'/f"{case['case_id']}-{arm}-{r['pin']}.json"; assert not out.exists()
                    pin,pout=PRICE[r['pin']]; reserve=(len(text.encode())+6000)*pin+2048*pout
                    if D(acct['spent_usd'])+reserve>CAP: stop('STOPPED_BEFORE_DISPATCH_BUDGET',next=out.name)
                    body={'model':r['model'],'messages':[{'role':'user','content':content}],'max_tokens':2048,'reasoning':{'effort':'medium'},'provider':{'only':[r['pin']],'allow_fallbacks':False,'require_parameters':True,'max_price':r['max_price']},'plugins':[],'transforms':[],'response_format':{'type':'json_schema','json_schema':{'name':'owner_choice','strict':True,'schema':{'type':'object','properties':{'choice':{'type':'string','enum':proto['options']},'reason':{'type':'string'}},'required':['choice','reason'],'additionalProperties':False}}}}
                    rh=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
                    acct.update(reserved_usd=str(reserve),current=out.name,at=now()); save(acct_p,acct)
                    try:
                        req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
                        with urllib.request.urlopen(req,timeout=120) as resp: response=json.load(resp)
                    except Exception as e:
                        save(out,{'at':now(),'arm':arm,'route':r['pin'],'request_sha256':rh,'error':type(e).__name__,'body':e.read().decode(errors='replace') if isinstance(e,urllib.error.HTTPError) else str(e),'charge_status':'UNKNOWN_FULL_RESERVE_RETAINED'})
                        stop('STOPPED_AMBIGUOUS_REQUEST_NO_RETRY')
                    cost=response.get('usage',{}).get('cost')
                    save(out,{'at':now(),'case_id':case['case_id'],'arm':arm,'route':r['pin'],'input_sha256':case['input_sha256'],'request_sha256':rh,'reserve_usd':str(reserve),'response':response,'actual_reported_cost_usd':cost})
                    if cost is None or D(str(cost))<0: stop('STOPPED_UNKNOWN_BILLING_FULL_RESERVE_RETAINED')
                    if D(str(cost))>reserve: stop('STOPPED_COST_ABOVE_RESERVE',cost=str(cost))
                    acct.update(spent_usd=str(D(acct['spent_usd'])+D(str(cost))),reserved_usd='0',completed=acct['completed']+1,at=now()); save(acct_p,acct)
                    print(json.dumps({'call':out.name,'done':acct['completed'],'spent':acct['spent_usd']}),flush=True)
                    if response.get('error'): stop('STOPPED_PROVIDER_ERROR')
                    if r['allowed'] and response.get('model') not in r['allowed']: stop('STOPPED_MODEL_ID_MISMATCH',model=response.get('model'))
        acct.update(status='COMPLETED',reserved_usd='0',at=now()); save(acct_p,acct)
    finally: lock.rmdir()
if __name__=='__main__': main()
