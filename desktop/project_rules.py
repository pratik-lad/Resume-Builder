"""Offline, versioned quality rules. Evidence is textual, never an ATS prediction."""
from __future__ import annotations
import re
import copy
from desktop.evidence_quality import text_similarity
from functools import lru_cache
from html import escape
from matching import normalizer, technology_catalog

VERSION = "projects-quality-13"
SOURCES = [{"rule": "Unity Catalog cluster runtime", "reviewed": "2026-10-16",
            "url": "https://docs.databricks.com/aws/en/data-governance/unity-catalog/requirements"},
           {"rule":"Neptune vector indexing requires an explicit engine/index design","reviewed":"2026-10-16",
            "url":"https://docs.aws.amazon.com/neptune-analytics/latest/userguide/vector-similarity.html"},
           {"rule":"Delta object storage and DynamoDB log coordination are distinct","reviewed":"2026-10-24",
            "url":"https://docs.delta.io/delta-storage/"},
           {"rule":"Databricks service-principal OAuth authentication","reviewed":"2026-10-24",
            "url":"https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m"},
           {"rule":"AWS KMS manages encryption keys; Secrets Manager holds application credentials","reviewed":"2026-10-24",
            "url":"https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html"},
           {"rule":"ECS persistent storage requires an explicit data store or volume","reviewed":"2026-10-24",
            "url":"https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_data_volumes.html"},
           {"rule":"Kyverno policy and Kubernetes admission boundaries","reviewed":"2026-10-29",
            "url":"https://kyverno.io/docs/introduction/"},
           {"rule":"Cilium and Istio require explicit policy and traffic boundaries","reviewed":"2026-10-29",
            "url":"https://docs.cilium.io/en/stable/network/servicemesh/istio/"},
           {"rule":"SAST analyzes code; distinguish container package scanning","reviewed":"2026-10-29",
            "url":"https://community.owasp.org/Source_Code_Analysis_Tools"}]
GUIDANCE = """Use the JD's primary platform; do not add another cloud without an explicit integration boundary and purpose.
Omit runtime version numbers unless required by the JD. Secrets stores hold credentials, not bulk data or running APIs.
Store only keys and credentials in secret stores. Describe a concrete mechanism, owned implementation and business deliverable per bullet.
Use only the mechanisms assigned to the individual project scope; other projects own other responsibilities.
Choose one explicit unit per quantity: a record count, a byte volume, a duration, or a request rate. Never write alternative units separated by a slash.
For every numeric improvement state metric, evaluation workload/population, baseline and final result; keep arithmetic consistent.
Use fictional, plausible outcomes freely, but do not confuse throughput, availability and accuracy.
Optional technologies belong only where an implementation actually uses them. Do not repeat a project in different words.
"""
# Trigger, capability label, independently checkable implementation facets.
DATABRICKS = [
    ("genie", "Genie configuration", ["metric views|metric view", "certified|approved tables", "KPI|business rules|approved definitions", "benchmark|labeled|labelled|golden|held.out", "citation|lineage|reproduc"]),
    ("collibra", "Collibra metadata synchronization", ["catalog|schema|table|column", "glossary|steward|business term", "mapping|mapped|identifier", "incremental|watermark|cursor|changed", "retry|retries|backoff", "conflict|authoritative|source.of.truth", "from Unity Catalog|Unity Catalog to Collibra", "from Collibra|Collibra to Unity Catalog"]),
    ("unity catalog", "Unity Catalog administration", ["catalog", "schema", "table", "storage credential", "external location", "lineage", "row filter|row.level", "column mask|column.level|masking"]),
    ("brand", "Commercial analytics domains", ["brand", "customer", "activity|activities", "market", "performance", "KPI|metric definition"]),
    ("stateful", "Authenticated stateful context serving", ["session|state", "Redis|DynamoDB|PostgreSQL|Delta table|database", "OAuth|JWT|IAM|authentication|authenticated", "API", "Databricks", "AWS|S3|Neptune|Bedrock"]),
    ("asset bundles|terraform", "Reusable deployment and handover", ["Terraform|Asset Bundle", "environment|promotion|rollback", "runbook", "documentation|documented|configuration guide", "mapping"]),
    ("pyspark|spark sql", "Production lakehouse pipelines", ["PySpark|Spark SQL", "Delta", "schema evolution", "partition|Z.order", "Bronze|Silver|Gold|medallion"]),
    ("rdf|owl|skos", "Ontology integration", ["RDF|OWL|SKOS", "mapping|mapped|triples|taxonomy|ontology", "Neptune|graph"]),
    ("bedrock knowledge bases", "Bedrock context integration", ["Bedrock", "sync|ingest|retrieve|retrieval", "S3|citation|permissions"]),
    ("mlflow", "MLflow model lifecycle", ["MLflow", "embedding|entity.resolution", "evaluation|tracking|registry|version"]),
]

