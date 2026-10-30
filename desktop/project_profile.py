"""Bounded, project-led profiles. Fictional claims remain deliberately allowed."""
from __future__ import annotations

import json
import re
from desktop.evidence_quality import text_similarity

from desktop.generation import normalize_skills, responsibilities, fields
from desktop.quality import without_dates

PROFILE_VERSION = "project-profile-9"

_ROLE_ENDING = re.compile(
    r"(?i)\b(?:engineer|developer|architect|manager|analyst|specialist|consultant|"
    r"administrator|admin|designer|scientist|tester|owner|lead|director|technician|"
    r"recruiter|writer|strategist|executive|representative|coordinator|accountant|"
    r"nurse|teacher|officer|operator|researcher|steward|auditor|controller|professor|"
    r"attorney|physician|doctor|pharmacist|therapist|advisor|adviser|planner|broker|"
    r"clerk|master|coach|trainer|lecturer|sre|devops|devsecops|professional)\s*(?:i{1,3}|iv|[1-4])?$"
)


def is_role_title(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip(" \t-*#")
    if value.casefold() == "professional":
        return True
    words = value.split()
    if not 1 <= len(words) <= 8 or re.search(r"[!?;:]|[.]$", value):
        return False
    if re.match(r"(?i)^(?:we|you|the|a|an|seeking|looking|hiring|join|must|strong|good|experience|responsibilities|build|built|design|designed|deliver|delivered|develop|developed|manage|managed|lead|led)\b", value):
        return False
    return bool(_ROLE_ENDING.search(value))


def safe_project_repair(previous, candidate):
    """A quality call must not replace evaluation with a duplicate data-flow bullet."""
    def pairs(values):
        return {(i,j) for i,b in enumerate(values) for j,a in enumerate(values[:i])
                if text_similarity(b.casefold(),a.casefold())>=.80}
    if pairs(candidate)-pairs(previous):return False
    for index,pattern in [(3,r'OAuth|IAM|JWT|permission|authenticat|authoriz|encrypt|security'),
                          (4,r'evaluat|baseline|benchmark|test|accuracy|precision|latency|throughput'),
                          (6 if len(previous)==7 else 5,r'deploy|release|rollback|runbook|bundle|CI/CD|handover')]:
        if re.search(pattern,previous[index],re.I) and not re.search(pattern,candidate[index],re.I):
            return False
    return True


def experience_years(source, jd):
    from desktop.project_experience import experience_profile
    return experience_profile(source, jd)['overall_years']


def target_role(jd, fallback):
    lines = jd.splitlines()
    for line in lines:
        label = re.match(r'(?i)^\s*(?:job title|position|target role|role)\s*:\s*(.+)', line)
        if label:
            value = re.split(r'\s*\(', label[1], maxsplit=1)[0].strip(' *#\t')
            if is_role_title(value):
                return value
    for line in lines[:8]:
        value = re.split(r'\s*\(', line.strip(' *#\t'), maxsplit=1)[0]
        if is_role_title(value):
            return value
    fallback = re.split(r'\s*\(', str(fallback or ''), maxsplit=1)[0]
    fallback = re.split(r'\s+(?:with|responsible for|specializing in|focused on)\b|[,;:]|\s+[—–-]\s+', fallback, maxsplit=1, flags=re.I)[0]
    fallback = re.sub(r'(?i)^(?:a|an|the)\s+', '', fallback).strip(' *#\t')
    return fallback if is_role_title(fallback) else 'Professional'


def consistent_years(text, years, profile=None):
    from desktop.project_experience import normalize_experience
    return normalize_experience(text, profile or {'overall_years':years,'specialties':[]})


def profile_continuation(text):
    """Small models return past-tense sentences where a noun phrase is needed."""
    text=re.sub(r'(?i)^(?:(?:strong|deep|extensive)\s+expertise\s+in|experienced\s+in|skilled\s+in|proficient\s+in)\s+','',text).strip()
    text=re.sub(r'(?i)^core implementation expertise\s+(?:with proficiency in|in)\s+','',text).strip()
    subject=re.match(r'(?i)^(React components|React hooks|SQL/PostgreSQL transactions|PostgreSQL transactions|Python APIs|FastAPI services|REST contracts)\s+(manage|handle|orchestrate|define|provide|enable|support|render)\b',text)
    if subject:
        text='implementing '+subject[1]+' that '+subject[2]+text[subject.end():]
    verbs={'designed':'designing','delivered':'delivering','developed':'developing',
           'engineered':'engineering','implemented':'implementing','built':'building',
           'configured':'configuring','integrated':'integrating','managed':'managing',
           'led':'leading','architected':'architecting','automated':'automating',
           'secured':'securing','optimized':'optimizing','established':'establishing'}
    pattern='|'.join(verbs)
    def convert(match):
        return re.sub(r'(?i)\b('+pattern+r')\b',lambda m:verbs[m[0].lower()],match[0])
    text=re.sub(r'(?i)^(?:'+pattern+r')(?:\s+and\s+(?:'+pattern+r'))?\b',convert,text)
    first=re.match(r'\w+',text)
    common={'designing','developing','implementing','testing','building','securing','leading','managing',
            'delivering','technical','transactional','automated','robust','architecting','engineering',
            'integrating','configuring','maintaining','optimizing','orchestrating','executing','coordinating','applying'}
    if first and first[0].lower() in common:text=text[:1].lower()+text[1:]
    return text


def brief(projects):
    """Keep all three contributions visible without filling the 4K context."""
    return [{"contribution": p.get("contribution", ""), "tools": p["tools"][:180],
             "implementation": [" ".join(b.split()[:24]) for b in p["bullets"][:3]],
             "security": " ".join(p['bullets'][3].split()[:24]),
             "evaluation": " ".join(p['bullets'][4].split()[:24]),
             "delivery": " ".join(p["bullets"][-1].split()[:24])} for p in projects]


def summary_issues(bullets, projects, headline, years, career_text=None):
    warnings = []
    if len(bullets) != 6:
        warnings.append("Professional summary should contain six substantial bullets.")
    if not bullets or not bullets[0].startswith(f"{headline} with {years}+ years of experience"):
        warnings.append("Summary opening must identify the target role and numeric experience.")
    filler = r"(?i)\b(?:results.driven|dynamic professional|highly motivated|passionate professional|proven track record|seasoned professional)\b"
    for i, bullet in enumerate(bullets):
        if re.search(filler, bullet):
            warnings.append("Summary contains generic profile filler: " + bullet[:100])
        minimum, maximum = (40, 55) if i == 0 else (30, 45)
        if not minimum <= len(bullet.split()) <= maximum:
            warnings.append(f"Summary bullet should contain {minimum}–{maximum} words: " + bullet[:100])
        numbers=re.findall(r"\d+(?:\.\d+)?\s*(?:%(?!\w)|\b(?:million|thousand|SKU|requests|records|users|ms|seconds)\b)",bullet,re.I)
        if numbers and not (career_text and all(re.search(re.escape(value),career_text,re.I) for value in numbers)):
            warnings.append("Summary outcome lacks matching generated-project evidence.")
        if re.search(r'(?i)\b(?:expertise in|proficient in|experienced in|skilled in)\s+(?:built|designed|implemented|developed|managed)\b', bullet):
            warnings.append("Summary contains an ungrammatical stitched phrase: " + bullet[:100])
        if re.search(r'(?i)\b(?:I|we|my|our)\b', bullet):
            warnings.append("Summary should use professional profile language without first-person pronouns.")
        if any(text_similarity(bullet.casefold(),previous.casefold()) > .75 for previous in bullets[:i]):
            warnings.append("Repeated professional-summary content: " + bullet[:100])
        if any(text_similarity(bullet.casefold(),b.casefold())>.78 for p in projects for b in p['bullets']):
            warnings.append('Summarize the career strength instead of copying a project responsibility: '+bullet[:100])
        normalized_bullet = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.]+", " ", bullet.casefold())).strip()
        for project in projects:
            project_name = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.]+", " ", str(project.get("name", "")).casefold())).strip()
            project_role = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.]+", " ", str(project.get("role", "")).casefold())).strip()
            target = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.]+", " ", str(headline).casefold())).strip()
            if len(project_name.split()) >= 2 and project_name in normalized_bullet:
                warnings.append("Keep project titles out of the professional summary.")
            if (len(project_role.split()) >= 2 and project_role not in target and target not in project_role
                    and project_role in normalized_bullet):
                warnings.append("Keep project-specific job titles out of the professional summary.")
            description = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#.]+", " ", str(project.get("description", "")).casefold())).strip()
            if len(description.split()) >= 12 and text_similarity(normalized_bullet,description) >= .90:
                warnings.append("Summarize career strengths instead of copying a project overview into the professional summary.")
    word_numbers=r'(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifty|ninety(?:[- ]eight)?)'
    for i,bullet in enumerate(bullets):
        if re.search(r'(?i)\b'+word_numbers+r'(?:[ -]+(?:point|and|one|two|three|four|five|six|seven|eight|nine|ten|thousand))*\s+(?:percent|seconds?|milliseconds?|records?|requests?|users?|(?:concurrent )?workloads?|(?:data corruption )?incidents?)\b',bullet):
            warnings.append('Keep quantified project outcomes out of the professional summary.')
    # Tools named in a summary must appear in the generated career, not the
    # uploaded source; fabricated project evidence is explicitly acceptable.
    from matching import normalizer
    career = career_text if career_text is not None else "\n".join(p['tools'] + ' ' + ' '.join(p['bullets']) for p in projects)
    # JD extraction deliberately discovers unknown names from phrases like
    # "using X". Applying that permissive extractor to prose turns words such
    # as "achieving" into alleged tools and discards otherwise valid summaries.
    def technology_text(text):
        return re.sub(r'(?i)\bOAuth\s*2(?:\.0)?\b', 'OAuth 2.0', text)
    implemented = normalizer.canonical_skills_in_text(technology_text(career))
    # A concrete implementation using a Python-only framework is Python
    # evidence even if the bullet does not repeat the language name. Require
    # both an action and the framework in the same project passage.
    career_lines = career.splitlines()
    if any(re.search(r'(?i)\b(?:implement\w*|develop\w*|built|build|designed|design|tested|test|integrat\w*|configur\w*|wrote|writ\w*)\b',line)
           and re.search(r'(?i)\b(?:FastAPI|Django|Flask|SQLAlchemy|pytest)\b',line)
           for line in career_lines):
        implemented.add('python')
    if any(re.search(r'(?i)\b(?:API|APIs|FastAPI|REST)\b',line)
           and re.search(r'(?i)\b(?:integrat\w*|connect\w*|forward\w*|rout\w*|call\w*|consum\w*)\b',line)
           for line in career_lines):
        implemented.add('api integration')
    if 'postgresql' in implemented or 'mysql' in implemented:
        implemented.add('sql')
    if re.search(r'(?i)\b(?:Jenkins|GitHub Actions|GitLab CI|Azure Pipelines)\b', career):
        implemented.add('ci/cd')
    if re.search(r'(?i)\b(?:tests?|tested|testing|validation|fixtures|evaluat\w*|benchmarks?|held.out|golden)\b',career):
        implemented.add('testing')
    if re.search(r'(?i)\bSDKs?\b',career):
        implemented.update({'sdk','sdks'})
    if re.search(r'(?i)\b(?:OAuth|IAM|JWT|permissions?|authentication|authorization|encryption)\b',career):
        implemented.add('security')
    if re.search(r'(?i)\bingest\w*|\bextract\w*',career) and re.search(r'(?i)\btransform\w*|Delta table|PySpark|Spark SQL',career):
        implemented.add('etl')
    for term in sorted(normalizer.canonical_skills_in_text(technology_text(' '.join(bullets))) - implemented):
        if re.search(r'(?i)\byears?\b|\bexperience\b', term):
            continue
        warnings.append("Summary technology needs generated-project evidence: " + term)
    return list(dict.fromkeys(warnings))


