"""JD-only tiers, complete multi-project output, recovery and edited exports."""
import copy
import json
from pathlib import Path

import pytest
from desktop.test_generation import input_resume
from desktop.test_project_quality import ProjectRuntime
from desktop.project_policy import select


@pytest.mark.parametrize('jd,count,years', [
    ('Experience: 7 years',3,7), ('Experience: 8',5,8),
    ('Experience: 8+ years',5,8), ('Exp: 11 YOE',5,11),
    ('Experience: 12 years',6,12), ('Experience: 12+ yrs',6,12),
    ('Experience: 18 YOE',6,18), ('Experience: 6–8 years',3,6),
    ('Experience: 8–12 years',5,8), ('Experience: 12 to 15 years',6,12),
    ('8+ years overall, including 5+ years Python',5,8),
    ('5 years Python development; 12 years overall experience',6,12),
    ('Python experience: 12 years',3,None),
    ('12 years of Python development',3,None),
    ('Build Python services.',3,None),
    ('Experience: 6 YOE\nRequired: 8+ years delivering AI solutions',5,8),
    ('Project duration: 12 years\nExperience: 7 years',3,7),
    ('Notice: 12 years\nRetention: 8 years\nExperience: 5',3,5),
    ('Experience: 7.5 years',3,7.5),
    ('Experience: 8.5 years',5,8.5),
    ('Maintain 12 years of audit data in storage.',3,None),
    ('Up to 12 years experience',3,None),
    ('Experience: 2023–2026',3,None),
])
def test_policy_boundaries(jd,count,years):
    result=select(jd)
    assert result['project_count']==count and result['jd_overall_years']==years
    assert bool(result['supporting_passages']) == (years is not None)


def test_conflicts_and_source_independence():
    from desktop.project_experience import experience_profile
    assert select('Experience: 6 YOE\nRequired: 8 years of experience')['warnings']
    assert experience_profile('20 years of experience','Experience: 5')['overall_years']==5
    assert select('Experience: 5')['project_count']==3
    assert select('Python development')['project_count']==3  # default career total is unrelated


@pytest.mark.parametrize('years,count,base',[(7,3,11),(8,5,16),(12,6,18)])
def test_complete_generation_and_edited_reports(input_resume,years,count,base):
    from desktop.project_generation import generate
    from desktop.project_rules import report,report_html
    runtime=ProjectRuntime();events=[]
    doc=generate({'resume':str(input_resume),'jd':f'Platform Engineer\nExperience: {years} years\nRequired: Python, FastAPI, Docker.'},runtime,lambda *a:events.append(a))
    assert len(doc['roles'])==len(doc['projects'])==len(doc['experience_blocks'])==count
    assert len({p['role_id'] for p in doc['projects']})==count
    assert len({p['name'].casefold() for p in doc['projects']})==count
    assert all(len(p['technical'])==5 and len(p['functional'])==2 for p in doc['projects'])
    assert doc['generation_status']=='complete' and base<=doc['model_calls']<=27
    assert doc['quality_repair_calls']<=2 and doc['repair_calls']<=3
    assert len(doc['profile_metadata']['summary_project_ids'])==count
    section=next(s for s in doc['sections'] if s['key']=='projects')
    assert section['text'].count('### Company Name: #Confidential')==count
    assert '\nCompany Name:' not in section['text']
    assert any(f'Project {count} of {count}' in msg for _,msg in events)
    assert doc['quality']['presentation_checks']['expected_project_count']
    edited=copy.deepcopy(doc)
    section=next(s for s in edited['sections'] if s['key']=='projects')
    section['text']=section['text'].rsplit('\n\n### Company Name:',1)[0]
    review=report(edited)
    assert review['project_count']['actual']==count-1
    assert not review['presentation_checks']['expected_project_count']
    assert any('edited text' in w for w in review['warnings'])
    html=report_html(review)
    assert 'Project count review' in html and f'{count-1} projects in edited text; {count} planned.' in html


@pytest.mark.parametrize('years,count',[(8,5),(12,6)])
def test_variable_count_exports(input_resume,tmp_path,monkeypatch,years,count):
    from desktop.project_generation import generate
    from desktop.draft import export
    import desktop.bootstrap
    from docx import Document
    monkeypatch.setattr(desktop.bootstrap,'DATA',tmp_path)
    (tmp_path/'artifacts').mkdir()
    doc=generate({'resume':str(input_resume),'jd':f'Experience: {years} years\nBuild Python services using Docker.'},ProjectRuntime(),lambda *a:None)
    for kind in ('docx','html'):
        path=Path(export({'document':doc,'kind':kind,'destination':str(tmp_path/('result.'+kind))},lambda *a:None)['artifact'])
        if kind=='docx':
            out=Document(path)
            text='\n'.join(p.text for p in out.paragraphs)
            assert text.count('Company Name: #Confidential')==count
            assert all(row.cells[0].text!='Company Name:' for table in out.tables for row in table.rows)
        else:
            text=path.read_text(encoding='utf-8')
            assert text.count('<h3>Company Name: #Confidential</h3>')==count
        assert '2021' not in text