EXTRA_TECH = {
    'amazon bedrock knowledge bases':'Amazon Bedrock Knowledge Bases',
    'amazon neptune':'Amazon Neptune', 'aws s3 tables':'Amazon S3 Tables',
    'aws services s3':'Amazon S3', 'databricks vector search':'Databricks Vector Search',
    'databricks asset bundles':'Databricks Asset Bundles', 'pyspark':'PySpark',
    'etl':'ETL', 'iam roles':'IAM Roles', 'kpi':'KPI Definitions', 'llm':'LLM',
    'rdf':'RDF', 'owl':'OWL', 'skos':'SKOS', 'spark sql':'Spark SQL', 'z-ordering':'Z-ordering',
}


def is_full_stack(jd):
    return bool(re.search(r'(?i)full[\s-]*stack', jd) and re.search(r'(?i)\bReact(?:\.js)?\b',jd) and re.search(r'(?i)\bPython\b',jd))


def full_stack_capabilities(jd):
    if not is_full_stack(jd):
        return []
    specs = [
        ('React application implementation', [r'React',r'component',r'state|hook|form',r'API|fetch|request',r'loading|error|retry|validation']),
        ('Python application and database implementation', [r'Python',r'FastAPI|Django|Flask',r'REST|endpoint|API',r'PostgreSQL|SQL',r'transaction|query|schema|index',r'validat|authoriz|permission']),
        ('Frontend and backend unit tests', [r'pytest',r'Jest|React Testing Library',r'fixture|mock|assert|test case|test cases',r'component|endpoint|service|handler']),
    ]
    if re.search(r'(?i)LLM|GenAI|generative AI',jd):
        specs.append(('GenAI application integration', [r'React',r'Python',r'LLM|language model|GenAI',r'API|endpoint',r'evaluat|benchmark|test',r'error|timeout|retry|failure']))
    if re.search(r'(?i)\bRAG\b|retrieval',jd):
        specs.append(('Permission-aware retrieval', [r'retriev|RAG',r'filter|permission|access',r'citation|source|ground',r'evaluat|benchmark|labeled|labelled|test quer']))
    if re.search(r'(?i)Copilot|Cursor|ChatGPT|AI.assisted|AI coding|vibe coding',jd):
        specs.append(('AI-assisted development workflow', [r'GitHub Copilot|Cursor|ChatGPT',r'scaffold|generat|suggest|iterat',r'review',r'test',r'secur|validat']))
    if re.search(r'(?i)\bAWS\b',jd):
        specs.append(('AWS production application ownership', [r'AWS|ECS|Lambda|EC2',r'deploy|release',r'monitor|CloudWatch|alert',r'incident|troubleshoot|diagnos',r'rollback|recovery|recover']))
    specs.append(('Application delivery and collaboration', [r'Git|CI/CD|GitHub Actions|Jenkins',r'Agile|sprint|cross.functional',r'release|deploy',r'runbook|handover|review']))
    return [{'label':label,'facets':facets,'required':not(label=='AWS production application ownership' and bool(re.search(r'(?i)AWS[^\n]*(?:preferred|optional)',jd)))} for label,facets in specs]

def classify(jd):
    # Classification is invariant within a generation. Reports/repairs reuse it
    # without repeatedly parsing the same long JD, while callers get owned data.
    return copy.deepcopy(_classify(jd))