def summary_topics(jd, projects):
    """Themes come from the completed career and JD, never a fixed technology recipe."""
    families = [
        (r'data.label|synthetic data|frontier|reward model|\bRLHF\b', 'AI data strategy, labeling controls, evaluation design and client delivery'),
        (r'vulnerability.management|service.mesh|policy.as.code|DevSecOps', 'cloud hardening, Kubernetes policy, remediation and security reviews'),
        (r'Salesforce|Apex|LWC|CPQ', 'Salesforce application architecture, business workflows and platform customization'),
        (r'Java|Spring|Angular', 'application design, service contracts and user interface implementation'),
        (r'React|full[ -]*stack', 'frontend behavior, backend services and transactional application design'),
        (r'Genie|Collibra|Unity Catalog', 'semantic analytics, metadata governance and catalogue administration'),
        (r'Databricks|Spark|data engineer', 'data engineering, transformation correctness and data lifecycle design'),
        (r'Terraform|landing zone|EKS', 'cloud infrastructure, identity boundaries and infrastructure automation'),
        (r'QA|Selenium|Playwright|test automation', 'test architecture, automated quality assurance and defect diagnosis'),
        (r'GenAI|LLM|retriev|agentic', 'AI application mechanisms, grounding and answer evaluation'),
    ]
    selected = [label for pattern, label in families if re.search(pattern, jd, re.I)]
    return [selected[0] if selected else 'the primary implementation strengths of the target role',
            selected[1] if len(selected)>1 else 'interfaces, business rules and integration mechanisms from the projects',
            'security, reliability and failure handling actually implemented in the projects',
            'validation, testing and delivery practices actually implemented in the projects',
            'distinct technical ownership, operational handover and cross-functional delivery from the projects']


