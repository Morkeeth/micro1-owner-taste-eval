"""Freeze the post-study four-way owner decisions as a prospective holdout. No network, no model calls."""
import json,hashlib,shutil,sys
from pathlib import Path
ROOT=Path(__file__).parent; RQ=Path.home()/'.local/state/fleet/review-queue'
OLD=ROOT.parent/'MICRO1-OWNER-WINDOW-FROZEN-e87f7594'
OPTS=["AWESOME, USE IT","EDIT THIS ONE","NEEDS NEW CONTENT","KILL THIS ONE"]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
study_ids={c['id'] for c in json.load(open(OLD/'MANIFEST.json'))}
assert len(study_ids)==31
seen=set();rows=[]
for n,l in enumerate(open(RQ/'verdicts.jsonl'),1):
    try:d=json.loads(l)
    except Exception:continue
    if d.get('verdict') in OPTS and d['id'] not in seen:
        seen.add(d['id']);d['_line']=n;rows.append(d)
later=[r for r in rows if r['id'] not in study_ids]
manifest=[];labels=[];attrition=[]
for i,r in enumerate(later,1):
    cid='P%03d'%i
    snap=RQ/'snapshots'/r['id']/(r['card_sha256'][:16]+'.json')
    if not snap.exists() or sha(snap)!=r['card_sha256']:
        attrition.append({'id':r['id'],'reason':'shown snapshot missing or hash mismatch'});continue
    card=json.load(open(snap))
    if card.get('options')!=OPTS: attrition.append({'id':r['id'],'reason':'options differ'});continue
    imgs=[m for m in card.get('media',[]) if Path(m).suffix.lower() in ('.jpg','.jpeg','.png','.webp') and Path(m).exists()]
    if not imgs: attrition.append({'id':r['id'],'reason':'no existing shown still'});continue
    src=Path(imgs[0]); dst=ROOT/'posters'/(cid+src.suffix.lower()); shutil.copy2(src,dst)
    shutil.copy2(snap,ROOT/'shown'/(cid+'.json'))
    inp={'case_id':cid,'shown_card_text':{k:card.get(k) for k in ['title','what','why','question','options','recommendation','context']},
         'visual_input_policy':'The exact first existing still/poster shown on the source card. It is one frame, not full video or audio.',
         'poster':str(dst),'poster_sha256':sha(dst)}
    ip=ROOT/'inputs'/(cid+'.json'); ip.write_text(json.dumps(inp,ensure_ascii=False,indent=1)+'\n')
    manifest.append({'case_id':cid,'id':r['id'],'source_line':r['_line'],'verdict_timestamp':r['ts'],'shown_sha256':r['card_sha256'],
        'input':str(ip),'input_sha256':sha(ip),'original_poster':str(src),'poster_sha256':inp['poster_sha256']})
    labels.append({'case_id':cid,'id':r['id'],'verdict':r['verdict'],'note':r.get('note',''),'ts':r['ts']})
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=1)+'\n')
(ROOT/'ATTRITION.json').write_text(json.dumps(attrition,indent=1)+'\n')
lp=ROOT/'labels'/'owner-verdicts.json'; lp.write_text(json.dumps(labels,ensure_ascii=False,indent=1)+'\n'); lp.chmod(0o600)
print(len(later),'later;',len(manifest),'frozen;',len(attrition),'attrition')
for m in manifest:
    c=json.load(open(m['input']))['shown_card_text']; print(m['case_id'],m['verdict_timestamp'][11:16],m['id'],'|',c['title'],'|',(c['why'] or '')[:110])
