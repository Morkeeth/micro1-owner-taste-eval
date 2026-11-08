"""Offline replay: re-score both studies from saved model outputs. No network, no API key."""
import subprocess,sys,json
from pathlib import Path
R=Path(__file__).resolve().parent
for d,s in [('study-a-retrospective-31','score_frozen.py'),('study-b-prospective-34','score_prospective.py')]:
    print('==',d); out=subprocess.run([sys.executable,'-I',str(R/d/s)],capture_output=True,text=True,cwd=R/d)
    if out.returncode: print(out.stderr); sys.exit(1)
    res=json.loads((R/d/'SCORES.json').read_text())
    if 'routes' in res:
        for k,v in res['routes'].items():
            if 'correct' in v: print(f"  {k}: {v['correct']}/{v['n']}")
        print('  always AWESOME:',res['constant_correct']['AWESOME, USE IT'],'/',res['n'])
    else:
        a=res['all']; print('  always AWESOME:',a['constant_correct'],'/',a['n'])
        for k in ['RAW-anthropic','RAW-openai','HISTORY-anthropic','HISTORY-openai']:
            v=a[k]; print(f'  {k}:', f"{v['correct']}/{a['n']}" if isinstance(v,dict) else v)
