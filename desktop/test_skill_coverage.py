"""Exact names, alternatives, edit authority and cross-domain completeness."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from desktop.job_brief import build, assign
from desktop.project_rules import ensure_mandatory_skills, report
from desktop.skill_coverage import present
from desktop.requirement_ledger import alternative_groups, term_present

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.mark.parametrize('generic,specific', [
    ('Testing', 'pytest'), ('SQL', 'SQLAlchemy'), ('containerization', 'Docker'),
    ('Kubernetes', 'Docker'), ('Git', 'Git Rebase'), ('LangChain', 'GitHub Copilot'),
    ('JavaScript', 'Vue.js'), ('Python', 'Python 3'),
])
def test_generic_parent_is_not_a_named_tool(generic, specific):
    assert not present(generic, specific)
    assert not term_present(generic, specific)


def test_experience_and_specific_tools_survive_extraction():
    b = build('Required Skills:\nPython 3 - 5+ years of experience\n'
              'Unit and integration testing using pytest\nLinux, ORM / SQLAlchemy, Vue.js, GraphQL', '', 'Engineer')
    technologies = set(b['technologies'])
    assert {'python 3', 'pytest', 'unit testing', 'integration testing', 'linux',
            'orm', 'sqlalchemy', 'vue.js', 'graphql'} <= technologies
    assert any(r['kind'] == 'qualification' and '5+' in r['text'] for r in b['requirements'])
    assert any(r['kind'] == 'technology' and r.get('experience_requirement_id') for r in b['requirements'])
    assert b['experience']['overall_years'] == 5
    assert 'javascript' not in technologies
    b = build('Required Skills:\nUnit and integration testing using pytest\n'
              'Git including rebase, cherry-pick and merge conflict resolution\n'
              'GitHub Copilot', '', 'Engineer')
    assert not {'unit', 'test', 'cherry-pick', 'github'} & set(b['technologies'])


def test_long_requirements_do_not_turn_prose_fragments_into_skills():
    bad={'clear','concise','persuasive','structured','fine-tuned','cost','quality',
         'bain','bcg','mckinsey','fast-paced','trade-offs','integrity','rationale',
         'timelines','identify','define','audit','patching','establish'}
    for fixture in ('forward-ai','cloud-security'):
        b=build((FIXTURES/(fixture+'-jd.txt')).read_text(encoding='utf-8'),'','Engineer')
        assert not bad.intersection(b['technologies'])
        items={item.casefold() for c in ensure_mandatory_skills([],b,[]) for item in c['items']}
        assert not bad.intersection(items)
    from desktop.evidence_quality import skill_terms
    assert 'acmeflow' in skill_terms('Apache Kafka, acmeflow')


def test_all_named_examples_and_preferences_are_completed_without_calls():
    jd = ('Required Skills:\nPostgreSQL or MySQL, plus Docker and Kubernetes\n'
          'Message queues such as Kafka, RabbitMQ or equivalent\n'
          'Preferred Skills:\nVue.js, GraphQL, SQLAlchemy, TestNovaDB, uvicorn, acmeflow')
    b = build(jd, '', 'Engineer')
    categories = ensure_mandatory_skills([{'name': 'Tests', 'items': ['Testing']}], b, [])
    text = '\n'.join(', '.join(c['items']) for c in categories)
    for tool in ('PostgreSQL', 'MySQL', 'Docker', 'Kubernetes', 'Kafka', 'RabbitMQ',
                 'Vue.js', 'GraphQL', 'SQLAlchemy', 'TestNovaDB', 'uvicorn', 'acmeflow'):
        assert present(text, tool), tool
    assert ensure_mandatory_skills(categories, b, []) == categories
    assert alternative_groups('PostgreSQL or MySQL, plus Docker and Kubernetes',
                              ['postgresql','mysql','docker','kubernetes']) == [['postgresql','mysql']]
    assert alternative_groups('PostgreSQL or MySQL; Kafka or RabbitMQ',
                              ['postgresql','mysql','kafka','rabbitmq']) == [['postgresql','mysql'],['kafka','rabbitmq']]
    assert alternative_groups('Unit testing using pytest or Jest, plus Docker',
                              ['unit testing','pytest','jest','docker']) == [['pytest','jest']]
    assert not any(t in b['technologies'] for t in ('equivalent','equivalent.','preferred'))


def test_edited_presence_is_not_implementation_and_is_never_repaired_by_report():
    jd = 'Required Skills:\nUnit testing using pytest\nDocker\nPreferred Skills:\nSQLAlchemy'
    b = build(jd, '', 'Engineer')
    doc = {'jd': jd, 'job_brief': b, 'sections': [
        {'key': 'skills', 'text': '**Testing:** Unit Testing, pytest\n**Containers:** Docker\n**Databases:** SQLAlchemy'},
        {'key': 'projects', 'text': '#### Platform\n- Designed service health checks using Kubernetes manifests with readiness probes and controlled rollback gates.'}]}
    before = doc['sections'][0]['text']
    r = report(doc)
    assert not r['skills_review']
    assert not any(c['status']=='supported' and 'pytest' in c['label'] for c in r['capabilities'])
    assert doc['sections'][0]['text'] == before
    doc['sections'][0]['text'] = '**Testing:** Testing\n**Containers:** Kubernetes\n**Databases:** SQL'
    r = report(doc)
    assert {'pytest', 'docker', 'sqlalchemy'} <= set(r['skills_review'])
    assert doc['sections'][0]['text'].endswith('SQL')


def test_git_and_testing_have_owned_responsibility_slots():
    b = build('Required Skills:\nGit rebase, cherry-pick, merge conflict resolution\n'
              'Unit and integration testing using pytest\nSQLAlchemy\nDocker\nLinux', '', 'Engineer')
    roles = [dict(project_name=f'Project {i}',problem='Backend service', contribution='Delivery',
                  stack='Python', capabilities='Backend implementation', requirement_ids=[]) for i in range(3)]
    assign(b, roles)
    slots = '\n'.join(v for role in roles for values in role['evidence_slots'].values() for v in values)
    for phrase in ('Git rebase', 'Git cherry-pick', 'merge conflict resolution', 'pytest fixtures',
                   'integration tests', 'SQLAlchemy ORM', 'Docker image', 'Linux service'):
        assert phrase in slots
    from desktop.job_brief import scope_text
    all_scopes='\n'.join(scope_text(b,role) for role in roles)
    assert 'integration: pytest fixtures' in all_scopes
    assert 'collaboration: Git rebase' in all_scopes
    assert 'ownership: Linux service' in all_scopes


@pytest.mark.parametrize('path', sorted(FIXTURES.glob('*-jd.txt')), ids=lambda p:p.stem)
def test_every_fixture_retains_every_named_skill_in_correctly_completed_table(path):
    jd = path.read_text(encoding='utf-8')
    b = build(jd, '', 'Engineer')
    categories = ensure_mandatory_skills([], b, [])
    text = '\n'.join('**'+c['name']+':** '+', '.join(c['items']) for c in categories)
    doc = {'jd': jd, 'job_brief': b, 'sections': [{'key': 'skills', 'text': text}]}
    assert not report(doc)['skills_review']
    assert all(present(text, term) for term in b['technologies'])
    assert '1.4 LPM' not in text and 'Timezone' not in text
    assert sum('Git' == item for c in categories for item in c['items']) <= 1


def test_no_local_category_or_item_slice_drops_dense_requirements():
    names = ['FutureTool'+str(i) for i in range(40)]
    b = build('Required Skills:\n'+', '.join(names), '', 'Engineer')
    categories = ensure_mandatory_skills([], b, [])
    text = ' '.join(item for c in categories for item in c['items'])
    assert all(present(text, name) for name in names)
    from desktop.evidence_quality import skill_terms
    assert 'acmeflow' in skill_terms('Experience with acmeflow')
    assert 'equivalent.' not in skill_terms('pytest, Jest, or equivalent.')


def test_compiled_legacy_patterns_have_exactly_the_existing_boundaries():
    import re
    from matching import normalizer
    for surface in normalizer._MAP:
        old = re.compile(rf'(?<![\w+#]){re.escape(surface)}(?![\w+#])')
        cached = normalizer._surface_pattern(surface)
        assert cached.pattern == old.pattern
        for text in (surface, 'x'+surface+'x', '#'+surface, surface+'+', ' '+surface+' '):
            assert bool(old.search(text)) == bool(cached.search(text))


def test_identical_prompt_token_counts_are_bounded_and_session_scoped():
    from desktop.runtime import Runtime
    class Response:
        def __init__(self, value):self.value=value
        def raise_for_status(self):pass
        def json(self):return self.value
    class Client:
        def __init__(self):self.calls=[]
        def post(self,path,**kwargs):
            self.calls.append(path)
            return Response({'prompt':'rendered'} if path=='/apply-template' else {'tokens':[1,2,3]})
        def close(self):pass
    runtime=Runtime();runtime.client=Client();client=runtime.client
    messages=[{'role':'user','content':'A full rendered request'}]
    assert runtime.token_count(messages)==3
    assert runtime.token_count(messages)==3 and len(client.calls)==2
    for i in range(130):runtime.token_count([{'role':'user','content':str(i)}])
    assert len(runtime._token_counts)==128
    runtime.stop()
    assert not runtime._token_counts


def test_python_framework_evidence_avoids_false_summary_retries():
    from desktop.project_profile import summary_issues
    bullet='Uses Python and API integration to deliver reliable application services with reviewed interfaces and tested failure handling for customer workflows.'
    project={'name':'Order Gateway','role':'Backend Engineer','tools':'FastAPI',
             'bullets':['Implemented a FastAPI gateway that forwards authenticated API requests to downstream services using scoped access controls.'],
             'description':'A gateway manages access to customer services.'}
    issues=summary_issues([bullet],[project],'Backend Engineer',8,career_text='\n'.join(project['bullets']))
    assert not any('evidence: python' in warning or 'evidence: api integration' in warning for warning in issues)
    project['bullets']=['Developed a Rust worker that streams records through a durable queue and stores validated results in a database.']
    issues=summary_issues([bullet],[project],'Backend Engineer',8,career_text='\n'.join(project['bullets']))
    assert any('evidence: python' in warning for warning in issues)
