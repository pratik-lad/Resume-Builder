"""Local JD hygiene, skill taxonomy and implementation checks; no model calls.

Checks describe fictional text, never certify candidate history or predict an ATS score.
"""
from __future__ import annotations

import re
from functools import lru_cache
from difflib import SequenceMatcher

VERSION = 'evidence-2'


@lru_cache(maxsize=2048)
def text_similarity(first, second):
    """Cache the exact existing comparison; never approximate its threshold."""
    return SequenceMatcher(None, first, second).ratio()

LOGISTICS = re.compile(r'(?i)^(?:timezone|time zone|budget|salary|payroll|compensation|rate|location|notice(?: period)?|engagement|work timings?|working hours?|project duration|availability|shift)\s*[:\-]|\b(?:LPM|LPA|immediate joiner)\b|\b(?:remote|onsite)\s+(?:location|work|availability)\b')
MILESTONE = re.compile(r'(?i)^(?:weeks?|months?|days?)\s+\d+(?:\s*[-–—]\s*\d+)?\s*:\s*')


def strip_milestone(text):
    # Keep the actual responsibility, but never make the employer's onboarding
    # schedule a candidate accomplishment. Original passages remain in the ledger.
    return MILESTONE.sub('', text.strip())


def is_heading(text):
    text = text.strip(' \t-*•:#')
    return bool(re.match(r'(?i)^(?:job title|position|target role|role)\s*:', text) or
                re.fullmatch(r'(?i)(?:required|mandatory|preferred|optional|nice.to.have|must.have|technical|core|essential)(?:\s*\(Bonus\))?(?:\s+(?:skills?|skillsets?|qualifications|requirements))?', text) or
                re.fullmatch(r'(?i)(?:key )?responsibilities|position overview|job overview|about us|thank you', text))


def requirement_kind(text, default):
    if LOGISTICS.search(text) or re.search(r'(?i)\bIST\b|^India\s*[-–]\s*Remote',text):
        return 'logistics'
    if re.search(r'(?i)certif|credential|\bdegree\b|bachelor|master|\b(?:years?|yrs?|YOE)\b|Professional English|\bC1\+|\bstrategy consulting\b', text):
        return 'qualification'
    if re.search(r'(?i)^(?:strong |solid |deep )?(?:understanding|knowledge|familiarity|awareness)\b',text):
        return 'knowledge'
    return default


# Compact terminology gaps in the existing catalogue. Named credentials stay
# in the separate verified catalogue; these are technologies and practices only.
TERMS = {
    'Cilium':r'\bCilium\b', 'Istio':r'\bIstio\b', 'Kyverno':r'\bKyverno\b',
    'OPA':r'\bOPA\b|Open Policy Agent', 'SAST':r'\bSAST\b', 'SCA':r'\bSCA\b',
    'SBOM':r'\bSBOM\b', 'Socket':r'\bSocket\b', 'JFrog':r'\bJFrog\b',
    'VDI':r'\bVDI\b', 'Browser Isolation':r'browser.isolation',
    'Service Mesh':r'service.mesh', 'Policy as Code':r'policy.as.code',
    'Vulnerability Management':r'vulnerability.management', 'Remediation SLAs':r'remediation SLAs?|SLA.driven remediation',
    'Supply Chain Security':r'supply.chain (?:security|scanning)',
    'Service Account Governance':r'service.account governance',
    'SFT':r'\bSFT\b', 'RLHF':r'\bRLHF\b', 'RLAIF':r'\bRLAIF\b',
    'DPO':r'\bDPO\b', 'PPO':r'\bPPO\b', 'Reward Modeling':r'reward model(?:ing|ling)',
    'LoRA':r'\bLoRA\b', 'PEFT':r'\bPEFT\b',
    'Synthetic Data Generation':r'synthetic data(?: generation| workflows?)?',
    'Data Labeling':r'data.label(?:l)?ing', 'AI Evaluation':r'AI (?:data and )?evaluation|evaluation pipelines?',
    'Agentic Workflows':r'agentic (?:systems|workflows)',
    'MVP Prototyping':r'\bMVP\b|iterative prototyp',
    'Coding Agents':r'coding agents?|agentic tool',
    'Experience Cloud':r'\bExperience Cloud\b', 'GitHub Copilot':r'GitHub Copilot',
    'IAM':r'\bIAM\b', 'RBAC':r'\bRBAC\b', 'NumPy':r'\bNumPy\b', 'Pandas':r'\bPandas\b',
}
NON_SKILLS = {'ctos','cto','vps','vps of engineering','vp','c1','lpm','lpa','yoe','mvp','bluf','ci','cd','net'}