def test_failure_retains_completed_projects_separately(input_resume,tmp_path,monkeypatch):
    from desktop.project_generation import generate
    import desktop.bootstrap
    monkeypatch.setattr(desktop.bootstrap,'DATA',tmp_path)
    runtime=ProjectRuntime();runtime.client=object()
    original=runtime.chat
    def fail(messages,**kwargs):
        task=json.loads(messages[1]['content'].split('\nPrevious response')[0])['task']
        if task.startswith('Write this fictional project.') and 'Release Recovery' in task:
            raise RuntimeError('Simulated owned worker model failure')
        return original(messages,**kwargs)
    runtime.chat=fail
    with pytest.raises(ValueError,match='Incomplete generation saved separately'):
        generate({'resume':str(input_resume),'jd':'Experience: 12 years\nRequired Python and Docker.'},runtime,lambda *a:None)
    saved=json.loads(next((tmp_path/'drafts').glob('incomplete-*.json')).read_text())
    assert saved['completed_projects']==3 and saved['expected_projects']==6
    assert saved['document']['generation_status']=='incomplete'
    assert not (tmp_path/'last-draft.json').exists()


def test_request_reserve_protects_required_final_sections():
    from desktop.generation import Writer
    runtime=ProjectRuntime()
    writer=Writer(runtime,'Python',lambda *a:None,project_edition=True)
    writer.calls=23;writer.reserve_calls=4
    with pytest.raises(ValueError,match='reserved'):
        writer.ask('Optional work',lambda value:value,'quality_repair',retry=False)
    assert runtime.calls==0 and writer.calls==23


def test_large_summary_context_retains_every_project():
    from desktop.generation import Writer
    from desktop.project_profile import make_summary
    runtime=ProjectRuntime()
    runtime.token_count=lambda messages: 4000  # force complete-passage compaction
    writer=Writer(runtime,'Python services',lambda *a:None,project_edition=True)
    projects=[{'role_id':f'role_{i}','name':f'Project {i}','role':'Engineer',
               'contribution':f'Business scope {i}','tools':'Python, Docker',
               'bullets':['Built Python services using typed schemas and durable queues with validation and controlled releases.']*7} for i in range(6)]
    bullets,_=make_summary(writer,projects,'Platform Engineer',12)
    assert len(bullets)==6 and len(writer.profile_metadata['summary_project_ids'])==6
    for task in runtime.prompts:
        assert all(p['contribution'] in task for p in projects)


@pytest.mark.parametrize('source,jd,total,origin', [
    ('20 years of experience','Experience: 7 years',7,'jd'),
    ('5 years of experience','Experience: 12 YOE',12,'jd'),
    ('20 years of experience','Experience: 6\nRequired: 8+ years of experience',8,'jd'),
    ('20 years of experience','Experience: 6–8 years',6,'jd'),
    ('20 years of experience','Python Engineer',20,'source'),
    ('','Python Engineer',9,'default'),
])
def test_jd_experience_is_authoritative(source,jd,total,origin):
    from desktop.project_experience import experience_profile
    result=experience_profile(source,jd)
    assert result['overall_years']==total and result['overall_origin']==origin
    assert result['policy']=='jd-first-overall-and-specialty'


def test_source_specialty_cannot_override_jd_total_or_specialty():
    from desktop.project_experience import experience_profile
    source='20 years of experience; 15 years of full-stack development'
    result=experience_profile(source,'8 years in software development; 5 years of full-stack development')
    assert result['overall_years']==8 and result['specialties'][0]['years']==5
    result=experience_profile(source,'8 years of experience')
    assert result['overall_years']==8 and result['specialties'][0]['years']==8
    assert result['warnings']


@pytest.mark.parametrize('years,count',[(7,3),(8,5),(12,6)])
def test_high_source_experience_does_not_leak_into_generated_career(input_resume,years,count):
    from docx import Document
    from desktop.project_generation import generate
    from desktop.project_rules import report
    source=Document(input_resume);source.add_paragraph('20 years of experience');source.save(input_resume)
    result=generate({'resume':str(input_resume),'jd':f'Platform Engineer\nExperience: {years} years\nRequired Python and Docker.'},ProjectRuntime(),lambda *a:None)
    assert result['experience_years']==years and len(result['projects'])==count
    summary=next(s['text'] for s in result['sections'] if s['key']=='summary')
    assert summary.startswith(f'- Platform Engineer with {years}+ years of experience')
    assert '20+ years' not in '\n'.join(s['text'] for s in result['sections'])
    assert report(result)['experience']['rows'][0]['stated_years']==[years]
