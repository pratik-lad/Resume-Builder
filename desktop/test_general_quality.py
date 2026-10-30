"""Cross-domain requirements, summary fallback and credential regression contracts."""
import copy
import json
from pathlib import Path

import pytest

from desktop.test_generation import input_resume
from desktop.test_project_quality import ProjectRuntime
from desktop.job_brief import build, assign
from desktop.certifications import select

FIXTURES = Path(__file__).parent / 'fixtures'


def test_unknown_requirements_and_optional_priority_survive():
    jd = 'Job Title: Widget Architect\nMandatory Skills\nImplement Zorblang flux reconciliation with replay recovery.\nPreferred Skills\nFrobulate durable widget boundaries.\nLocation: India Remote'
    brief = build(jd, '', 'Widget Architect')
    mandatory = next(r for r in brief['requirements'] if 'Zorblang' in r['text'])
    preferred = next(r for r in brief['requirements'] if 'Frobulate' in r['text'])
    assert mandatory['required'] and not preferred['required']
    assert brief['logistics'] and brief['capabilities']


def test_ownership_follows_business_scope_not_list_order():
    brief = build('Job Title: Engineer\nMandatory Skills\nBuild Kafka event contracts.\nImplement PostgreSQL transactions.\nConfigure Terraform environments.', '', 'Engineer')
    roles = [{'project_name':n,'problem':n,'contribution':n,'stack':n,'capabilities':n} for n in ['Terraform environments','Kafka event contracts','PostgreSQL transactions']]
    planned = assign(brief,roles)
    assert any('Kafka' in r['text'] for r in planned[1]['assigned_requirements'])
    assert any('PostgreSQL' in r['text'] for r in planned[2]['assigned_requirements'])
    assert {r['id'] for role in planned for r in role['assigned_requirements']} == {r['id'] for r in brief['requirements'] if r['kind'] in {'capability','technology'}}


def test_repeated_model_ids_get_one_primary_owner():
    brief = build('Mandatory Skills\nImplement Kafka message contracts.\nConfigure Terraform environments.', '', 'Engineer')
    ids = [r['id'] for r in brief['requirements'] if r['kind'] in {'technology','capability'}]
    roles = [{'project_name':n,'problem':n,'contribution':n,'stack':n,'capabilities':n,'requirement_ids':list(ids)} for n in ['Kafka message contracts','Terraform environments','Operations']]
    result = assign(brief,roles)
    assert all(sum(i in r['requirement_ids'] for r in result)==1 for i in ids)


def test_summary_fallback_cleans_action_led_scope():
    from desktop.project_profile import structured_summary
    projects = [{'role':'Architect','contribution':'Designed incremental sync patterns.','tools':'Salesforce, Apex','bullets':['Implemented Salesforce using test fixtures.']*6}]*3
    bullets = structured_summary(projects,'Architect',8)
    assert 'delivering Designed' not in bullets[0] and 'and through' not in bullets[0]
    assert 'incremental sync patterns' in bullets[0]
    projects[0] = {**projects[0], 'contribution':'Architected CPQ engine with real-time pricing.', 'tools':'Salesforce, Apex Security, Unexplained DevTools'}
    bullets = structured_summary(projects,'Architect',8)
    assert 'delivering architected' not in bullets[0]
    assert 'Unexplained DevTools' not in ' '.join(bullets)
    projects[0]['contribution'] = 'Designed and delivered commerce workflows.'
    assert 'delivering commerce workflows' in structured_summary(projects,'Architect',8)[0]
    projects[0]['contribution'] = 'Implemented Angular reactive forms to reduce validation errors by 40%'
    bullets = structured_summary(projects,'Architect',8)
    assert all('%' not in b for b in bullets)
    assert 'Angular reactive forms' in bullets[0] and 'angular reactive forms' not in bullets[0]
    projects[0]['contribution']='Optimized SQL queries and implemented PostgreSQL transactions.'
    assert 'SQL queries and PostgreSQL transactions' in structured_summary(projects,'Architect',8)[0]


def test_salesforce_credentials_required_first_and_not_empty():
    jd = (FIXTURES/'salesforce-jd.txt').read_text()
    result = select(jd,42)
    names = [r['title'] for r in result['selected']]
    assert 2 <= len(names) <= 4
    assert names[:2] == ['Salesforce Certified Application Architect','Salesforce Certified System Architect'] or names[:2] == ['Salesforce Certified System Architect','Salesforce Certified Application Architect']
    assert all('Salesforce' in n for n in names)
    assert all(r['url'].startswith('https://') for r in result['selected'])
    assert select(jd,42) == result


def test_catalogue_shortfall_retired_and_unknown_credentials():
    result = select('Technical writer\nRequired Certifications\nUnlisted Galactic Writing Credential',1)
    assert not result['selected'] and result['warnings']
    assert all(c['status']=='active' for c in select('Azure GenAI Engineer',1)['selected'])
    historical = select('Azure Engineer\nRequired Certifications\nMicrosoft Certified: Azure AI Engineer Associate (AI-102)',1)
    assert any(c['status']=='retired' for c in historical['selected'])
    assert any('retired' in w for w in historical['warnings'])


