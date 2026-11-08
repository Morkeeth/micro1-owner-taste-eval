"""Frozen retrospective poster test. Sequential, no retries/fallback or label reads."""
import base64, decimal, hashlib, json, os, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).parent
D=decimal.Decimal
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
    os.replace(tmp,p)
def now():return datetime.now().astimezone().isoformat()
def can_reserve(spent,reserve):return D(str(spent))+D(str(reserve))<=D('10')
def main():
    assert not sys.flags.optimize
    freeze=json.loads((ROOT/'FREEZE.json').read_text())
    for file,key in [('PROTOCOL.json','protocol_sha256'),('MANIFEST.json','manifest_sha256')]:
        assert digest(ROOT/file)==freeze[key],file
    protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    execution=json.loads((ROOT/'EXECUTION.json').read_text())
    assert execution['protocol_sha256']==freeze['protocol_sha256']
    assert execution['budget_usd']==10 and execution['max_tokens']==2048
    key=os.environ['OPENROUTER_API_KEY']
    (ROOT/'responses').mkdir(exist_ok=True)
    lock=ROOT/'RUN.lock';lock.mkdir()
    account={'at':now(),'cap_usd':'10','spent_usd':'0','reserved_usd':'0','completed':0,'status':'RUNNING'}
    save(ROOT/'ACCOUNTING.json',account)
    def post(body):
        req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
    try:
        for case in manifest:
            inp_path=Path(case['input']);assert digest(inp_path)==case['input_sha256']
            inp=json.loads(inp_path.read_text());image=Path(inp['poster']);assert digest(image)==inp['poster_sha256']
            mime='image/png' if image.suffix=='.png' else 'image/webp' if image.suffix=='.webp' else 'image/jpeg'
            content=[{'type':'text','text':protocol['model_prompt']+'\n\nCASE\n'+json.dumps({'case_id':inp['case_id'],'card':inp['shown_card_text'],'visual_input_policy':inp['visual_input_policy']},ensure_ascii=False)}, {'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(image.read_bytes()).decode()}}]
            for route in execution['routes']:
                output=ROOT/'responses'/(case['case_id']+'-'+route['pin']+'.json')
                assert not output.exists(),'No rerun/overwrite permitted'
                reserve=D(route['per_request_reserve_usd'])
                if not can_reserve(account['spent_usd'],reserve):
                    account.update(status='STOPPED_BEFORE_DISPATCH_BUDGET',next_case=case['case_id'],next_route=route['pin']);save(ROOT/'ACCOUNTING.json',account);return
                body={'model':route['model'],'messages':[{'role':'user','content':content}],'max_tokens':2048,'reasoning':{'effort':'medium'},'provider':{'only':[route['pin']],'allow_fallbacks':False,'require_parameters':True,'max_price':route['max_price']},'plugins':[],'transforms':[], 'response_format':{'type':'json_schema','json_schema':{'name':'owner_choice','strict':True,'schema':{'type':'object','properties':{'choice':{'type':'string','enum':protocol['options']},'reason':{'type':'string'}},'required':['choice','reason'],'additionalProperties':False}}}}
                request_hash=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
                account.update(reserved_usd=str(reserve),current_case=case['case_id'],current_route=route['pin'],at=now());save(ROOT/'ACCOUNTING.json',account)
                try:
                    response=post(body)
                except Exception as error:
                    # An ambiguous network failure can be billed. Retain full reserve; never retry.
                    save(output,{'at':now(),'case_id':case['case_id'],'route':route,'request_sha256':request_hash,'error_type':type(error).__name__,'error_body':error.read().decode(errors='replace') if isinstance(error,urllib.error.HTTPError) else str(error),'charge_status':'UNKNOWN_FULL_RESERVE_RETAINED'})
                    account.update(status='STOPPED_AMBIGUOUS_REQUEST_NO_RETRY');save(ROOT/'ACCOUNTING.json',account);return
                cost=response.get('usage',{}).get('cost')
                save(output,{'at':now(),'case_id':case['case_id'],'route':route,'input_sha256':case['input_sha256'],'poster_sha256':inp['poster_sha256'],'request_sha256':request_hash,'response':response,'actual_reported_cost_usd':cost})
                if cost is None or not isinstance(cost,(int,float,str)) or D(str(cost))<0:
                    account.update(status='STOPPED_UNKNOWN_BILLING_FULL_RESERVE_RETAINED');save(ROOT/'ACCOUNTING.json',account);return
                actual=D(str(cost))
                if actual>reserve:
                    account.update(status='STOPPED_PROVIDER_BOUND_VIOLATION',reported_cost_usd=str(actual));save(ROOT/'ACCOUNTING.json',account);return
                account.update(spent_usd=str(D(account['spent_usd'])+actual),reserved_usd='0',completed=account['completed']+1,at=now());save(ROOT/'ACCOUNTING.json',account)
                print(json.dumps({'case':case['case_id'],'route':route['pin'],'completed':account['completed'],'spent_usd':account['spent_usd']}),flush=True)
                if response.get('error'):
                    account.update(status='STOPPED_PROVIDER_ERROR');save(ROOT/'ACCOUNTING.json',account);return
                if response.get('model') not in route['allowed_response_models']:
                    account.update(status='STOPPED_MODEL_ID_MISMATCH',actual_model=response.get('model'));save(ROOT/'ACCOUNTING.json',account);return
        account.update(status='COMPLETED_AVAILABLE_OPENROUTER_ROUTES',venice='NOT_RUN_KEY_NOT_AVAILABLE');save(ROOT/'ACCOUNTING.json',account)
    finally:
        lock.rmdir()
if __name__=='__main__':main()
