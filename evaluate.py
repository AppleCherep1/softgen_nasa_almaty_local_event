"""Real local model evaluation and latency recording; never fabricate a benchmark."""
import argparse
import json
import math
import os
import platform
import statistics
from datetime import datetime,timezone
from pathlib import Path
from time import perf_counter
from core import extract, BackendError, model_name, warmup, PROMPT_VERSION
from guards import GUARD_VERSION

def score(expected,facts):
    actual={f['field']:f['value'] for f in facts}
    errors={k:{'expected':v,'actual':actual.get(k,'unknown')} for k,v in expected.items() if actual.get(k,'unknown')!=v}
    for k,v in actual.items():
        if k not in expected and v!='unknown':errors[k]={'expected':'unknown/omitted','actual':v}
    missed_negative=sum(expected.get(k)=='no' and actual.get(k)=='yes' for k in ('responsive','normal_breathing'))
    unjustified_reassurance=sum(expected.get(k,'unknown')=='unknown' and actual.get(k)=='yes' for k in ('responsive','normal_breathing'))
    unresolved_critical=sum(expected.get(k)=='no' and actual.get(k,'unknown')=='unknown' for k in ('responsive','normal_breathing'))
    return errors,missed_negative,unjustified_reassurance,unresolved_critical

def run(cases,model):
    os.environ['CREW_MODEL']=model
    start=perf_counter();state=warmup();warmup_ms=round((perf_counter()-start)*1000)
    report={'model':model,'status':'available' if state['ready'] else 'unavailable','total':len(cases),'tested':0,'passed':0,'raw_passed':0,'failed':[],'raw_failed':[], 'guard_interventions':0,'critical_metrics':{'raw':{'no_to_yes':0,'unknown_to_yes':0,'no_to_unknown':0},'guarded':{'no_to_yes':0,'unknown_to_yes':0,'no_to_unknown':0}},'warmup_ms':warmup_ms if state['ready'] else None,'mean_ms':None,'p50_ms':None,'p95_ms':None,'cases':[]}
    if not state['ready']:
        report['reason']='Local Ollama probe failed; no real latency or accuracy measured.';return report
    durations=[]
    for case in cases:
        start=perf_counter();actual_facts=None;raw_facts=None;warnings=[];raw_errors={}
        try:
            actual_facts=extract(case['text']);raw_facts=getattr(actual_facts,'raw_facts',list(actual_facts));warnings=getattr(actual_facts,'guard_warnings',[])
            scores={}
            for kind,facts in [('raw',raw_facts),('guarded',actual_facts)]:
                errors,low,reassure,unresolved=score(case['expected'],facts);scores[kind]=errors
                for k,v in zip(('no_to_yes','unknown_to_yes','no_to_unknown'),(low,reassure,unresolved)):report['critical_metrics'][kind][k]+=v
            errors=scores['guarded'];raw_errors=scores['raw']
        except BackendError as exc:errors=raw_errors={'backend_error':str(exc)}
        ms=round((perf_counter()-start)*1000);durations.append(ms);report['tested']+=1
        report['guard_interventions']+=len(warnings)
        record={'id':case['id'],'ms':ms,'passed':not errors,'raw_passed':not raw_errors,'guard_warnings':warnings};report['cases'].append(record)
        if errors:report['failed'].append({**record,'errors':errors,'actual':actual_facts})
        else:report['passed']+=1
        if raw_errors:report['raw_failed'].append({'id':case['id'],'errors':raw_errors,'actual':raw_facts})
        else:report['raw_passed']+=1
    report.update(mean_ms=round(statistics.mean(durations)),p50_ms=round(statistics.median(durations)),p95_ms=sorted(durations)[max(0,math.ceil(.95*len(durations))-1)])
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('cases',nargs='?',default=str(Path(__file__).with_name('eval_cases.jsonl')))
    parser.add_argument('--compare',action='store_true',help='Run qwen3:4b and qwen3:1.7b sequentially')
    parser.add_argument('--output')
    args=parser.parse_args()
    cases=[json.loads(line) for line in Path(args.cases).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not cases:parser.error('Empty evaluation set')
    models=['qwen3:4b','qwen3:1.7b'] if args.compare else [model_name()]
    reports=[run(cases,model) for model in models]
    metadata={'guard_version':GUARD_VERSION,'passed_means':'Model output AFTER guards; raw_passed separately measures validated model output BEFORE guards. Critical metrics count field-level cases, not clinical outcomes.','prompt_version':PROMPT_VERSION,'at':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),'timing':'Wall time per local extraction, includes Ollama prompt processing and decoding; startup probe excluded. May include validation and lock wait.','note':'Synthetic development suite, not clinical validation. Changed prompt/new fields require re-evaluation.'}
    result={**metadata,'models':reports} if args.compare else {**metadata,**reports[0]}
    target=args.output or ('benchmark_result.json' if args.compare else 'evaluation_result.json')
    Path(target).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2 if any(r['status']=='unavailable' for r in reports) else (1 if any(r['failed'] for r in reports) else 0)
if __name__=='__main__':raise SystemExit(main())
