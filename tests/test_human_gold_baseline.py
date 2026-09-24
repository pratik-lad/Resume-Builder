"""Evaluation isolation: rejected proposals must never enter ground truth."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'api'))
spec = importlib.util.spec_from_file_location('human_gold_baseline', ROOT / 'eval/human_gold_baseline.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


def fixture_row():
    profile = {'profile_id': 1, 'skills_primary': ['Python']}
    option = baseline.review._fact_options(profile)[0]
    fact = {'fact_id': 'F01', 'type': option['type'], 'text': option['text'], 'entities': option['entities']}
    requirement = {'req_id': 'R01', 'text': 'Python', 'type': 'hard_skill', 'must_have': True}
    match = {'req_id': 'R01', 'fact_ids': ['F01'], 'score': 1.0, 'status': 'covered', 'method': 'lexical'}
    entities = {'by_fact_id': {'F01': option['entities']}, 'allowed_entities': ['Python']}
    row = {'resume_id': '1', 'jd_id': 'j1', 'review_status': 'reviewed_match',
           **{key: json.dumps(value) for key, value in {
               'gold_facts': [fact], 'gold_requirements': [requirement],
               'gold_matches': [match], 'gold_entities': entities}.items()}}
    return row, {1: profile}, {'j1': {'title': 'Python Developer', 'description': 'Required Python'}}


def test_only_accepted_gold_enters_baseline():
    row, profiles, jobs = fixture_row()
    report, accepted = baseline.audit([row], profiles, jobs)
    assert len(accepted) == 1
    assert not report['all_50_complete']
    row['review_status'] = 'proposal_rejected'
    assert baseline.audit([row], profiles, jobs)[1] == []


@pytest.mark.parametrize('field,value', [
    ('gold_matches', [{'req_id': 'R99', 'fact_ids': ['F01'], 'score': 1, 'status': 'covered'}]),
    ('gold_matches', [{'req_id': 'R01', 'fact_ids': ['F99'], 'score': 1, 'status': 'covered'}]),
    ('gold_entities', {'by_fact_id': {}, 'allowed_entities': ['Kubernetes']}),
    ('gold_facts', []),
])
def test_invalid_gold_excluded(field, value):
    row, profiles, jobs = fixture_row()
    row[field] = json.dumps(value)
    report, accepted = baseline.audit([row], profiles, jobs)
    assert not accepted
    assert report['records'][0]['errors']


def test_duplicate_pair_not_counted_twice():
    row, profiles, jobs = fixture_row()
    report, accepted = baseline.audit([row, row], profiles, jobs)
    assert len(accepted) == 1
    assert 'duplicate pair' in report['records'][1]['errors']


def test_metric_math_and_empty_denominators():
    result = baseline.classification(['a', 'a', 'b', 'b'], ['a', 'b', 'b', 'b'])
    assert result['accuracy'] == .75
    assert result['kappa'] == .5
    assert baseline.classification([], [])['accuracy'] is None
    assert baseline.latency([1, 2, 3, 4])['p50'] == 2.5
    assert baseline.latency([])['p50'] is None
