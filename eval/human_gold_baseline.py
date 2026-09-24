"""Read-only gold audit and component baseline. Run inside the API container.

No proposal file is opened. Rejected/invalid rows are excluded, never relabelled.
Fresh JD predictions and rewrites are persisted as evaluation artifacts only.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time

import review
from config import settings
from schemas import Fact, Requirement, Match, RequirementSet
from pipeline import jd, match as match_stage, optimize
from matching import embedder
from validation import entity_guard, ladder

STATES = {'reviewed_match','reviewed_partial','reviewed_mismatch'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classification(gold, predicted):
    n=len(gold)
    if not n:
        return {'n':0,'accuracy':None,'kappa':None}
    acc=sum(a==b for a,b in zip(gold,predicted))/n
    ga,pr=Counter(gold),Counter(predicted)
    pe=sum(ga[k]*pr[k] for k in set(ga)|set(pr))/(n*n)
    return {'n':n,'correct':sum(a==b for a,b in zip(gold,predicted)), 'accuracy':acc,
            'kappa':(acc-pe)/(1-pe) if pe<1 else None,
            'confusion':{a:dict(Counter(b for x,b in zip(gold,predicted) if x==a)) for a in sorted(set(gold))}}


def latency(values):
    if not values: return {'n':0,'p50':None,'p95':None}
    xs=sorted(values);p=(len(xs)-1)*.95;lo=int(p)
    return {'n':len(xs),'p50':statistics.median(xs),'p95':xs[lo]+(xs[min(lo+1,len(xs)-1)]-xs[lo])*(p-lo),'max':max(xs)}


def norm(text):
    return ' '.join(text.casefold().split()).strip(' .;:')


def audit(rows,profiles,jobs):
    records=[]; valid=[]; seen=set()
    counts=Counter(row['review_status'] for row in rows)
    for i,row in enumerate(rows,1):
        errors=[]; key=(row['resume_id'],row['jd_id'])
        if key in seen: errors.append('duplicate pair')
        seen.add(key)
        if row['review_status'] not in STATES: errors.append('not accepted human review')
        values={}
        for field in ('gold_facts','gold_requirements','gold_matches','gold_entities'):
            try:
                values[field]=json.loads(row[field])
                if not values[field]: errors.append(field+' empty')
            except (ValueError,TypeError): errors.append(field+' absent/invalid JSON')
        profile=profiles.get(int(row['resume_id']));job=jobs.get(row['jd_id'])
        if profile is None or job is None: errors.append('missing source join')
        if len(values)==4 and profile and job:
            try:
                facts=[Fact.model_validate(f) for f in values['gold_facts']]
                reqs=[Requirement.model_validate(r) for r in values['gold_requirements']]
                matches=[Match.model_validate(m) for m in values['gold_matches']]
                fids={f.fact_id for f in facts}; rids={r.req_id for r in reqs}
                if len(fids)!=len(facts): errors.append('duplicate fact ID')
                if len(rids)!=len(reqs): errors.append('duplicate requirement ID')
                if any(not f.fact_id for f in facts):errors.append('blank fact ID')
                if any(not r.req_id for r in reqs):errors.append('blank requirement ID')
                mids=[m.req_id for m in matches]
                if set(mids)!=rids or len(mids)!=len(rids): errors.append('invalid/duplicate/missing match requirement ID')
                if any(not set(m.fact_ids)<=fids or len(m.fact_ids)!=len(set(m.fact_ids)) for m in matches):errors.append('invalid/duplicate referenced fact ID')
                options=review._fact_options(profile)
                for f in facts:
                    if not any(f.text==o['text'] and f.type==o['type'] and f.entities==o['entities'] for o in options):
                        errors.append('fact unsupported by source profile: '+f.fact_id)
                source=f"{job.get('title','')}\n{job.get('description','')}".casefold()
                if any(r.text.casefold() not in source for r in reqs):errors.append('requirement not present in source JD')
                expected={f.fact_id:f.entities for f in facts}
                entities=values['gold_entities']
                if entities.get('by_fact_id')!=expected: errors.append('gold entity fact map inconsistent')
                union={x for f in facts for group in f.entities.values() for x in group}
                if set(entities.get('allowed_entities',[]))!=union:errors.append('entity whitelist mismatch')
                source_entities={x for o in options for group in o['entities'].values() for x in group}
                if not set(entities.get('allowed_entities',[]))<=source_entities:errors.append('JD-only or unsupported entity in gold_entities')
                for m in matches:
                    expected_status='covered' if m.score>=settings.covered_threshold else 'partial' if m.score>=settings.partial_threshold else 'missing'
                    if not 0<=m.score<=1 or expected_status!=m.status:errors.append('invalid score/status: '+m.req_id)
                    if m.status!='missing' and not m.fact_ids:errors.append('non-missing match without evidence: '+m.req_id)
            except Exception as exc:errors.append('gold schema: '+str(exc))
        records.append({'pair_number':i,'resume_id':key[0],'jd_id':key[1],'review_status':row['review_status'],'errors':errors})
        if not errors:valid.append((i,row,facts,reqs,matches,profile,job,values['gold_entities']))
    return {'total':len(rows),'statuses':dict(counts),'valid_accepted':len(valid),
            'all_50_complete':len(rows)==50 and len(valid)==50,'records':records},valid


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    csv_path=settings.evaluation_dir/'gold_label_review.csv'
    before=digest(csv_path)
    source_hashes={name:digest(settings.evaluation_source_dir/name) for name in ('synthetic_profiles.json','scraped_jobs.json','benchmarks.json')}
    profiles,jobs=review._sources();rows,_=review._read_rows()
    validation,valid=audit(rows,profiles,jobs)
    report={'started_at':datetime.now(timezone.utc).isoformat(),'ground_truth':'accepted gold_* CSV fields only',
      'gold_csv_sha256':before,'source_sha256':source_hashes,'validation':validation,
      'scope':'Provisional component baseline on accepted structured profiles. No original resume PDF/DOCX is linked. Gold facts and requirements supplied as inputs isolate matching; fresh JD extraction measured separately.',
      'config':{k:v for k,v in settings.model_dump(mode='json').items() if k in ('model_extract','model_rewrite','seed','temp_extract','temp_rewrite','embed_model','embed_enabled','sem_cal_min','sem_cal_max','covered_threshold','partial_threshold','fuzzy_threshold','low_fit_score','max_bullets','max_repair_attempts')},
      'cases':[], 'jd_predictions':{},'metrics':{}}
    def checkpoint(stage):
        report['stage']=stage
        (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    checkpoint('validated')
    print(json.dumps({'validation':{k:v for k,v in validation.items() if k!='records'},'excluded':[r for r in validation['records'] if r['errors']]}),flush=True)
    if args.validate_only:return
    if not valid:raise RuntimeError('No valid human gold rows')
    gold_status=[];pred_status=[];pairs_gold=[];pairs_pred=[];rejected=[];mismatch=[]
    for number,row,facts,reqs,matches,profile,job,entities in valid:
        raw='\n'.join(f.text for f in facts)
        rs=RequirementSet(role_title=job.get('title',''),jd_text=job.get('description',''),requirements=reqs)
        start=time.perf_counter();pred,card,gaps=match_stage.run(rs,facts,raw);elapsed=time.perf_counter()-start
        gm={m.req_id:m for m in matches}
        gold_status.extend(gm[m.req_id].status for m in pred);pred_status.extend(m.status for m in pred)
        pairs_gold.append(row['review_status'].removeprefix('reviewed_'))
        pairs_pred.append(card.fit_decision)
        rejected.append(card.fit_decision=='mismatch');mismatch.append(row['review_status']=='reviewed_mismatch')
        report['cases'].append({'pair_number':number,'resume_id':row['resume_id'],'jd_id':row['jd_id'],
         'gold_fit':pairs_gold[-1],'predicted_fit':pairs_pred[-1],'match_seconds':elapsed,'score_card':card.model_dump(),
         'predicted_matches':[m.model_dump() for m in pred],
         'match_errors':[{'req_id':m.req_id,'gold':gm[m.req_id].status,'predicted':m.status,'method':m.method} for m in pred if gm[m.req_id].status!=m.status]})
        print(f"MATCH {len(report['cases'])}/{len(valid)} pair {number} score={card.jd_alignment_score} gold={pairs_gold[-1]}",flush=True)
    tp=sum(a and b for a,b in zip(rejected,mismatch));fp=sum(a and not b for a,b in zip(rejected,mismatch));fn=sum(not a and b for a,b in zip(rejected,mismatch))
    report['metrics'].update(requirement_matching=classification(gold_status,pred_status),pair_fit=classification(pairs_gold,pairs_pred),
      mismatch_rejection={'tp':tp,'fp':fp,'fn':fn,'tn':len(valid)-tp-fp-fn,'recall':tp/(tp+fn) if tp+fn else None,'precision':tp/(tp+fp) if tp+fp else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,'gate':'score_card.fit_decision == mismatch'},
      match_latency=latency([c['match_seconds'] for c in report['cases']]),embeddings_available=embedder.available())
    checkpoint('matching complete')
    for job_id in dict.fromkeys(v[1]['jd_id'] for v in valid):
        job=jobs[job_id];start=time.perf_counter()
        try:
            output=jd.extract(job.get('title','')+'\n\n'+job.get('description',''))
            report['jd_predictions'][job_id]={'requirements':[r.model_dump() for r in output.requirements],'seconds':time.perf_counter()-start}
        except Exception as exc:
            report['jd_predictions'][job_id]={'requirements':[],'seconds':time.perf_counter()-start,'error':str(exc)}
        print(f"JD {len(report['jd_predictions'])}/{len(set(v[1]['jd_id'] for v in valid))} {job_id}",flush=True);checkpoint('extracting JDs')
    gold_types=[];pred_types=[];gold_flags=[];pred_flags=[];exact_tp=exact_gold=exact_pred=0
    aligned_gold=0;alignment_records=[]
    for number,row,facts,reqs,matches,profile,job,entities in valid:
        predicted=report['jd_predictions'][row['jd_id']]['requirements']
        gs=Counter(norm(r.text) for r in reqs);ps=Counter(norm(r['text']) for r in predicted)
        exact_tp+=sum((gs&ps).values());exact_gold+=sum(gs.values());exact_pred+=sum(ps.values())
        for req in reqs:
            candidates=[r for r in predicted if norm(r['text'])==norm(req.text)]
            if not candidates:
                parent=req.source_text or req.text
                candidates=[r for r in predicted if norm(r['text'])==norm(parent)]
            # Alignment requires literal reviewed phrase/context equality. No
            # semantic matching or proposal labels decide evaluation alignment.
            if len(candidates)==1:
                p=candidates[0];aligned_gold+=1;gold_types.append(req.type);pred_types.append(p['type']);gold_flags.append(req.must_have);pred_flags.append(p['must_have'])
                alignment_records.append({'pair_number':number,'req_id':req.req_id,'gold_type':req.type,'predicted_type':p['type'],'gold_must':req.must_have,'predicted_must':p['must_have']})
    report['requirement_alignment']=alignment_records
    report['metrics'].update(requirement_type=classification(gold_types,pred_types),must_have=classification(gold_flags,pred_flags),
      requirement_alignment={'aligned_gold':aligned_gold,'total_gold':exact_gold,'coverage':aligned_gold/exact_gold},
      jd_extraction_exact={'true_positive':exact_tp,'gold':exact_gold,'predicted':exact_pred,'precision':exact_tp/exact_pred if exact_pred else 0,'recall':exact_tp/exact_gold if exact_gold else 0,'f1':2*exact_tp/(exact_gold+exact_pred) if exact_gold+exact_pred else 0},
      jd_latency=latency([r['seconds'] for r in report['jd_predictions'].values()]))
    checkpoint('JD classification complete')
    all_rewrites=[];final_texts=[];first_pass=0;reverted=0;total=0;rewrite_latencies=[];ucr_bad=ucr_total=0
    for case,(_,row,facts,reqs,matches,profile,job,entities) in zip(report['cases'],valid):
        if case['score_card']['fit_decision']=='mismatch':
            case['rewrite']={'skipped':'project low-fit gate'};continue
        raw='\n'.join(f.text for f in facts)
        # Same whitelist builder as ingest; use gold entities plus source facts,
        # never JD entities. Preserve existing validator behavior and thresholds.
        allowed=entity_guard.build_allowed(raw,[entities['allowed_entities']])
        predicted=[Match.model_validate(m) for m in case['predicted_matches']]
        start=time.perf_counter()
        try:
            result=optimize.optimize(facts,reqs,predicted,allowed)
            elapsed=time.perf_counter()-start
            case['rewrite']={'seconds':elapsed,**result.model_dump()}
            if result.rewrites:rewrite_latencies.append(elapsed)
            for rw in result.rewrites:
                all_rewrites.append(rw.model_dump());first_pass+=rw.attempts==1 and rw.status!='reverted';reverted+=rw.status=='reverted';total+=1
                bad, counted = entity_guard.claim_token_counts(rw.final, allowed)
                ucr_bad += bad; ucr_total += counted
            case['rewrite']['validation_after_rewrite']=[{'fact_id':rw.fact_id,'violations':[v.model_dump() for v in ladder.validate(rw.final,optimize._evidence(next(f for f in facts if f.fact_id==rw.fact_id)),allowed)]} for rw in result.rewrites]
        except Exception as exc:case['rewrite']={'seconds':time.perf_counter()-start,'error':str(exc)}
        print(f"REWRITE pair {case['pair_number']} {case['rewrite'].get('seconds',0):.2f}s",flush=True);checkpoint('rewriting structured profiles')
    report['metrics'].update(rewrite_latency=latency(rewrite_latencies),rewrites={'count':total,'first_pass_count':first_pass,'first_pass_rate':first_pass/total if total else None,'reverted_count':reverted,'revert_rate':reverted/total if total else None,'ucr_bad_tokens':ucr_bad,'ucr_total_tokens':ucr_total,'ucr':ucr_bad/ucr_total if ucr_total else 0.0,'scope':'validator-consistent token UCR on eligible structured-profile rewrites; zero eligible prose facts is reported separately by count'})
    report['not_measurable']={
      'resume_extraction_F1':'No linked original PDF/DOCX for these synthetic structured profiles. Supplied gold facts bypass parsing/extraction; no fabricated source documents used.',
      'full_end_to_end_p50':'No document ingest/render/n8n run over linked original resumes; component timings are not end-to-end.',
      'rewrite_p50_improvement_40_percent':'Baseline only; no tuned model comparison.',
      'first_pass_improvement_10_points':'Baseline only; no tuned model comparison.',
      'blind_AB_60_percent':'No tuned model or 50 blind human preference labels.',
      'coverage_delta_ATS_roundtrip_peak_RAM_VRAM':'Not instrumented/executed in this component baseline; no acceptance claim.',
      'independent_UCR':'Human gold annotates facts and matches, not the truth of generated rewrite claims; reported UCR uses existing token checker.'}
    report['gold_csv_unchanged']=digest(csv_path)==before
    report['sources_unchanged']=all(digest(settings.evaluation_source_dir/name)==value for name,value in source_hashes.items())
    report['completed_at']=datetime.now(timezone.utc).isoformat();checkpoint('complete')
    print(json.dumps(report['metrics'],indent=2),flush=True)


if __name__=='__main__':main()