@lru_cache(maxsize=32)
def _classify(jd):
    from desktop.draft import requirements
    result = []
    optional_lines=[];optional=False
    for line in jd.splitlines():
        if re.match(r'(?i)^\s*(?:Preferred|Nice.to.Have|Optional)\b',line):optional=True
        elif re.match(r'(?i)^\s*(?:Required|Mandatory|Key Responsibilities|About the Role)\b',line):optional=False
        elif optional:optional_lines.append(line)
    comparable=lambda s:re.sub(r'\W+',' ',s.casefold()).strip()
    optional_text=comparable(' '.join(optional_lines))
    for r in requirements(jd).requirements:
        text = r.text
        if re.search(r"(?i)^(?:location|notice|payroll|engagement|salary|onsite|offshore|work timings|project duration)|delivery center|Pune,? India|\bIST\b|shift|remote", text):
            kind = "logistics"
        elif re.search(r"(?i)degree|bachelor|certif|credential|\b(?:years?|yrs?)\b", text):
            kind = "qualification"
        else:
            kind = "capability" if re.search(r"(?i)\b(build|configure|integrat|administ|design|deploy|automat|implement|maintain|security|monitor|govern)", text) else "technology"
        is_optional=bool(optional_text and comparable(text) in optional_text) or bool(re.search(r'(?i)AWS[^\n]*preferred',text))
        result.append({"id": r.req_id, "text": text, "kind": kind, "required": r.must_have and not is_optional,
                       "terms": sorted(normalizer.technology_terms_in_text(text))})
    # The shared extractor drops one-word lines such as "Docker". Recruiter
    # skill lists still count, with their explicit mandatory/preferred heading.
    for line in jd.splitlines():
        text=line.strip(' \t-*')
        if re.match(r'(?i)^(?:Location|Work Timings|Shift|Notice(?: period)?|Project Duration|Availability)\s*:',text) and not any(comparable(text)==comparable(r['text']) for r in result):
            result.append({'id':f"M{len(result)+1:02}",'text':text,'kind':'logistics','required':True,'terms':[]})
    optional=False
    for line in jd.splitlines():
        if re.match(r'(?i)^\s*(?:Preferred|Nice.to.Have|Optional)\b',line):
            optional=True;continue
        if re.match(r'(?i)^\s*(?:Required|Mandatory|Key Responsibilities|About the Role)\b',line):
            optional=False;continue
        text=line.strip(' \t-*•')
        terms=sorted(normalizer.technology_terms_in_text(text))
        if (not terms or len(text.split())>30 or re.search(r'(?i)certif|\byears\b|^location|^payroll|^notice',text)):
            continue
        if any(comparable(text) in comparable(row['text']) for row in result):
            continue
        result.append({'id':f"L{len(result)+1:02}",'text':text,'kind':'technology','required':not optional and not bool(re.search(r'(?i)AWS[^\n]*preferred',text)),'terms':terms})
    from desktop.job_brief import extra_requirements
    return extra_requirements(jd,result)

def capabilities(jd):
    result = full_stack_capabilities(jd)
    if re.search("databricks|unity catalog|genie|collibra", jd, re.I):
        for trigger, label, facets in DATABRICKS:
            if re.search(trigger, jd, re.I):
                optional = label in {"Ontology integration", "Bedrock context integration", "MLflow model lifecycle"}
                result.append({"label": label, "facets": facets, "required": not optional})
    for item in classify(jd):
        if item["kind"] not in {"capability", "technology"}:
            continue
        terms = item["terms"]
        if terms:
            from desktop.requirement_ledger import alternatives
            facets = [r'(?<!\w)' + re.escape(t) + r'(?!\w)' for t in terms]
            if alternatives(item['text']): facets = ['|'.join(facets)]
        else:
            from desktop.job_brief import words
            anchors = sorted(words(item['text']))
            facets = [re.escape(t) for t in anchors[:4]]
        if facets:
            result.append({"label": item["text"], "facets": facets, "required": item["required"], 'requirement_id':item['id']})
    return result

def clean_skills(categories):
    result = []
    for c in categories:
        if c["name"].casefold() == "additional capabilities":
            continue
        items = [v for v in c["items"] if not re.fullmatch(r"(?i)strong|good|average|very good|India|Pune|immediate joiner", v)]
        # Generation-only cleanup; exports preserve edited skill text.
        items = ['LLM API Integration' if re.search(r'(?i)LLM.powered authentication(?: and authorization)?(?: flows)?',v) else v for v in items]
        if items:
            result.append({"name": c["name"], "items": items})
    return result

def technical_terms(jd):
    """Named required technologies; exclude raw comma fragments and logistics."""
    terms=set()
    for item in classify(jd):
        if item['required'] and item['kind'] in {'technology','capability'}:
            terms.update(EXTRA_TECH.get(t,t) for t in item['terms'] if technology_catalog.entry_for(t) or t in EXTRA_TECH)
            for key in ['databricks asset bundles','pyspark','rdf','owl','skos']:
                if re.search(r'(?i)(?<!\w)'+re.escape(key)+r'(?!\w)',item['text']):terms.add(EXTRA_TECH[key])
    return sorted(terms)

