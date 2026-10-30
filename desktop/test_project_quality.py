"""Quality checks protect evidence, edits and bounded work across JD domains."""
import json
import re
import pytest
from pathlib import Path
from desktop.test_generation import FakeRuntime as LegacyRuntime, input_resume
from desktop import project_rules as rules

class ProjectRuntime(LegacyRuntime):
    def chat(self,messages,json_output=False,seed=42):
        task=json.loads(messages[1]["content"].split("\nPrevious response")[0])["task"]
        self.prompts.append(task);self.calls+=1
        if task.startswith('Write this fictional project.'):
            return json.dumps({'platform':'AWS Linux','team_size':'8',
              'description':'The operations platform helps regional teams coordinate customer requests and resolve delayed orders. It provides a shared workspace for validating inventory availability, assigning fulfillment work and tracking delivery exceptions across independently managed business units.',
              'data_flow':'Built order routing with Python workers and durable task queues, validating customer requests against typed schemas before dispatching fulfillment events through idempotent service interfaces.',
              'implementation':'Implemented inventory reconciliation using database transaction boundaries and row locking to prevent duplicate reservations while maintaining auditable stock movement histories across regional fulfillment operations.',
              'integration':'Integrated shipment status feeds through authenticated FastAPI endpoints, mapping carrier identifiers to internal orders and quarantining invalid payloads for reviewed replay without blocking valid updates.'})
        if task.startswith('Complete the SAME fictional project.'):
            return json.dumps({'security':'Configured scoped workload identities using signed service tokens and audited permission checks, separating customer access from operational administration across individual deployment environments and support teams.',
              'evaluation_delivery':'Evaluated request latency using 500 replay cases, reducing the baseline from 500 ms to 300 ms through query optimization before validating Docker health checks and staged rollback procedures.',
              'collaboration':'Coordinated requirements with product owners through Agile acceptance workshops, translating routing exceptions into reviewed scenarios and agreeing operational responsibilities with fulfillment and customer support teams.',
              'ownership':'Documented incident recovery procedures with support engineers, using monitored queue failures to prioritize fixes and rehearsing replay procedures before handing over each release to operations.'})
        if 'professional-summary bullets' in task:
            opening=re.search(r'Begin exactly: (.*?)\. Complete this',task)[1] if 'Begin exactly:' in task else ''
            first=[
                opening+' delivering maintainable business operations services, translating functional requirements into clear implementation boundaries, reliable interfaces and coordinated engineering delivery while supporting controlled releases, technical documentation and practical operational handover across enterprise teams.',
                'Strong expertise in Python and FastAPI, building typed service contracts and asynchronous processing workflows that connect business applications while isolating failures across independently managed components with clear implementation ownership.',
                'Experienced in transactional data handling and integration design, applying idempotent event processing and identifier mappings to reconcile business state across order, inventory and shipment workflows with clear validation boundaries.']
            second=[
                'Skilled in securing operational APIs through scoped workload identities and audited permission boundaries, separating customer-facing access from administrative operations across independently managed environments and services with documented access ownership.',
                'Proficient in automated testing and Docker release delivery, using replayable validation fixtures, staged promotion and documented rollback procedures to support reliable production service changes and consistent operational readiness.',
                'Experienced in technical ownership and operational collaboration, documenting recovery runbooks, diagnosing delivery failures and handing over actionable monitoring procedures to engineering and support teams through practical knowledge transfer.']
            selected=first if 'career_scope' in json_output['properties'] else second
            return json.dumps(dict(zip(json_output['properties'],selected)))
        if 'Use these category names:' in task:
            group=json_output['properties']['categories']['items']['properties']['name']['enum']
            return json.dumps({'categories':[{'name':n,'items':['Python','Asynchronous Programming','Schema Validation','Docker']} for n in group]})
        if '"certifications"' in task:
            titles=json_output['properties']['certifications']['items']['enum']
            return json.dumps({'certifications':titles[:2]})
        if "Plan exactly 3 fictional roles" in task:
            jd=json.loads(messages[1]['content'].split('\nPrevious response')[0])['job_description_data']
            roles=[{"title":"Platform Engineer","employer":e,"project_name":n,"problem":p,"contribution":c,"stack":"Python, Docker, FastAPI","capabilities":"deployment and authenticated services"} for e,n,p,c in [("North Labs","Order Routing","Late order processing","Order workflow automation"),("West Labs","Inventory Ledger","Inconsistent stock balances","Inventory reconciliation"),("South Labs","Delivery Console","Unclear dispatch tracking","Shipment visibility")]]
            if 'Collibra' in jd and 'Genie' in jd:
                for role,(name,contribution,stack) in zip(roles,[('Brand Context Service','Genie configuration and authenticated stateful context serving','Databricks Genie, AWS, Python'),('Metadata Exchange','Collibra metadata synchronization and Unity Catalog administration','Collibra, Unity Catalog, Python'),('Performance Lakehouse','Production lakehouse pipelines and commercial analytics domains','PySpark, Delta Lake, Terraform')]):
                    role.update(project_name=name,contribution=contribution,capabilities=contribution,stack=stack,problem='Brand customer market performance analysis')
            if 'React' in jd and 'Python' in jd:
                for role,(contribution,stack) in zip(roles,[('React application implementation and Python application and database implementation','React, Python, FastAPI, PostgreSQL, pytest, Jest'),('GenAI application integration and AI-assisted development workflow','React, Python, LLM, GitHub Copilot'),('AWS production application ownership and application delivery and collaboration','Python, AWS, GitHub Actions')]):
                    role.update(contribution=contribution,capabilities=contribution,stack=stack)
            return json.dumps({'headline':'Platform Engineer','roles':roles})
        if "Return platform, tools" in task:
            return json.dumps({"platform":"Linux","tools":"Python, Docker, FastAPI","team_size":"6"})
        if '"description":string' in task:
            return json.dumps({"description":"A business operations service routes validated customer orders through authenticated interfaces, giving support teams reliable processing status and actionable exceptions across regional delivery systems."})
        if "Return seven string fields" in task:
            return json.dumps({k:"Implemented Python services with authenticated requests, schema validation and repeatable deployment checks for regional operations." for k in json_output["properties"]})
        if '"bullets"' in task or task.startswith('Bullet fields:'):
            # Distinct implementation mechanisms, without fabricated meaningless metrics.
            first=["Built order routing with Python workers and durable task queues, validating customer requests against typed schemas before dispatching fulfillment events through idempotent service interfaces.","Implemented inventory reconciliation using database transaction boundaries and row locking to prevent duplicate reservations while maintaining auditable stock movement histories across regional fulfillment operations.","Integrated shipment status feeds through authenticated FastAPI endpoints, mapping carrier identifiers to internal orders and quarantining invalid payloads for reviewed replay without blocking valid updates."]
            second=["Configured scoped workload identities using signed service tokens and audited permission checks, separating customer access from operational administration across individual deployment environments and support teams.","Evaluated delivery correctness using a held-out dataset of labeled routing cases, comparing expected state transitions with replayed production fixtures before approving staged service promotion.","Automated container releases with Docker health checks, versioned configuration and rollback gates, documenting recovery runbooks and training operators to diagnose failed queue deliveries during service handover."]
            values=second if "access/security" in task or task.startswith('Bullet fields: security') else first
            return json.dumps(dict(zip(json_output['properties'],values)) if task.startswith('Bullet fields:') else {"bullets":values})
        self.calls-=1;self.prompts.pop()
        return super().chat(messages,json_output=json_output,seed=seed)

