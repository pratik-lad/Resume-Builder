"""Formatted JD decisions, immutable job provenance and coherent comparisons."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from desktop.test_generation import input_resume
from desktop.test_project_quality import ProjectRuntime
from desktop.project_policy import select
from desktop.jd_binding import assessment_view, fingerprint, validate_completed, warnings


@pytest.mark.parametrize('form',[
    '**Experience:** {n}+ Years', '__Experience__: {n} yrs',
    '### Experience required: {n} YOE', 'Experience: minimum {n} years',
    'Minimum {n} years of relevant professional software development experience.',
    '{n}+ years of hands-on experience in software development',
    'Experience required:\n{n}+ Years', '**Minimum Experience:**\n{n}',
    'Experience: {n}', 'Experience\u00a0:\u00a0{n}\u00a0years',
])
@pytest.mark.parametrize('years,count',[(7,3),(8,5),(12,6)])
def test_equivalent_formats(form,years,count):
    jd=form.format(n=years);decision=select(jd)
    assert decision['project_count']==count and decision['jd_overall_years']==years
    assert all(p in jd for p in decision['supporting_passages'])


@pytest.mark.parametrize('jd,count,years',[
    ('**Experience:** 6–8 Years',3,6), ('**Experience:** 8–12 Years',5,8),
    ('Experience: 12 to 15 yrs',6,12), ('**Experience:** 7.5 years',3,7.5),
    ('Experience: 6 YOE\nRequired: 12 years of professional experience',6,12),
    ('Python experience: 12 years',3,None), ('Snowflake experience: 12 years',3,None),
    ('Contract duration: 12 years\nMaintain 15 years of audit data.',3,None),
    ('Month 12: take ownership\nRetention: 8 years\nExperience: 7',3,7),
    ('Experience: 2023–2026',3,None),
    ('8 years overall including 12 years Python development',5,8),
    ('6 years of hands-on experience with Snowflake',3,None),
])
def test_scope_and_noncareer_numbers(jd,count,years):
    decision=select(jd);assert decision['project_count']==count and decision['jd_overall_years']==years


def test_ambiguous_duration_is_reported_not_silently_absent():
    decision=select('Experience: 8/12')
    assert decision['project_count']==3 and decision['warnings']


def test_secondary_specialty_does_not_create_a_total_conflict():
    result=select('**Experience:** 8+ Years\nAt least 6+ years of hands-on experience with Snowflake')
    assert result['jd_overall_years']==8 and not result['warnings']


@pytest.mark.parametrize('name,count',[('snowflake',5),('full-stack',5),('data',6),('react',5),('cloud',3)])
def test_observed_jd_variants(name,count):
    from desktop.job_brief import build
    jd=(Path(__file__).parent/'fixtures'/f'project-count-{name}-jd.txt').read_text(encoding='utf-8')
    brief=build(jd,'20 years of experience','Engineer')
    assert brief['project_count_policy']==select(jd)
    assert brief['project_count_policy']['project_count']==count
    assert brief['experience']['required_overall_years']==select(jd)['jd_overall_years']


def test_comparison_rebuilds_requirements_without_mutating_generation(input_resume):
    from desktop.project_generation import generate
    from desktop.project_rules import report, report_html
    from desktop.requirement_ledger import report as ledger_report
    original='Platform Engineer\n**Experience:** 8+ years\nRequired Python and Docker.'
    doc=generate({'resume':str(input_resume),'jd':original,'_job_id':'job-A'},ProjectRuntime(),lambda *a:None)
    before=copy.deepcopy(doc)
    doc['comparison_jd']='Cloud Engineer\n**Experience:** 12 years\nRequired Azure and Terraform.'
    view=assessment_view(doc)
    assert doc['jd']==original and doc['generation_context']==before['generation_context']
    assert doc['job_brief']==before['job_brief'] and doc['sections']==before['sections']
    assert view['job_brief']['jd_sha256']==fingerprint(doc['comparison_jd'])
    terms=view['job_brief']['technologies']
    assert 'azure' in [t.lower() for t in terms] and 'terraform' in [t.lower() for t in terms]
    result=report(doc)
    assert result['project_count']['expected']==5 and result['project_count']['comparison_policy']['project_count']==6
    assert result['experience']['rows'][0]['required_years']==12
    assert 'different JD' in report_html(result)
    assert ledger_report(doc)==ledger_report(view)


def test_old_mismatched_draft_is_preserved_and_flagged(input_resume):
    from desktop.project_generation import generate
    doc=generate({'resume':str(input_resume),'jd':'Platform Engineer\nExperience: 8\nPython and Docker.'},ProjectRuntime(),lambda *a:None)
    doc.pop('generation_context');doc['jd']='Data Engineer\nExperience: 12 years\nRequired SQL.'
    before=copy.deepcopy(doc)
    assert warnings(doc)
    view=assessment_view(doc)
    assert doc==before and len(doc['projects'])==5 and view['_jd_binding']['warnings']


def test_completion_guard_rejects_missing_rendered_project(input_resume):
    from desktop.project_generation import generate
    doc=generate({'resume':str(input_resume),'jd':'Platform Engineer\nExperience: 12\nPython and Docker.'},ProjectRuntime(),lambda *a:None)
    validate_completed(doc)
    section=next(s for s in doc['sections'] if s['key']=='projects')
    section['text']=section['text'].rsplit('\n\n### Company Name:',1)[0]
    with pytest.raises(ValueError,match='expected 6 complete projects'):validate_completed(doc)


def test_gui_job_associations_and_restore(tmp_path):
    env=os.environ.copy();env.update(RESUME_DESKTOP_EDITION='projects',RESUME_DESKTOP_DATA=str(tmp_path),QT_QPA_PLATFORM='offscreen')
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'desktop/jd_ui_check.py')],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    checks=json.loads((tmp_path/'ui-check.json').read_text())
    assert all(checks.values())