def complete_skills(categories,jd,preserve_concepts=False):
    grouped={};seen=set()
    def add(term,category='Platforms and Tools'):
        entry=technology_catalog.entry_for(term)
        name=EXTRA_TECH.get(term.casefold(),entry['name'] if entry else term)
        identity=normalizer.canonical(name).casefold()
        if identity in seen:return
        seen.add(identity)
        if preserve_concepts:
            from desktop.evidence_quality import skill_category
            label=skill_category(name,category)
        else:
            label=entry.get('category',category) if entry else category
        grouped.setdefault(label,[]).append(name)
    for category in clean_skills(categories):
        for value in category['items']:
            if preserve_concepts:
                # Writing calls are scoped to JD/project evidence. Keep short
                # concepts such as async/await and schema evolution intact.
                if (len(value.split())<=8 and not re.search(r'(?i)\b(managed|implemented|built|strong|proficiency|experience|hands.on|india|pune|immediate joiner)\b',value)
                        and not re.match(r'(?i)^(?:configured|enforced|maintained|defined|automated|integrated|established|developed|delivered|designed|created|owned|tested)\b',value)
                        and not re.fullmatch(r'(?i)good|average|very good',value) and '%' not in value):
                    split=re.fullmatch(r'\s*([A-Za-z][A-Za-z0-9.+-]*)\s*\(([^)]*,[^)]*)\)\s*',value)
                    for item in ([split[1], *[part.strip() for part in split[2].split(',')]] if split else [value]):
                        add(item,category['name'])
                continue
            known=normalizer.technology_terms_in_text(value)
            for term in sorted(known):
                if technology_catalog.entry_for(term) or term in EXTRA_TECH:add(term,category['name'])
            if not known and len(value.split())<=5 and re.search(re.escape(value),jd,re.I) and not re.search(r'(?i)\b(managed|implemented|built|strong|proficiency|experience|hands.on)\b',value):
                add(value,category['name'])
    represented=normalizer.canonical_skills_in_text(' '.join(v for values in grouped.values() for v in values))
    for term in technical_terms(jd):
        if normalizer.canonical(term) in represented:continue
        if preserve_concepts:
            entry=technology_catalog.entry_for(term) or {}
            # Reuse a matching category when possible instead of creating a
            # repeated uncategorized keyword bucket.
            from desktop.evidence_quality import skill_category
            target=skill_category(term,entry.get('category','Core Technologies & Implementation'))
            add(term,target)
        else:add(term)
    return [{'name':name,'items':items} for name,items in grouped.items()]


def ensure_mandatory_skills(categories, brief, projects):
    """Complete every explicitly named JD skill, including preferences/examples."""
    from desktop.evidence_quality import display_term, skill_category
    from desktop.skill_coverage import named_rows, present, pattern
    grouped = {}
    seen = set()

    def add(value, proposed='Core Technologies & Implementation'):
        name = display_term(value.strip())
        if not present(name, value.strip()):
            # Catalogue aliases may also collapse a tool into its parent.
            # Preserve the actual JD spelling rather than fail generation.
            source = '\n'.join(r.get('source_passage',r['text']) for r in brief.get('requirements',[]))
            match = pattern(value.strip()).search(source)
            name = match[0] if match else value.strip()
        if not name or name.casefold() in seen:
            return
        category=skill_category(name,proposed)
        if any(re.search(r'(?i)(?<!\w)'+re.escape(name)+r'(?!\w)',item) and len(item.split())<=6
               for item in grouped.get(category,[])):
            return
        seen.add(name.casefold())
        grouped.setdefault(category, []).append(name)

    for category in categories:
        for value in category['items']:
            if value.casefold() == 'next.js' and not re.search(r'(?i)(?<!\w)Next\.js(?!\w)',
                    ' '.join(r['text'] for r in brief.get('requirements',[]))+'\n'+' '.join(b for p in projects for b in p.get('bullets',[]))):
                continue
            add(value,category['name'])

    project_text = '\n'.join(b for project in projects for b in project.get('bullets', []))
    # Skills-list presence and implementation choice are separate policies:
    # every named option is listed; a genuine OR capability needs one suitable
    # implementation, not an incoherent architecture using every example.
    for row in named_rows(brief):
        for term in row['terms']:
            add(term)

    # A cloud product already described in an implementation bullet should be
    # visible in the main skills table, even when the JD calls it indirectly.
    for term in ('Experience Cloud','AWS','Azure','GCP'):
        if present(project_text,term):
            add(term)
    result = [{'name':name,'items':items} for name,items in grouped.items() if items]
    text = '\n'.join(', '.join(c['items']) for c in result)
    missing = [term for row in named_rows(brief) for term in row['terms'] if not present(text, term)]
    if missing:
        raise ValueError('Explicit skill completion failed: '+', '.join(sorted(set(missing))))
    return result

def normalize(text, jd):
    text=re.sub(r'(?i)scans? for vulnerabilities and linting via GitHub Copilot',
                'runs configured security and lint checks on developer-reviewed Copilot-assisted changes',text)
    # A local cosmetic cleanup, never a silent rewrite of edited document text.
    if re.match(r'(?i)^(?:I|We)\s+',text):
        text=re.sub(r'(?i)^(?:I|We)\s+','',text)
        text=text[:1].upper()+text[1:]
    if not re.search(r"(?i)(?:runtime|DBR)\s*\d", jd):
        text = re.sub(r"(?i)\b((?:Databricks\s+)?Runtime|DBR)\s+(?:version\s+)?\d+(?:\.\d+)*(?:\s*LTS)?", r"\1", text)
    text=re.sub(r'(?i)\bTerraform Asset Bundles\b','Databricks Asset Bundles and Terraform',text)
    # A small model sometimes copies alternative-unit notation from a prompt.
    # Generated fictional claims use the first named unit; edits are never passed
    # through this generation normalizer and remain reviewable in reports.
    text=re.sub(r'(?i)\brecords?\s*/\s*bytes\b','records',text)
    text=re.sub(r'(?i)\btokens?\s*/\s*characters\b','tokens',text)
    return text.replace("#confidentail", "Confidential client")