@lru_cache(maxsize=512)
def _skill_terms(text):
    from matching import normalizer, technology_catalog
    values = set()
    for term in normalizer.technology_terms_in_text(text):
        if term.casefold() in NON_SKILLS:
            continue
        entry = technology_catalog.entry_for(term)
        if entry:
            surfaces = technology_catalog.surfaces(entry)
            # The broad legacy dictionary maps ordinary "next" to Next.js.
            surfaces = [s for s in surfaces if s.casefold() not in {'next','net'}]
            if not any(re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',text,re.I) for s in surfaces):
                continue
        elif not re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text,re.I):
            continue
        term = re.sub(r'(?i)\s+(?:tooling|tools|concepts|applications|practices)$','',term)
        values.add(term.casefold())
    values.update(name.casefold() for name,pattern in TERMS.items() if re.search(pattern,text,re.I))
    # Preserve unfamiliar acronyms, compound product names and numbered tools.
    for token in re.findall(r'\b[A-Za-z][A-Za-z0-9]*(?:[.-][A-Za-z0-9]+)*\b',text):
        if token.casefold() in NON_SKILLS or re.fullmatch(r'AI|ML|CS|PhD|MSc|US|API|CTO|VP|CTOs|VPs|USD|INR',token):
            continue
        if (re.fullmatch(r'[A-Z]{2,8}',token) or re.search(r'[a-z][A-Z]|[a-zA-Z]\d',token)) and not re.search(r'(?i)^(C1|YOE|LPM|LPA)$',token):
            values.add(token.casefold())
    return tuple(sorted(values))


def skill_terms(text):
    from desktop.skill_coverage import explicit_terms
    return list(explicit_terms(text))


# First match wins: specific tool families precede broad platform families.
CATEGORIES = [
    (r'\bGit\b|GitHub(?! Copilot| Actions)|GitLab(?! CI)|Bitbucket|version control|branch|rebas|cherry.pick|pull request|merge|\bAgile\b', 'Version Control & Collaboration'),
    (r'Copilot|Cursor|ChatGPT|coding agent|AI.assisted|agentic tool|vibe coding', 'AI-Assisted Development'),
    (r'SAST|SCA\b|SBOM|Socket|JFrog|Snyk|Sonar|Trivy|Grype|AppSec|supply.chain|vulnerabil|remediation|secure.SDLC|image scann', 'Application & Supply Chain Security'),
    (r'Cilium|Istio|Kyverno|\bOPA\b|service.mesh|policy.as.code|admission|container security', 'Kubernetes & Policy Enforcement'),
    (r'CloudWatch|CloudTrail|Datadog|Prometheus|Grafana|OpenTelemetry|Splunk|ELK|observab|logging|monitoring|alert', 'Monitoring & Observability'),
    (r'\bIAM\b|RBAC|OAuth|JWT|Key Vault|Secrets Manager|\bKMS\b|VDI|browser.isolation|identity|authentication|authoriz|encrypt|\bsecurity\b|service.account|zero.trust', 'Security & Identity'),
    (r'Salesforce|Apex|LWC|CPQ|Experience Cloud|Sales Cloud|Service Cloud|OmniStudio|\bCRM\b', 'Salesforce Architecture & Business Applications'),
    (r'\bERP\b|\bSAP\b|\bB2B\b|Oracle', 'Business Platforms & Integration'),
    (r'Collibra|Unity Catalog|Genie|semantic|ontology|\bRDF\b|\bOWL\b|\bSKOS\b|metadata|lineage|row filter|column mask', 'Governance, Metadata & Semantic Analytics'),
    (r'LLM|\bSFT\b|RLHF|RLAIF|\bDPO\b|\bPPO\b|LoRA|PEFT|reward model|synthetic data|data.label|AI evaluation|crowdsourc|\bRAG\b|retriev|agentic workflow|GenAI|machine learning|Bedrock|MLflow|vector', 'AI Data, Models & Evaluation'),
    (r'\bMVP\b|prototyp|technical discovery|executive communication|commercial outcome|gross margin|contribution margin', 'Solution Engineering & Delivery'),
    (r'pytest|Jest|JUnit|Selenium|Playwright|Cypress|testing|test |debug|code quality|code review', 'Testing, Debugging & Code Quality'),
    (r'\bLinux\b|\bUnix\b|\bBash\b', 'Linux & Operating Systems'),
    (r'Terraform|CloudFormation|Bicep|Ansible|Helm|Docker|Kubernetes|\bEKS\b|\bAKS\b|\bGKE\b|CI/CD|GitHub Actions|GitLab CI|Jenkins|Argo|infrastructure as code|\bIaC\b|\bDevOps\b', 'Infrastructure, Containers & CI/CD'),
    (r'\bAWS\b|Amazon|\bAzure\b|\bGCP\b|Google Cloud|\bS3\b|\bEC2\b|Lambda|VPC|Cloud Platforms', 'Cloud Platforms'),
    (r'Databricks|Spark|PySpark|Airflow|Beam|Dataflow|Snowflake|ETL|lakehouse|schema evolution|data pipeline|Delta|NumPy|Pandas', 'Data Engineering & Analytics'),
    (r'PostgreSQL|MySQL|\bSQL\b|Mongo|Redis|DynamoDB|database|caching|SQLAlchemy|\bORM\b', 'Databases & Caching'),
    (r'Kafka|RabbitMQ|messag|event.driven|distributed system', 'Messaging & Distributed Systems'),
    (r'React|Vue|Angular|TypeScript|JavaScript|HTML|CSS|frontend|GraphQL', 'Frontend & Web Technologies'),
    (r'Python|FastAPI|Flask|Django|Java|Spring|\bGo\b|C\+\+|\.NET|REST|API|SOAP|async|microservice|backend', 'Programming & Backend Development'),
]