def test_rules_detect_versions_clouds_units_and_math():
    text="Unity Catalog uses Runtime 8.3 and AWS S3 with Azure Key Vault.\n- Built retrieval using text chunked into 500MB batches.\n- Reduced latency from 100 ms to 80 ms by 40% on 500 test queries."
    warnings=rules.findings(text)
    assert any("11.3" in w for w in warnings)
    assert any("AWS/Azure" in w for w in warnings)
    assert any("chunks" in w for w in warnings)
    assert any("arithmetic" in w for w in warnings)
    assert not any("arithmetic" in w for w in rules.findings(text.replace("40%","20%")))
    assert "8.3" not in rules.normalize(text, "Databricks engineer")
    assert "8.3" in rules.normalize(text,"Required Runtime 8.3")
    assert any('secrets store' in w for w in rules.findings('Persisted embeddings in a Databricks secret store using authenticated writes.'))
    assert any('different metrics' in w for w in rules.findings('Evaluated 10000 test queries; baseline accuracy was 85.2%, and the final result achieved 94.1% precision.'))
    assert 'Terraform Asset Bundles' not in rules.normalize('Deployed Terraform Asset Bundles.','Databricks')
    assert any('Delta table data' in w for w in rules.findings('- Stored state in a Delta table backed by DynamoDB.'))
    assert not any('Delta table data' in w for w in rules.findings('- Configured Delta tables on S3 using DynamoDB for LogStore coordination.'))
    assert '500k records' in rules.normalize('Processed 500k records/bytes.','Data engineering')
    assert '1024 tokens' in rules.normalize('Used chunks of 1024 tokens/characters.','Retrieval')