@pytest.mark.parametrize('fixture',['salesforce','full-stack','java','databricks','aws','azure-genai','qa','backend-completeness'])
def test_general_pipeline_contract(input_resume,fixture):
    from desktop.project_generation import generate
    jd = (FIXTURES/(fixture+'-jd.txt')).read_text(encoding='utf-8')
    runtime = ProjectRuntime()
    doc = generate({'resume':str(input_resume),'jd':jd},runtime,lambda *args:None)
    assert doc['model_calls'] <= 27 and doc['quality_repair_calls'] <= 2
    from desktop.job_brief import VERSION
    assert doc['job_brief']['version'] == VERSION
    assert len({p['name'] for p in doc['projects']}) == 3
    assert all(len(p['bullets'])==7 for p in doc['projects'])
    sections = {s['key']:s['text'] for s in doc['sections']}
    assert len([l for l in sections['summary'].splitlines() if l.startswith('- ')]) == 6
    assert '**' in sections['skills'] and 'Role:' in sections['projects']
    assert sections['projects'].count('### Company Name: #Confidential') == 3
    assert '\nCompany Name: #Confidential' not in sections['projects']
    assert '2021' not in sections['education']
    assert len(doc['certification_selection']['selected']) >= 1
    assert sections.get('certifications')
    assert not any('"certifications":[' in t for t in runtime.prompts)
    assert doc['profile_metadata']['summary_methods']
    assert all(p['tools']==r['stack'] for p,r in zip(doc['projects'],doc['roles']))
    if fixture=='java':
        assert not any('Include only the assigned AI coding tool' in t for t in runtime.prompts)
    if fixture in {'salesforce','java','qa'}:
        writing = [t for t in runtime.prompts if t.startswith('Bullet fields:')]
        assert not any('React REST request -> Python' in t or 'held-out retrieval dataset' in t for t in writing)


def test_bad_summary_uses_grammatical_fallback_with_no_extra_calls():
    from desktop.generation import Writer
    from desktop.project_profile import make_summary
    runtime = ProjectRuntime()
    runtime.chat = lambda *args,**kwargs: '{}'
    writer = Writer(runtime,'Salesforce Architect',lambda *args:None,project_edition=True)
    projects = [{'name':str(i),'role':'Architect','contribution':c,'tools':'Salesforce, Apex, LWC',
                 'bullets':['Implemented business workflows using Salesforce with authorization, test fixtures and release rollback.']*6}
                for i,c in enumerate(['commerce solution design','ERP integration','platform release engineering'])]
    bullets,warnings = make_summary(writer,projects,'Salesforce Architect',8)
    assert len(bullets) == 6 and writer.calls <= 4
    assert writer.profile_metadata['fallback_used']
    assert all('Python' not in b and 'React' not in b for b in bullets)
    assert not any('in designed' in b for b in bullets)
    assert warnings


def test_project_schemas_remain_structural_without_padding_to_character_caps():
    from desktop.project_generation import object_schema
    assert object_schema(['architecture'])['properties']['architecture'] == {'type':'string'}
    assert object_schema(['implementation'])['additionalProperties'] is False
    from desktop.generation import Writer
    runtime = ProjectRuntime()
    calls = []
    def chat(messages, **kwargs):
        calls.append(kwargs['json_output'])
        return '{"description":"A complete project description describing a specific business problem and its application deliverable for customer-facing teams."}'
    runtime.chat = chat
    writer = Writer(runtime, 'Engineer', lambda *a: None, project_edition=True)
    writer.ask('Return description.', lambda value: value, 'project_1_description')
    assert calls[0]['properties']['description'] == {'type':'string'}


def test_overview_context_excludes_detailed_responsibility_instructions(input_resume):
    from desktop.project_generation import generate
    class CaptureRuntime(ProjectRuntime):
        def __init__(self):
            super().__init__(); self.overviews = []
        def chat(self, messages, **kwargs):
            payload = json.loads(messages[1]['content'].split('\nPrevious response')[0])
            if payload['task'].startswith('Write this fictional project.'):
                self.overviews.append(payload)
            return super().chat(messages, **kwargs)
    runtime = CaptureRuntime()
    generate({'resume': str(input_resume), 'jd': (FIXTURES/'full-stack-jd.txt').read_text()}, runtime, lambda *a: None)
    assert len(runtime.overviews) == 3
    for payload in runtime.overviews:
        assert '40-65 word business overview' in payload['task']
        assert 'WHOLE response under 220 words' in payload['task']
        assert 'Project contract:' in payload['task']


def test_certification_report_recalculates_edits():
    from desktop.project_rules import report
    jd = (FIXTURES/'salesforce-jd.txt').read_text()
    doc = {'jd':jd,'generation_seed':42,'sections':[{'key':'certifications','text':'- Salesforce Certified Application Architect\n- Salesforce Certified System Architect'}]}
    original = copy.deepcopy(doc)
    first = report(doc)['certifications']
    assert all(c['present'] for c in first['rows'] if c['priority']=='required')
    doc['sections'][0]['text'] = 'Edited custom credential'
    assert any('missing from edited' in w for w in report(doc)['certifications']['warnings'])
    assert original['sections'][0]['text'].startswith('- Salesforce')
    assert doc['sections'][0]['text'] == 'Edited custom credential'


def test_official_certificate_prefixes_are_not_duplicate_responsibilities():
    from desktop.project_rules import findings
    text = '- Salesforce Certified Application Architect\n- Salesforce Certified System Architect\n- Salesforce Certified Technical Architect'
    assert not any('duplicate' in w for w in findings(text))