def findings(text, jd=""):
    issues = []
    for line in text.splitlines():
        for match in re.finditer(r'(?i)\b(?:persist|stor)\w*\s+(?P<data>[^.!?\n]{0,90})\b(?:secret stores?|Secrets Manager|Key Vault)\b',line):
            if re.search(r'(?i)records|transactions|documents|business data|payloads',match['data']) and not re.search(r'(?i)credentials?|secrets?|keys?|tokens?',match['data']):
                issues.append('Store business records in a database or object store; secret stores hold credentials and encryption secrets, not application records.')
        if re.search(r'(?i)PyTest[^.!?\n]{0,70}React Testing Library mocks',line):
            issues.append('Explain separate Python pytest and JavaScript Jest/React Testing Library runners instead of mixing their fixtures and mocks.')
    if re.search(r'(?i)LLM.powered authentication(?: and authorization)?(?: flows)?',text):
        issues.append('Separate LLM application integration from deterministic user authentication and access-control enforcement.')
    if re.search(r'(?i)scans? for vulnerabilities and linting via GitHub Copilot',text):
        issues.append('Name the configured CI lint/security checks separately from Copilot-assisted code generation and developer review.')
    if re.search(r'(?i)KMS keys?[^.!?\n]{0,35}stor\w*\s+in\s+(?:AWS\s+)?Secrets Manager',text):
        issues.append('Distinguish KMS-managed key material from key identifiers and application credentials stored in Secrets Manager.')
    for line in text.splitlines():
        if re.search(r'(?i)ECS container[^.!?\n]{0,30}(?:for|as) persistent storage',line) and not re.search(r'(?i)EFS|EBS|FSx|volume',line):
            issues.append('Name the durable database or attached volume; an ECS container alone does not explain persistent business storage.')
        if re.search(r'(?i)user sessions?[^.!?\n]{0,25}(?:via|using|with) OAuth service principals',line):
            issues.append('Clarify human user sign-in versus service-principal authentication; describe JWT/OIDC validation and application authorization.')
    if re.search(r'(?i)Databricks Service Mesh\s+tokens?',text):
        issues.append('Review authentication naming: use a documented Databricks OAuth service-principal flow or explain the custom service, rather than assuming Service Mesh tokens authorize the API.')
    if re.search(r'(?i)Delta\s+(?:Lake\s+)?table\w*[^.!?\n]{0,25}(?:backed by|stored in|hosted in)\s+DynamoDB',text):
        issues.append('Delta table data belongs in object storage; DynamoDB may store application session state or coordinate a LogStore, not host Delta table data.')
    if re.search(r'(?im)^-\s+(?:I|We|My|Our)\s+',text):
        issues.append('Use action-led professional bullets without first-person pronouns.')
    if re.search(r'(?i)\b\d+\s*[kKmM]?\s+records\s*/\s*bytes\b',text):
        issues.append('Specify an actual ingestion unit: record count or byte volume, not records/bytes.')
    if re.search(r"(?i)(?:persist|stor|sav)\w*[^.!?\n]{0,100}(?:embeddings?|vectors?|documents?|session state)[^.!?\n]{0,70}(?:secret store|secrets store|Key Vault)", text):
        issues.append("Embeddings/documents/session state cannot be persisted in a secrets store; name the actual data/index/state store.")
    if re.search(r"(?i)row.level[^.!?\n]{0,15}masking", text):
        issues.append("Distinguish row filters from column masking instead of describing row-level masking.")
    if re.search(r"(?i)vector (?:store|index)[^.!?\n]{0,60}Neptune(?! Analytics)", text):
        issues.append("Specify the vector index engine: distinguish Neptune Analytics vector indexing from the Neptune graph database.")
    if re.search("Unity Catalog", text, re.I):
        for v in re.findall(r"(?i)(?:runtime|DBR)\s+(\d+(?:\.\d+)?)", text):
            if tuple(int(x) for x in (v.split(".") + ["0"])[:2]) < (11, 3):
                issues.append("Unity Catalog conflicts with a cluster runtime below 11.3 LTS.")
    if re.search(r"\bAWS\b|\bS3\b|\bBedrock\b", text) and re.search(r"ADLS|Azure|Blob Storage|Key Vault", text):
        if not re.search(r"(?i)cross.cloud|multi.cloud|federat|migration|bridge|private connectivity|replicat", text):
            issues.append("Mixed AWS/Azure services need an explained integration boundary.")
    if re.search(r"(?i)chunk\w*[^.\n]{0,45}\d+\s*(?:MB|GB)\b", text):
        issues.append("Separate ingestion byte batches from retrieval token/character chunks.")
    for line in text.splitlines():
        baseline=re.search(r'(?i)\bbaseline\b([^;]{0,110})',line)
        final=re.search(r'(?i)\b(?:final result|final|result)\b([^;]{0,110})',line)
        metric=r'(?i)\b(accuracy|precision|recall|F1|latency|cost|throughput)\b'
        if baseline and final:
            a=re.search(metric,baseline[1]);b=re.search(metric,final[1])
            if a and b and a[1].lower()!=b[1].lower():
                issues.append('Baseline and final result use different metrics: '+line[:160])
        if re.search(r'(?i)\bTerraform Asset Bundles\b',line):
            issues.append('Distinguish Databricks Asset Bundles from Terraform deployment assets.')
        if not re.search(r"\d+(?:\.\d+)?\s*(?:%|percent\b)", line, re.I):
            continue
        if len(re.findall(r"\d+(?:\.\d+)?\s*(?:%|percent\b)",line,re.I))>2 and not re.search(r"(?i)from\s+\d[^.;]{0,40}\bto\s+\d[^.;]{0,60}\bby\s+\d",line):
            issues.append("Multiple percentage claims need separate metric baselines/results or an explicit consistent change calculation: "+line[:160])
        if not (re.search(r"(?i)baseline|from\s+\d", line) and re.search(r"(?i)to\s+\d|result|achiev|final", line) and re.search(r"(?i)dataset|queries|records|requests|cases|workload|benchmark|samples|test", line) and re.search(r"(?i)accuracy|precision|recall|latency|throughput|cost|time|rate|availability|F1|correctness", line)):
            issues.append("Quantified outcome needs its metric, workload, baseline and final result: " + line[:160])
        m = re.search(r"(?i)from\s+(\d+(?:\.\d+)?)\s*(%|percent)?\s*(?:\w+\s+){0,2}to\s+(\d+(?:\.\d+)?)", line)
        change = re.search(r"(?i)(?:by|improvement(?:\s+of)?|reduction(?:\s+of)?)\s+(\d+(?:\.\d+)?)\s*(%|percent(?:age points)?)", line)
        if m and change and float(m[1]):
            expected = abs(float(m[3])-float(m[1]))
            if "points" not in change[2].lower():
                expected = expected / float(m[1]) * 100
            if abs(expected-float(change[1])) > 1:
                issues.append("Baseline/result arithmetic disagrees with the stated improvement: " + line[:160])
    # Qualification names often share a long official prefix. They are not
    # duplicate implementation responsibilities.
    bullets = [v.lstrip("- ").lower() for v in text.splitlines() if v.startswith("- ") and len(v.split()) >= 12]
    for i, b in enumerate(bullets):
        if any(text_similarity(b, prev) >= .80 for prev in bullets[:i]):
            issues.append("Repeated or near-duplicate implementation: " + b[:140])
    from desktop.evidence_quality import content_findings
    return list(dict.fromkeys(issues + content_findings(text,jd)))