CATEGORY_ALIASES = {
    'Version Control & Delivery':'Version Control & Collaboration',
    'AI, GenAI & Retrieval':'AI Data, Models & Evaluation',
    'Data Engineering & Lakehouse':'Data Engineering & Analytics',
    'Data Engineering & Warehousing':'Data Engineering & Analytics',
}


def canonical_category(name):
    return CATEGORY_ALIASES.get(name,name)


def skill_category(value, proposed='Core Technologies & Implementation'):
    for pattern,name in CATEGORIES:
        if re.search(pattern,value,re.I):
            return name
    return canonical_category(proposed) if proposed not in {'Platforms & Implementation','Cloud & Infrastructure','Tools & Platforms'} else 'Core Technologies & Implementation'


def display_term(term):
    from matching import technology_catalog
    from desktop.skill_coverage import SPELLINGS
    specific = next((name for name in SPELLINGS if name.casefold() == term.casefold()), None)
    if specific:
        return specific
    shorthand={'aws':'AWS','azure':'Azure','gcp':'GCP','llm':'LLM','genai':'GenAI','api':'API',
               'api integration':'API Integration','ci/cd':'CI/CD','chatgpt':'ChatGPT','cpq':'CPQ',
               'crm':'CRM','erp':'ERP','soap':'SOAP','b2b':'B2B','testing':'Testing',
               'gross margin':'Gross Margin','contribution margin':'Contribution Margin'}
    if term.casefold() in shorthand:
        return shorthand[term.casefold()]
    explicit = next((k for k in TERMS if k.casefold()==term.casefold()),None)
    entry = technology_catalog.entry_for(term)
    return explicit or (entry['name'] if entry else term)


