import csv
import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

API = Path(__file__).resolve().parents[1] / "api"
sys.path.insert(0, str(API))
import review  # noqa: E402


def _setup(tmp_path, monkeypatch):
    evaluation = tmp_path / "evaluation"
    source = tmp_path / "source"
    evaluation.mkdir(); source.mkdir()
    fields = ["resume_id", "jd_id", "gold_facts", "gold_requirements", "gold_matches", "gold_entities", "review_status", "confidence", "review_notes"]
    with (evaluation / "gold_label_review.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerow({"resume_id": "1", "jd_id": "jd-1", "review_status": "needs_human_review", "confidence": "medium"})
    profile = {"profile_id": 1, "roles": ["Backend Engineer"], "skills_primary": ["Python"], "skills_secondary": ["Docker"], "experience_years": 3, "seniority": "Mid", "domains": ["E-commerce"], "preferences": {"locations": ["Bangalore"]}}
    job = {"id": "jd-1", "title": "Backend Engineer", "description": "Required: Python experience. Build REST APIs."}
    (source / "synthetic_profiles.json").write_text(json.dumps([profile]), encoding="utf-8")
    (source / "scraped_jobs.json").write_text(json.dumps([job]), encoding="utf-8")
    (source / "benchmarks.json").write_text(json.dumps({"jobs": []}), encoding="utf-8")
    monkeypatch.setattr(review.settings, "evaluation_dir", evaluation)
    monkeypatch.setattr(review.settings, "evaluation_source_dir", source)
    return evaluation, source


def test_save_review_builds_source_grounded_gold_json(tmp_path, monkeypatch):
    evaluation, source = _setup(tmp_path, monkeypatch)
    source_before = (source / "synthetic_profiles.json").read_text(encoding="utf-8")
    payload = review.ReviewSave(
        fact_keys=["skills_primary:1", "experience_years"],
        requirements=[review.RequirementDraft(text="Python", type="hard_skill", must_have=True, min_years=0, canonical_skills=["python"])],
        matches=[review.MatchDraft(fact_keys=["skills_primary:1"], status="covered", method="lexical")],
        decision="match", confidence="high", notes="Direct Python evidence.", action='accept',
    )
    response = review.save_review(0, payload)
    assert response["review_status"] == "reviewed_match"
    with (evaluation / "gold_label_review.csv").open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    facts = json.loads(row["gold_facts"])
    assert [fact["text"] for fact in facts] == ["Python", "3 years of experience"]
    assert json.loads(row["gold_matches"])[0]["fact_ids"] == ["F01"]
    assert json.loads(row["gold_entities"])["allowed_entities"] == ["3", "Python"]
    assert (source / "synthetic_profiles.json").read_text(encoding="utf-8") == source_before


def test_review_rejects_invented_fact_and_requirement(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with pytest.raises(HTTPException, match="source-supported"):
        review._validate_and_build(review.ReviewSave(fact_keys=["skills_primary:99"], draft=True), {"skills_primary": ["Python"]}, {"title": "", "description": "Python"}, False)
    with pytest.raises(HTTPException, match="exact phrase"):
        review._validate_and_build(
            review.ReviewSave(fact_keys=[], requirements=[review.RequirementDraft(text="Kubernetes", type="tool", must_have=True, min_years=0)], matches=[review.MatchDraft(status="missing", method="none")], draft=True),
            {"skills_primary": ["Python"]}, {"title": "", "description": "Python"}, False,
        )


def proposal_fixture(evaluation):
    proposal = {'status':'proposal', 'fact_keys':['skills_primary:1'],
        'requirements':[{'req_id':'R01','text':'Python','type':'hard_skill','must_have':True,'min_years':0,'canonical_skills':['python']}],
        'matches':[{'req_id':'R01','fact_ids':['F01'],'status':'covered','method':'lexical','score':0.92}],
        'decision':'partial', 'confidence':'medium', 'notes':'Proposal reference'}
    (evaluation/'annotation_proposals.json').write_text(json.dumps({'proposals':{'0':proposal}}),encoding='utf-8')
    return proposal


def test_prefill_reads_ids_scores_without_writing_gold(tmp_path, monkeypatch):
    evaluation,_=_setup(tmp_path,monkeypatch)
    proposal_fixture(evaluation)
    before=(evaluation/'gold_label_review.csv').read_bytes()
    result=review.review_pair(0)
    assert result['origin']=='proposal'
    assert result['seed']['fact_keys']==['skills_primary:1']
    assert result['seed']['matches'][0]['fact_keys']==['skills_primary:1']
    assert result['seed']['matches'][0]['score']==.92
    assert result['seed']['matches'][0]['method']=='lexical'
    assert result['seed']['matches'][0]['status']=='covered'
    assert result['validation_errors']==[]
    assert (evaluation/'gold_label_review.csv').read_bytes()==before


def test_accept_edit_reopen_preserves_evidence_score_and_human_decision(tmp_path,monkeypatch):
    evaluation,_=_setup(tmp_path,monkeypatch);proposal_fixture(evaluation)
    result=review.review_pair(0)
    payload=review.ReviewSave(**result['seed'],action='accept',revision=result['revision'])
    payload.decision='mismatch'
    payload.notes='Human corrected overall decision'
    review.save_review(0,payload)
    reopened=review.review_pair(0)
    assert reopened['origin']=='gold'
    assert reopened['seed']['decision']=='mismatch'
    assert reopened['seed']['matches'][0]['score']==.92
    assert reopened['seed']['matches'][0]['fact_keys']==['skills_primary:1']
    assert reopened['row']['review_status']=='reviewed_mismatch'
    assert json.loads(reopened['row']['gold_entities'])['allowed_entities']==['Python']


def test_draft_keeps_incomplete_edits_and_does_not_write_gold(tmp_path,monkeypatch):
    evaluation,_=_setup(tmp_path,monkeypatch);proposal_fixture(evaluation)
    before=(evaluation/'gold_label_review.csv').read_bytes()
    result=review.review_pair(0)
    payload=review.ReviewSave(**result['seed'],action='draft',revision=result['revision'])
    payload.requirements[0].text=''  # unfinished text must be resumable
    payload.decision='mismatch';payload.notes='Continue tomorrow'
    review.save_review(0,payload)
    reopened=review.review_pair(0)
    assert reopened['origin']=='draft'
    assert reopened['seed']['requirements'][0]['text']==''
    assert reopened['seed']['decision']=='mismatch'
    assert reopened['seed']['notes']=='Continue tomorrow'
    assert (evaluation/'gold_label_review.csv').read_bytes()==before
    with pytest.raises(HTTPException,match='another tab'):
        review.save_review(0,payload)


def test_reject_never_promotes_or_removes_gold(tmp_path,monkeypatch):
    evaluation,_=_setup(tmp_path,monkeypatch);proposal_fixture(evaluation)
    review.save_review(0,review.ReviewSave(action='reject'))
    result=review.review_pair(0)
    assert result['rejected']
    assert result['row']['review_status']=='proposal_rejected'
    assert not result['row']['gold_facts']
    review.save_review(0,review.ReviewSave(**result['seed'],action='accept'))
    accepted=review.review_pair(0)['row']
    review.save_review(0,review.ReviewSave(action='reject'))
    assert review.review_pair(0)['row']==accepted


def test_implicit_accept_and_bad_requirement_references_rejected(tmp_path,monkeypatch):
    evaluation,_=_setup(tmp_path,monkeypatch);proposal_fixture(evaluation)
    payload=review.ReviewSave(**review.review_pair(0)['seed'])
    with pytest.raises(HTTPException,match='Explicit ACCEPT'):
        review.save_review(0,payload)
    payload.action='accept';payload.matches[0].req_id='R99'
    with pytest.raises(HTTPException,match='requirement ID'):
        review.save_review(0,payload)


@pytest.mark.parametrize('phrase,kind',[
    ('Strong experience in Java','hard_skill'),('Hands-on Spring Boot','hard_skill'),
    ('Microservices','hard_skill'),('Kafka','hard_skill'),('PostgreSQL','hard_skill'),
    ('REST APIs','hard_skill'),('Bachelor degree','qualification'),
    ('3 years experience','qualification'),('AWS certification','qualification')])
def test_type_classification(phrase,kind):
    from review_annotations import requirement_atoms
    atom=requirement_atoms({'text':phrase,'type':'qualification','canonical_skills':[phrase.split()[-1]],'must_have':True})[0]
    assert atom['type']==kind


def test_atomic_conjunction_and_optional_alternatives():
    from review_annotations import requirement_atoms, explicit_skill_match
    base={'type':'qualification','must_have':False,'min_years':0}
    combined=requirement_atoms({**base,'text':'Familiarity with Docker & Kubernetes','canonical_skills':['docker','kubernetes']})
    assert [r['text'] for r in combined]==['Docker','Kubernetes']
    assert all(not r['must_have'] for r in combined)
    cloud=requirement_atoms({**base,'text':'Cloud platforms (AWS / Azure / GCP)','canonical_skills':['aws','azure','gcp']})
    assert len(cloud)==1 and cloud[0]['logic']=='any'
    aws=[{'key':'a','type':'skill','text':'AWS'}]
    assert explicit_skill_match(cloud[0],aws)['status']=='covered'
    docker=[{'key':'d','type':'skill','text':'Docker'}]
    assert [explicit_skill_match(r,docker)['status'] for r in combined]==['covered','missing']
    assert requirement_atoms({'text':'CI/CD','type':'hard_skill','canonical_skills':['ci/cd'],'must_have':True})[0]['logic']=='single'


def test_combined_skill_cannot_be_accepted_as_atomic(tmp_path,monkeypatch):
    _setup(tmp_path,monkeypatch)
    payload=review.ReviewSave(fact_keys=['skills_primary:1'],decision='partial',action='accept',
        requirements=[review.RequirementDraft(text='Python and Docker',type='hard_skill',must_have=True,min_years=0,canonical_skills=['python','docker'])],
        matches=[review.MatchDraft(status='covered',method='lexical',fact_keys=['skills_primary:1'])])
    with pytest.raises(HTTPException,match='atomic'):
        review._validate_and_build(payload,{'skills_primary':['Python']},{'description':'Python and Docker'},True)


def test_prefill_maps_reordered_matches_by_id_and_no_cross_pair_state():
    from review_annotations import prefill
    options=review._fact_options({'skills_primary':['Python','Docker']})
    seed={'fact_keys':['skills_primary:1','skills_primary:2'],
          'requirements':[{'req_id':'R01','text':'Python'},{'req_id':'R02','text':'Docker'}],
          'matches':[{'req_id':'R02','fact_ids':['F02'],'status':'covered','method':'lexical'},
                     {'req_id':'R01','fact_ids':[],'status':'missing','method':'none'}]}
    resolved=prefill(seed,options)
    assert resolved['matches'][0]['fact_keys']==[]
    assert resolved['matches'][1]['fact_keys']==['skills_primary:2']
    assert prefill({},options)['matches']==[]