def project_assignments(jd, roles):
    """Compatibility entry point for semantic assignment from the shared brief."""
    from desktop.job_brief import build, assign
    return assign(build(jd,'','Professional'),roles)

def facet_display(pattern):
    """Readable prompt/report wording; regex syntax stays inside the checker."""
    from desktop.skill_coverage import SPELLINGS, pattern as spelling_pattern
    specific = next((name for name in SPELLINGS if spelling_pattern(name).pattern == pattern), None)
    if specific:
        return specific
    pattern = pattern.replace(r'(?<![\w+#])(?:', '').replace(r')(?![\w+#])', '')
    return (pattern.replace(r'(?<!\w)','').replace(r'(?!\w)','').replace(r'\b','').replace(r'\.','<literal-dot>')
            .replace('\\','').replace('|',' or ').replace('.',' ').replace('<literal-dot>','.'))


def report(document):
    sections = document.get("sections", [])
    text = "\n".join(s["text"] for s in sections if s["key"] == "projects")
    passages = []
    project = ""
    for line in text.splitlines():
        if line.startswith("#### "):
            project = line[5:]
        if line.startswith("- "):
            passages.append((project, line[2:]))
    items = []
    cap_rows=capabilities(document.get('jd',''))
    if document.get('job_brief'):
        from desktop.requirement_ledger import alternative_groups
        from desktop.skill_coverage import pattern
        cap_rows=[c for c in cap_rows if not c.get('requirement_id')]
        from desktop.job_brief import words
        for row in document['job_brief']['requirements']:
            if row['kind'] not in {'capability','technology'}:continue
            terms=row['terms'];groups=alternative_groups(row['text'],terms)
            options={t for g in groups for t in g}
            facets=[pattern(t).pattern for t in terms if t not in options]
            facets += ['|'.join(pattern(t).pattern for t in group) for group in groups]
            if not facets:facets=[re.escape(t) for t in sorted(words(row['text']))[:4]]
            if facets:cap_rows.append({'label':row['text'],'facets':facets,'required':row['required'],'requirement_id':row['id']})
    for cap in cap_rows:
        hits = []
        for project, line in passages:
            if re.search(r"(?i)\b(using|via|with|through|by|into)\b", line) and re.search(r"(?i)\b(?:built|build|configur|implement|design|integrat|deploy|automat|evaluat|develop|map|secur|document|maintain|optimi[sz]|publish|validat|establish|orchestrat|enforc|wrote|authored|tested|resolved|diagnos|support|triag|refactor|debugg|review|owned|led|conducted|coordinat|collaborat)\w*\b", line):
                matched = [f for f in cap["facets"] if re.search(f, line, re.I)]
                if matched:
                    hits.append({"project": project, "passage": line, "facets": matched})
        covered = {f for h in hits for f in h["facets"]}
        missing = [f for f in cap["facets"] if f not in covered]
        items.append({**cap, "status": "supported" if not missing else "partial" if hits else "missing",
                      "passages": hits, "missing_facets": missing})
    jd=document.get('jd','')
    all_text='\n'.join(s['text'] for s in sections)
    from desktop.quality import contains_skill
    groups={}
    skills_text='\n'.join(s['text'] for s in sections if s['key']=='skills')
    from desktop.skill_coverage import present, terms_by_priority, named_rows
    coverage_brief=document.get('job_brief') or {'requirements':classify(jd)}
    for required,label in ((True,'mandatory'),(False,'preferred')):
        terms=terms_by_priority(coverage_brief,required)
        rows=[{'term':t,'present':present(all_text,t),'in_skills':present(skills_text,t)} for t in terms]
        selected=[c for c in items if c['required']==required]
        supported=sum(c['status']=='supported' for c in selected)
        groups[label]={'keywords':rows,'keyword_count':len(rows),'keyword_present':sum(r['present'] for r in rows),
                       'skills_present':sum(r['in_skills'] for r in rows),
                       'capability_count':len(selected),'supported':supported,
                       'partial':sum(c['status']=='partial' for c in selected),
                       'missing':sum(c['status']=='missing' for c in selected)}
    profile=[]
    if document.get('profile_version'):
        from desktop.project_profile import summary_issues
        summary=next((s['text'] for s in sections if s['key']=='summary'),'')
        bullets=[l[2:] for l in summary.splitlines() if l.startswith('- ')]
        profile=summary_issues(bullets,document.get('projects',[]),
                               next((s['text'].splitlines()[1] for s in sections if s['key']=='header' and len(s['text'].splitlines())>1),''),
                               document.get('experience_years',9), career_text=text)
    names=[line[5:] for line in text.splitlines() if line.startswith('#### ')]
    checks={'distinct_project_titles':len(names)==3 and len(set(n.casefold() for n in names))==3,
            'expected_bullets_per_project':bool(names) and all(sum(p==name for p,_ in passages)==(7 if document.get('template_version') else 6) for name in names),
            'no_additional_capabilities':'additional capabilities' not in all_text.casefold()}
    assessed={c['label'] for c in items}
    unassessed=[row for row in document.get('job_brief',{}).get('requirements',classify(jd)) if row['text'] not in assessed]
    from desktop.project_experience import review_experience
    missing_in_skills=[]
    for row in named_rows(coverage_brief):
        missing_in_skills.extend(t for t in row['terms'] if not present(skills_text,t))
    review_text='\n'.join(s['text'] for s in sections if s['key'] in {'skills','projects'})
    return {"version": VERSION, "capabilities": items, "warnings": findings(review_text, jd),
            'skills_review':list(dict.fromkeys(missing_in_skills)),
            'skill_coverage_version':'explicit-skills-1',
            'experience':review_experience(document),
            'coverage':groups,'profile_warnings':profile,'presentation_checks':checks,
            'profile_generation':document.get('profile_metadata',{}),
            'certifications':credential_review(document),
            'unassessed_requirements':unassessed,
            "sources": SOURCES, "scope": "Heuristic text evidence and known rules; unknown technical combinations require review. Fictional claims are not verified."}

