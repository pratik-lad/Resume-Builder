"""Read-only matcher calibration diagnostics on accepted human gold pairs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, '/app')
import review
from config import settings
from schemas import RequirementSet
from pipeline import match as match_stage


def split_name(row):
    label = row['review_status'].removeprefix('reviewed_')
    if label == 'match':
        return 'calibration'
    digest = int(hashlib.sha256(f"{row['resume_id']}|{row['jd_id']}".encode()).hexdigest(), 16)
    return 'holdout' if digest % 5 == 0 else 'calibration'


def main():
    rows, _ = review._read_rows()
    profiles, jobs = review._sources()
    records = []
    for number, row in enumerate(rows, 1):
        if not row['review_status'].startswith('reviewed_'):
            continue
        facts = json.loads(row['gold_facts'])
        reqs = json.loads(row['gold_requirements'])
        from schemas import Fact, Requirement
        facts = [Fact.model_validate(x) for x in facts]
        reqs = [Requirement.model_validate(x) for x in reqs]
        job = jobs[row['jd_id']]
        raw = '\n'.join(f.text for f in facts)
        predicted, card, _ = match_stage.run(
            RequirementSet(role_title=job.get('title',''), jd_text=job.get('description',''), requirements=reqs),
            facts, raw)
        must = [m for m, r in zip(predicted, reqs) if r.must_have]
        hard = [m for m, r in zip(predicted, reqs) if r.type in ('hard_skill','tool')]
        records.append({
            'pair_number': number, 'resume_id': row['resume_id'], 'jd_id': row['jd_id'],
            'gold': row['review_status'].removeprefix('reviewed_'), 'split': split_name(row),
            'score': card.jd_alignment_score,
            'hard': card.hard_skill_coverage, 'resp': card.responsibility_match,
            'qual': card.qualification_match, 'keyword': card.keyword_surface,
            'requirements': len(reqs), 'must_requirements': len(must),
            'covered': sum(m.status == 'covered' for m in predicted),
            'partial': sum(m.status == 'partial' for m in predicted),
            'missing': sum(m.status == 'missing' for m in predicted),
            'must_covered': sum(m.status == 'covered' for m in must),
            'must_partial': sum(m.status == 'partial' for m in must),
            'hard_covered': sum(m.status == 'covered' for m in hard),
            'hard_partial': sum(m.status == 'partial' for m in hard),
            'lexical': sum(m.method in ('lexical','fuzzy') for m in predicted),
            'semantic': sum(m.method == 'semantic' for m in predicted),
        })
        print(f"{number}/50 {records[-1]['gold']} score={card.jd_alignment_score}", flush=True)
    out = Path('/data/evaluation/matching-calibration-input.json')
    out.write_text(json.dumps({'config': {
        'low_fit_score': settings.low_fit_score, 'partial_threshold': settings.partial_threshold,
        'covered_threshold': settings.covered_threshold,
        'split_rule': 'match in calibration; other labels holdout when sha256(resume_id|jd_id) mod 5 == 0'},
        'split_counts': dict(Counter(f"{r['split']}:{r['gold']}" for r in records)),
        'records': records}, indent=2), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