def structured_summary(projects, headline, years, experience=None, job_brief=None):
    """A grammatical fallback grounded in generated project fields, not source claims."""
    from desktop.project_experience import career_opening
    def scope(index):
        p = projects[index % len(projects)]
        value = p.get('contribution') or p.get('role') or 'business solution engineering'
        actions = r'designed|developed|built|implemented|optimi[sz]ed|configured|integrated|automated|delivered|deployed|led|managed|engineered|architected|established|created|orchestrated|secured|enforced|migrated|evaluated'
        value = re.sub(r'(?i)^(?:'+actions+r')(?:\s+and\s+(?:'+actions+r'))?\s+', '', value)
        value = re.sub(r'(?i)^and\s+(?:'+actions+r')\s+', '', value)
        value = re.split(r'[,;]', value, maxsplit=1)[0]
        value = re.sub(r'(?i)\band\s+(?:'+actions+r')\s+', 'and ', value)
        value = re.split(r'(?i)\s+(?:to|while|and)\s+(?:reduce|improve|increase|decrease|achieve|cut|save)\b|,?\s+(?:reducing|improving|increasing|decreasing|achieving|saving)\b',value,maxsplit=1)[0]
        # Outcomes stay in projects. A planned scope can itself contain a metric;
        # it must not bypass the summary validator through the local fallback.
        value = re.sub(r'(?i)\b(?:by\s+)?\d+(?:\.\d+)?\s*(?:%|percent\b|million\b|thousand\b|requests\b|records\b|users\b|ms\b|seconds\b)\s*','',value)
        value = re.sub(r'(?i)\b\d+(?:\.\d+)?[kmb]?\+?\s*(?:records|requests|users|cases|transactions)\b(?:\s+(?:monthly|daily|annually))?', '', value)
        value = re.sub(r'[.;]+', ' and ', value.strip(' .;')).strip().rstrip(' ,')
        if not value:
            return 'the owned solution design'
        adjectives = {'robust','incremental','scalable','granular','unified','modular','automated','repeatable','secure','reliable','custom','advanced'}
        return value[:1].lower()+value[1:] if value.split()[0].lower() in adjectives else value
    def tools(index):
        from desktop.quality import contains_skill
        from matching import technology_catalog
        project = projects[index % len(projects)]
        values = re.split(r'[,;]', project['tools'])
        values = list(dict.fromkeys(without_dates(v).strip(' .') for v in values if v.strip()))
        implementation = ' '.join(project['bullets'])
        generic = {'security','testing','integration','development','cloud','monitoring','devops','deployment','architecture'}
        jd_text = ' '.join(r['text'] for r in (job_brief or {}).get('requirements',[]))
        values = [v for v in values if v.casefold() not in generic and contains_skill(implementation,v)
                  and (technology_catalog.entry_for(v) or re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)',jd_text,re.I))]
        chosen = []
        for value in values:
            if len(chosen) < 3 and (not chosen or len((' '.join(chosen+[value])).split()) <= 7):
                chosen.append(value)
        return ', '.join(chosen) or 'the assigned technology stack'
    career = ' '.join(' '.join(p['bullets']) for p in projects)
    def mechanisms(candidates, default):
        return ', '.join(label for pattern,label in candidates if re.search(pattern,career,re.I)) or default
    security = mechanisms([(r'OAuth','OAuth authentication'),(r'JWT','JWT validation'),(r'permission|authoriz|RBAC','scoped authorization'),
                           (r'encrypt','data encryption'),(r'error|retry|retries|backoff','controlled failure handling')], 'the project access controls and failure boundaries')
    delivery = mechanisms([(r'pytest','pytest'),(r'Jest','Jest'),(r'fixture|mock','repeatable test fixtures'),
                           (r'CI/CD|GitHub Actions|pipeline','automated delivery checks'),(r'rollback','rollback validation')], 'the project validation and release procedures')
    prefix = career_opening(headline, years, experience)
    endings = [' by defining the business constraint, choosing an implementation boundary, validating the resulting workflow and documenting the decisions that governed release and operational ownership.',
               ' by mapping the business constraint to technical decisions, testing the delivered workflow and explaining the resulting operational responsibilities.',
               ' through technical decisions, repeatable validation and documented release ownership.']
    openings = [prefix+' delivering '+scope(0)+tail for tail in endings]
    opening = next((s for s in openings if 40 <= len(s.split()) <= 55), min(openings,key=lambda s:abs(len(s.split())-45)))
    return [opening,
        'Technical delivery includes ' + scope(0) + ' using ' + tools(0) + ', with the implementation shaped by the project constraint, chosen integration boundary and acceptance criteria.',
        'A separate contribution covers ' + scope(1) + ' using ' + tools(1) + ', connecting the owned workflow to validation, failure handling and a documented handover.',
        'Security decisions apply ' + security + ' to the delivered workflows, with explicit access boundaries and recovery behavior for their users and data.',
        'Validation and release ownership uses ' + delivery + ', connecting design changes to repeatable checks, controlled deployment and operational support.',
        'Client and team delivery includes ' + scope(2) + ' using ' + tools(2) + ', resolving trade-offs with stakeholders and documenting the support decisions.']


def polish_summary_opening(text):
    """Remove formulaic openings without changing claims or project evidence."""
    present={'built':'Builds','designed':'Designs','developed':'Develops','delivered':'Delivers',
             'deployed':'Deploys','executed':'Executes','implemented':'Implements',
             'configured':'Configures','orchestrated':'Orchestrates','established':'Establishes'}
    opening=re.match(r'(?i)^('+'|'.join(present)+r')(?:\s+and\s+('+'|'.join(present)+r'))?\b',text)
    if opening:
        value=present[opening[1].lower()]
        if opening[2]:value+=' and '+present[opening[2].lower()].lower()
        text=value+text[opening.end():]
    agreement={'enforcing':'enforces','delivering':'delivers','maintaining':'maintains',
               'managing':'manages','validating':'validates','integrating':'integrates',
               'securing':'secures','testing':'tests','deploying':'deploys',
               'monitoring':'monitors','designing':'designs','implementing':'implements'}
    text=re.sub(r'(?i)\b(Designs|Builds|Implements|Establishes|Develops|Secures|Leads|Tests)\s+and\s+('+
                '|'.join(agreement)+r')\b',
                lambda match:match[1]+' and '+agreement[match[2].lower()],text)
    for pattern,replacement in [
        (r'(?i)^Experienced in designing\s+', 'Designs '),
        (r'(?i)^Experienced in implementing\s+', 'Implements '),
        (r'(?i)^Strong expertise in implementing\s+', 'Implements '),
        (r'(?i)^Strong expertise in establishing\s+', 'Establishes '),
        (r'(?i)^Proven ability to own\s+', 'Owns '),
    ]:
        if re.match(pattern,text):
            return re.sub(pattern,replacement,text,count=1)
    return text


def make_summary(writer, projects, headline, years, experience=None, job_brief=None):
    from desktop.project_experience import career_opening
    context = json.dumps(brief(projects), ensure_ascii=False)
    saved_jd = writer.jd
    topics = summary_topics(saved_jd, projects)
    writer.jd = 'Target role: ' + headline + '\nSummary themes: ' + '; '.join(topics)
    # Requirement completeness is enforced by the ledger/project stage; the
    # summary describes completed career evidence instead of repeating the JD.
    opening = career_opening(headline, years, experience)
    bullets, notices = [], []
    methods = []
    fallback = structured_summary(projects, headline, years, experience, job_brief)
    try:
        for half, keys in enumerate((['career_scope','implementation','data_integration'], ['security_reliability','delivery_quality','ownership_collaboration'])):
            # Summaries need implementation evidence, not project title labels.
            # Keeping titles out of this input prevents copy/leak retries while
            # the existing field-leak and evidence validation remain intact.
            context = json.dumps([{'contribution':p.get('contribution',p['role']), 'tools':p['tools'],
                                   'evidence':p['bullets'][:3] if half==0 else p['bullets'][3:]} for p in projects], ensure_ascii=False)
            schema = {'type':'object','properties':{key:{'type':'string'} for key in keys},'required':keys,'additionalProperties':False}
            if half == 0:
                # Constrain only the agreed career prefix; the model writes the
                # actual summary. This avoids wasting retries on role/duration
                # wording without fabricating a different experience total.
                schema['properties']['career_scope']['pattern'] = '^' + re.escape(opening).replace(r'\ ', ' ') + ' .+$'
            instructions = ({'career_scope':'Begin exactly: '+opening+'. Complete this as one 40-55 word grammatical bullet; retain all experience durations.',
                             'implementation':topics[0], 'data_integration':topics[1]} if half==0 else dict(zip(keys,topics[2:])))
            task = ('Write exactly 3 complete professional-summary bullets in these JSON string fields: '+json.dumps(instructions)+
                    '. Each value is ONE complete, compact professional-profile sentence, not a continuation or a topic label. Use 30-45 words per bullet, except career_scope 40-55. '
                    'Vary sentence openings. State the actual design choice, constraint, validation or personal contribution rather than generic expertise claims. '
                    'Describe career-level strengths using the completed fictional projects, not a list of past project tasks. '
                    'Do not copy project overview sentences or project-specific job titles. No numeric claims except supplied experience durations; no metrics, percentages, project names, I/we, calendar dates, unrelated technologies or invented mechanisms absent from these projects. '
                    'Avoid repeated points and awkward phrases such as Expertise in designed. Completed projects: '+context)
            def check(value):
                result = [consistent_years(without_dates(v), years, experience) for v in fields(value, keys).values()]
                if half == 0 and opening.endswith(';'):
                    prefix = opening[:-1]
                    if result[0].startswith(prefix):
                        result[0] = opening + ' ' + result[0][len(prefix):].lstrip(' ,;:.')
                if half == 0 and not result[0].startswith(opening):
                    raise ValueError('Keep the exact target role and all overall/specialty experience durations in the summary opening.')
                career_text='\n'.join(b for p in projects for b in p['bullets'])
                quality = summary_issues(bullets+result, projects, headline, years,career_text=career_text)
                quality = [w for w in quality if not w.startswith(('Professional summary should contain', 'Summary bullet should contain'))]
                # Word targets remain visible in the report. A few words either
                # side of the target should not discard a substantive sentence.
                for index, bullet in enumerate(result, start=len(bullets)):
                    low, high = (28, 65) if index == 0 else (22, 55)
                    if not low <= len(bullet.split()) <= high:
                        quality.append(f'Write a complete, concise summary bullet of {low}-{high} words.')
                if quality:
                    raise ValueError('; '.join(quality[:2]))
                return result
            try:
                part = writer.ask(task, check, f'summary_{half+1}', response_schema=schema)
                methods.append('model')
            except ValueError as error:
                part = fallback[half*3:half*3+3]
                methods.append('structured-fallback')
                notices.append('Summary part '+str(half+1)+' used a project-grounded structured fallback after bounded validation: '+str(error)[:180])
            bullets.extend(part)
    finally:
        writer.jd = saved_jd
    bullets=[bullets[0]]+[polish_summary_opening(value) for value in bullets[1:]]
    career_text=' '.join(b for p in projects for b in p['bullets'])
    warnings = notices + summary_issues(bullets, projects, headline, years,career_text=career_text)
    writer.profile_metadata = {'version':PROFILE_VERSION, 'summary_methods':methods, 'themes':topics,
                               'fallback_used':'structured-fallback' in methods}
    return bullets, list(dict.fromkeys(warnings))


SKILL_GROUPS = [
    (r"python|fastapi|flask|backend|microservice|java|spring", "Programming & Backend Development"),
    (r"salesforce|apex|lwc|cpq", "Salesforce Architecture & Business Applications"),
    (r"QA|selenium|playwright|test automation", "Test Automation & Quality Engineering"),
    (r"oauth|jwt|iam|security|authentication|rbac", "Security & Identity"),
    (r"sql|database|postgres|mysql|redis|mongo|cache", "Databases & Caching"),
    (r"aws|azure|gcp|cloud|s3|lambda", "Cloud Platforms"),
    (r"terraform|kubernetes|eks|aks|docker|ci/cd|github actions|devops", "Infrastructure, Containers & CI/CD"),
    (r"databricks|spark|pipeline|etl|data engineer|delta", "Data Engineering & Lakehouse"),
    (r"collibra|unity catalog|governance|genie|metadata", "Governance, Metadata & Semantic Analytics"),
    (r"genai|generative|llm|rag|retrieval|agent|machine learning", "AI, GenAI & Retrieval"),
    (r"kafka|queue|rabbitmq|distributed|event", "Messaging & Distributed Systems"),
    (r"prometheus|grafana|datadog|monitor|logging|observability", "Monitoring & Observability"),
    (r"react|vue|angular|frontend|typescript|javascript", "Frontend & Web Technologies"),
]


def make_skills(writer, jd, projects, complete, job_brief=None):
    context = json.dumps([{'contribution':p.get('contribution',p['role']),'tools':p['tools']} for p in projects], ensure_ascii=False)
    names = [name for trigger, name in SKILL_GROUPS if re.search(trigger, jd, re.I)]
    names += ["Testing, Debugging & Code Quality", "Version Control & Delivery"]
    names = list(dict.fromkeys(names))[:10]
    if len(names) < 4:
        names.insert(0, "Core Technologies & Implementation")
    categories = []
    saved_jd = writer.jd
    writer.jd = 'Relevant technologies and practices: ' + ', '.join((job_brief or {}).get('technologies', []))
    try:
        for half, group in enumerate((names[::2], names[1::2])):
            schema = {"type":"object", "properties":{"categories":{"type":"array", "minItems":1,
                      "maxItems":len(group), "items":{"type":"object", "properties":{
                          "name":{"type":"string","enum":group},
                          "items":{"type":"array","minItems":2,"maxItems":8,"items":{"type":"string"}}},
                          "required":["name","items"],"additionalProperties":False}}},
                      "required":["categories"],"additionalProperties":False}
            task = ('Return {"categories":[{"name":string,"items":[string]}]}. Use these category names: '
                    + json.dumps(group) + '. Give 3–8 concise skills per relevant category. Include tools AND implementation '
                    'concepts/practices (such as asynchronous programming or schema evolution) when relevant. '
                    'No sentences, unrelated clouds, vague adjectives, locations or Additional Capabilities. '
                    'Omit categories without relevant skills. Under 250 words total. Completed projects: ' + context)
            def check(value):
                result = normalize_skills(value)
                result = [c for c in result if c['name'] in group]
                if not result:
                    raise ValueError("Return usable JD-specific skill categories.")
                return result
            rows = [r['text'] for r in (job_brief or {}).get('requirements', []) if r['kind'] in {'technology','capability'}]
            batches = writer.batches(rows, task) if hasattr(writer, 'batches') else [writer.jd]
            try:
                for index,batch in enumerate(batches):
                    writer.jd = batch
                    categories.extend(writer.ask(task, check, f'skills_{half+1}_batch_{index+1}', response_schema=schema))
            except ValueError:
                # A malformed optional skills response must not discard complete projects.
                # Exact planned tools are a local fallback, not raw recruiter wording.
                items = list(dict.fromkeys(t.strip() for p in projects for t in p['tools'].split(',') if t.strip()))
                if items:
                    categories.append({'name':group[0],'items':items[:12]})
    finally:
        writer.jd = saved_jd
    return complete(categories, jd, preserve_concepts=True)


def certification_candidates(jd):
    # Backward-compatible public helper; selection itself is now local and ranked.
    from desktop.certifications import candidates
    return candidates(jd)