def credential_review(document):
    """Edited section text is authoritative; saved selection metadata is descriptive."""
    text = '\n'.join(s['text'] for s in document.get('sections',[]) if s['key']=='certifications')
    from desktop.certifications import select
    selection = select(document.get('jd',''), document.get('generation_seed',0))
    rows = [{**c, 'present':c['title'].casefold() in text.casefold()} for c in selection['selected']]
    warnings = list(selection['warnings'])
    for c in rows:
        if c['priority']=='required' and not c['present']:
            warnings.append('Required credential missing from edited resume: '+c['title'])
    return {'method':selection['method'],'rows':rows,'warnings':warnings,
            'scope':'Credential names are catalogue-backed; possession is fictional and not verified.'}


def report_html(result):
    rows = []
    for i, item in enumerate(result["capabilities"]):
        evidence = "<br>".join(escape(h["project"] + ": " + h["passage"]) for h in item["passages"])
        priority='Mandatory' if item['required'] else 'Preferred'
        rows.append(f'<tr><td>{priority}</td><td>{escape(item["label"])}</td><td>{item["status"]}</td><td>{evidence or "No implementation passage"}</td><td>{escape(", ".join(facet_display(f) for f in item["missing_facets"]))}</td></tr>')
    sources = ''.join('<li><a href="'+escape(s['url'],quote=True)+'">'+escape(s['rule'])+'</a> (reviewed '+escape(s['reviewed'])+')</li>' for s in result['sources'])
    coverage=[]
    for label,group in result.get('coverage',{}).items():
        keywords=f"{group['keyword_present']}/{group['keyword_count']}" if group['keyword_count'] else 'Not specified'
        missing=', '.join(r['term'] for r in group['keywords'] if not r['present']) or 'None identified'
        coverage.append('<tr><td>'+label.title()+'</td><td>'+keywords+'</td><td>'+str(group.get('skills_present',0))+'/'+str(group['keyword_count'])+'</td><td>'+
                        f"{group['supported']} supported / {group['partial']} partial / {group['missing']} missing"+
                        '</td><td>'+escape(missing)+'</td></tr>')
    checks=''.join('<li>'+escape(k.replace('_',' '))+': '+('Pass' if v else 'Review')+'</li>' for k,v in result.get('presentation_checks',{}).items())
    unassessed=''.join('<li>'+('Mandatory' if r['required'] else 'Preferred')+' / '+escape(r['kind'])+': '+escape(r['text'])+'</li>' for r in result.get('unassessed_requirements',[]))
    experience = result.get('experience')
    experience_html = ''
    if experience:
        experience_html = '<h2>Experience requirements</h2><p>'+escape(experience['scope'])+'</p><table><tr><th>Requirement</th><th>JD minimum</th><th>Stated years</th><th>Status</th><th>Passages</th></tr>'
        for row in experience['rows']:
            experience_html += '<tr><td>'+escape(row['label'])+'</td><td>'+escape(str(row['required_years']) if row['required_years'] is not None else 'Not specified')+'</td><td>'+escape(', '.join(str(n)+'+' for n in row['stated_years']) or 'None')+'</td><td>'+escape(row['status'])+'</td><td>'+escape(' | '.join(row['passages']))+'</td></tr>'
        experience_html += '</table><ul>'+''.join('<li>'+escape(w)+'</li>' for w in experience['warnings'])+'</ul>'
    credentials = result.get('certifications',{})
    credential_html = '<h2>Certification review</h2><p>'+escape(credentials.get('scope',''))+'</p><ul>'
    credential_html += ''.join('<li>'+escape(c['title'])+' ? '+('present' if c['present'] else 'not in edited resume')+' ('+escape(c['priority'])+')</li>' for c in credentials.get('rows',[]))
    credential_html += ''.join('<li>'+escape(w)+'</li>' for w in credentials.get('warnings',[]))+'</ul>'
    metadata = result.get('profile_generation',{})
    credential_html += '<p>Summary generation: '+escape(', '.join(metadata.get('summary_methods',[])) or 'Legacy / edited document')+'.</p>'
    missing_skills=''.join('<li>'+escape(value)+'</li>' for value in result.get('skills_review',[]))
    return (credential_html+experience_html+'<h2>Mandatory and preferred coverage</h2><p>Keyword presence and project implementation evidence are separate. '
            'Counts are local heuristics, not an external ATS score. A 95% target is not a measured guarantee.</p>'
            '<table><tr><th>Priority</th><th>Keyword presence</th><th>Technical Skills presence</th><th>Capability evidence</th><th>Missing keywords</th></tr>'+''.join(coverage)+'</table>'
            '<h2>Named JD terms missing from Technical Skills</h2><p>Includes mandatory, preferred and named example tools; implementation alternatives are evaluated separately.</p><ul>'+missing_skills+'</ul><h2>Capability implementation review</h2><p>' + escape(result["scope"]) + '</p><table><tr><th>Priority</th><th>Capability</th><th>Status</th><th>Evidence passages</th><th>Remaining facets</th></tr>' + ''.join(rows) + '</table><h2>Requirements needing manual review</h2><p>These qualifications, logistics or unmapped requirements are not counted as automatically satisfied.</p><ul>'+unassessed+'</ul><h2>Technical review</h2><ul>' + ''.join('<li>'+escape(w)+'</li>' for w in result["warnings"]) + '</ul><h2>Profile and presentation review</h2><ul>'+checks+''.join('<li>'+escape(w)+'</li>' for w in result.get('profile_warnings',[]))+'</ul><h3>Offline rule references</h3><ul>'+sources+'</ul>')