def metric_findings(line):
    """Check result statements only, not team sizes, experience or resource limits."""
    numeric = bool(re.search(r'\d',line))
    result = bool(re.search(r'(?i)baseline|from\s+\d|final result|\d+(?:\.\d+)?\s*%|(?:reduc|improv|increas|decreas|achiev)\w*[^.;\n]{0,45}\d',line))
    if not numeric or not result:
        return []
    checks = {
        'metric definition':r'accuracy|precision|recall|F1|latency|throughput|cost|rate|availability|time|defects?|vulnerabilit|compliance|false.positive|pass|agreement|margin|duration|coverage|failure|events|deployments|backlog|incidents',
        'baseline and resulting value':r'from\s+\d[^.\n]{0,60}\bto\s+\d|baseline[^.\n]{0,70}\d[^.\n]{0,120}(?:final|result|\bto\b)[^.\n]{0,35}\d',
        'evaluation population or workload':r'dataset|queries|records|requests|cases|workload|benchmark|samples|fixtures|images|builds|deployments|tenants|endpoints|tickets|incidents|annotat|transactions|environments|microservices|reviews|templates',
        'measurement method and conditions':r'held.out|labelled|labeled|replay|same (?:load|hardware|workload)|fixed (?:load|hardware|workload)|load.test|A/B|paired|canary|adjudicat|independent review|expert review|human review|manual review|statistical fit|control group|identical',
        'measurement window':r'\b\d+[ -](?:day|week|month|hour|run|iteration|minute|cycle)|over (?:a|one|two|three|four|six|eight) [\w -]*(?:day|week|month|hour|weekly runs|daily runs)|every (?:\d+|one|two|three|four|six|eight) (?:day|week|month|hour)|\b(?:one|two|three|four|six|eight) iterations?\b|per (?:run|release|build|week|month)|across \d+ (?:runs|releases|builds)|\bquarterly\b',
        'attributable implementation change':r'after|change due to|change\s*:|caused by|by (?:implement|configur|introduc|chang|replac|tun|autom|batch|dedup|optim|add|remov)|following|through (?:implement|configur|introduc|chang|replac|tun|autom|batch|dedup|optim)',
    }
    missing=[name for name,pattern in checks.items() if not re.search(pattern,line,re.I)]
    issues=['Result needs '+', '.join(missing)+': '+line[:160]] if missing else []
    labelled=re.search(r'(?i)baseline\s*:\s*([\d,]+(?:\.\d+)?)([^;()\n]*?)(?:;|→|->)\s*final(?:\s+(?:result|value))?\s*:\s*([\d,]+(?:\.\d+)?)([^;()\n]*)',line)
    change=re.search(r'(?i)\bby\s+(\d+(?:\.\d+)?)\s*%',line)
    if labelled and change and change.start()<labelled.start():
        before=float(labelled[1].replace(',',''));after=float(labelled[3].replace(',',''))
        unit=lambda value:re.sub(r'[^a-z%/]','',value.casefold())
        if before and unit(labelled[2])==unit(labelled[4]):
            expected=abs(after-before)/before*100
            if abs(expected-float(change[1]))>1:
                issues.append('Baseline/result arithmetic disagrees with the stated improvement: '+line[:160])
    return issues


def content_findings(text,jd=''):
    warnings=[]
    for line in text.splitlines():
        if re.search(r'(?i)\b(?:LPM|LPA)\b|\b(?:salary|payroll|timezone)\s*:',line):
            warnings.append('Recruiter compensation or timezone leaked into professional content: '+line[:140])
        if MILESTONE.match(line.lstrip('- ')):
            warnings.append('Employer onboarding timetable copied into career history: '+line[:140])
        if not line.startswith('- '):continue
        warnings.extend(metric_findings(line))
        if re.search(r'(?i)SAST[^.;]{0,35}(?:container |image )?image scanning|SAST[^.;]{0,30}scan(?:ned|ning)? (?:container )?images',line):
            warnings.append('Separate SAST source-code analysis from container image/package vulnerability scanning: '+line[:140])
        if re.search(r'(?i)Kyverno',line) and re.search(r'(?i)across AWS,? GCP,? (?:and )?Azure|cloud configurations?',line) and not re.search(r'(?i)Kubernetes|cluster|admission',line):
            warnings.append('Explain Kyverno Kubernetes admission enforcement separately from cloud configuration governance: '+line[:140])
        if re.search(r'(?i)Cilium[^.;]{0,100}(?:via|in|through) Istio',line):
            warnings.append('Clarify separate Cilium and Istio enforcement boundaries; one does not automatically enforce the other\'s policies: '+line[:140])
        if re.search(r'(?i)SCADA',line) and not re.search(r'(?i)SCADA|industrial|operational technology|\bOT\b',jd):
            warnings.append('SCADA needs an industrial-control use case; it is not a source-code security scanner: '+line[:140])
        if re.search(r'(?i)\b(?:owned|led|managed|delivered)\b',line) and not re.search(r'(?i)decid|chose|select|trade.off|prioriti|approved|acceptance|risk|scope|review|implemented|designed|handover|rollback|budget|cost|margin',line):
            warnings.append('Ownership needs a personal decision, deliverable or resolved risk: '+line[:140])
    return list(dict.fromkeys(warnings))