def test_skills_contain_names_and_not_recruiter_fragments():
    categories=[{'name':'Metadata','items':['Managed Databricks Unity Catalog schema evolution to align','Strong','India']}]
    jd='Required: Python, Terraform, Docker. Location: Pune, India.'
    result=rules.complete_skills(categories,jd)
    text=json.dumps(result)
    assert 'Python' in text and 'Docker' in text and 'Terraform' in text
    assert 'Managed' not in text and 'Strong' not in text and 'India' not in text

def test_databricks_ownership_is_distinct_and_commercial():
    roles=[{'title':'Engineer','employer':str(i),'project_name':n,'problem':'Brand customer market analysis','contribution':n,'stack':stack,'capabilities':n} for i,(n,stack) in enumerate([('Genie configuration and stateful context serving','Genie, AWS'),('Collibra metadata synchronization and Unity Catalog administration','Collibra, Unity Catalog'),('Production lakehouse pipelines and commercial analytics domains','PySpark, Delta Lake')])]
    jd=(Path(__file__).parent/'fixtures/databricks-jd.txt').read_text(encoding='utf-8')
    planned=rules.project_assignments(jd,roles)
    assert len({r['project_name'] for r in planned})==3
    assert any(c['label']=='Genie configuration' for c in planned[0]['assigned_capabilities'])
    assert any(c['label']=='Collibra metadata synchronization' for c in planned[1]['assigned_capabilities'])
    assert all('clinical' not in r['problem'].lower() and 'Azure' not in r['stack'] for r in planned)


def test_evidence_requires_implementation_and_reports_gaps():
    doc={"jd":"Configure Genie and Unity Catalog.","sections":[{"key":"projects","text":"#### Insights\nTools: Genie, Unity Catalog\n- Configured Genie using approved tables and metric views to ground business queries in approved definitions with golden query evaluation and source lineage."}]}
    report=rules.report(doc)
    genie=next(c for c in report["capabilities"] if c["label"]=="Genie configuration")
    assert genie["status"]=="supported" and genie["passages"][0]["project"]=="Insights"
    doc['sections'][0]['text']=doc['sections'][0]['text'].replace('Configured','Configures')
    assert next(c for c in rules.report(doc)['capabilities'] if c['label']=='Genie configuration')['status']=='supported'
    uc=next(c for c in report["capabilities"] if c["label"]=="Unity Catalog administration")
    assert uc["status"]!="supported"
    doc["sections"][0]["text"]="Tools: Genie, Unity Catalog"
    assert all(c["status"]=="missing" for c in rules.report(doc)["capabilities"])

@pytest.mark.parametrize("jd",["Build AWS Terraform infrastructure using EKS and GitHub Actions.","Develop Azure GenAI retrieval using Azure AI Search.","Configure Databricks Genie and Collibra metadata integration with Unity Catalog."])
def test_domain_prompts_and_bounded_generation(input_resume,jd):
    from desktop.project_generation import generate
    runtime=ProjectRuntime()
    result=generate({"resume":str(input_resume),"jd":jd},runtime,lambda *a:None)
    assert result["model_calls"]<=26 and result["quality_repair_calls"]<=2
    assert all(len(p["bullets"])==7 for p in result["projects"])
    assert all("retrieval generates embeddings" not in p for p in runtime.prompts)
    assert "Store bulk documents" not in runtime.prompts[0]
    assert result["planning"]["version"]==rules.VERSION

def test_repair_does_not_retry_or_discard_resume(input_resume):
    from desktop.project_generation import generate
    runtime=ProjectRuntime();original=runtime.chat;failed=[]
    def chat(messages,**kwargs):
        if "improved implementation bullets" in messages[1]["content"]:
            failed.append(1);return "invalid json"
        return original(messages,**kwargs)
    runtime.chat=chat
    result=generate({"resume":str(input_resume),"jd":"Configure Genie and Unity Catalog."},runtime,lambda *a:None)
    assert len(failed)==2 and result["quality_repair_calls"]==2
    assert len(result["projects"])==3
    assert result["repair_calls"]<=3

def test_old_drafts_mask_label_and_keep_edited_text():
    from desktop.project_document import sanitize
    doc={"edition":"projects","jd":"Python services","sections":[{"key":"projects","title":"Relevant Project Experience","text":"### Employer\n#### Edited project\nClient: #confidentail\n- My edited work."},{"key":"skills","text":"Additional Capabilities: Strong, India\nPython: FastAPI"}],"projects":[],"experience_blocks":[]}
    result=sanitize(doc)
    assert "My edited work" in result["sections"][0]["text"]
    assert "Confidential client" in result["sections"][0]["text"]
    assert "Additional Capabilities" not in result["sections"][1]["text"]

@pytest.mark.parametrize('fixture',['databricks-jd.txt','aws-jd.txt','azure-genai-jd.txt'])
def test_repository_jd_fixtures(input_resume,fixture):
    from desktop.project_generation import generate
    jd=(Path(__file__).parent/'fixtures'/fixture).read_text(encoding='utf-8')
    result=generate({'resume':str(input_resume),'jd':jd},ProjectRuntime(),lambda *a:None)
    assert result['model_calls']<=26
    assert len({p['name'] for p in result['projects']})==3
    assert 'Additional Capabilities' not in result['sections'][2]['text']
    assert result['quality']['capabilities']

def test_hard_call_budget():
    from desktop.generation import Writer
    writer=Writer(ProjectRuntime(),'Python',lambda *a:None,project_edition=True)
    writer.calls=27
    with pytest.raises(ValueError,match='budget'):
        writer.ask('test',lambda v:v,'test')
    assert writer.calls==27

def test_html_recalculates_capabilities_after_edit(tmp_path,monkeypatch):
    import desktop.bootstrap as bootstrap
    from desktop.draft import export
    monkeypatch.setattr(bootstrap,'DATA',tmp_path)
    (tmp_path/'artifacts').mkdir()
    doc={'edition':'projects','mode':'demo','jd':'Configure Databricks Genie.','sections':[{'key':'header','title':'Contact','text':'Alex Example'},{'key':'projects','title':'Relevant Project Experience','text':'#### Insights\nClient: Confidential client\n- Configured Genie using approved tables, metric views and approved definitions with golden query validation and source lineage.'}]}
    first=Path(export({'document':doc,'kind':'html','destination':'unused'},lambda *a:None)['artifact']).read_text(encoding='utf-8')
    assert 'supported' in first
    doc['sections'][1]['text']='#### Edited Insights\nClient: Confidential client\nTools: Genie'
    second=Path(export({'document':doc,'kind':'html','destination':'unused'},lambda *a:None)['artifact']).read_text(encoding='utf-8')
    assert 'No implementation passage' in second and '<td>supported</td>' not in second
