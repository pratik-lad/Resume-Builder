"""Shared offline JD brief and scope assignment; no additional model call."""
from __future__ import annotations

import copy
import re

VERSION = "job-brief-5"
STOP = set("a an the and or of in to for with using on as by from experience skills required preferred strong good knowledge ability hands years development engineering implementation".split())


def words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9+#.-]*", text.casefold()) if len(w) > 2 and w not in STOP}


def extra_requirements(jd, existing):
    """Keep unfamiliar capabilities instead of silently relying on a tech dictionary."""
    from desktop.evidence_quality import requirement_kind, skill_terms, is_heading, strip_milestone
    rows = [copy.deepcopy(r) for r in existing if not is_heading(r['text'])]
    for row in rows:
        row['source_passage'] = row.get('source_passage',row['text'])
        row['text'] = strip_milestone(row['text'])
        row['kind'] = requirement_kind(row['text'], row['kind'])
        row['terms'] = skill_terms(row['text']) if row['kind'] in {'capability','technology','knowledge'} else []
    comparable = lambda value: re.sub(r"\W+", " ", value.casefold()).strip()
    optional, qualification_section, overview_section = False, False, False
    for line in jd.splitlines():
        original = line.strip(" \t-*•●")
        text = strip_milestone(original)
        if not text:
            continue
        heading = re.match(r"(?i)^(preferred|nice.to.have|optional|required|mandatory|must.have|technical skills|core skills|essential skills|key responsibilities|responsibilities|certifications|qualifications)\b([^:]*)[:]?\s*$", text)
        if heading and len(text.split()) <= 5:
            overview_section = False
            optional = bool(re.match(r"(?i)preferred|nice.to.have|optional", text))
            qualification_section = bool(re.search(r'(?i)certif|qualification|credential',text))
            continue
        if re.fullmatch(r'(?i)(?:position|job) overview\s*:',text):
            overview_section = True
            continue
        if overview_section:
            continue
        if len(text) < 3:
            continue
        if is_heading(text):
            continue
        norm = comparable(text)
        matches = [r for r in rows if norm == comparable(r['text']) or
                   (len(norm) >= 24 and len(comparable(r['text'])) >= 24 and
                    (norm in comparable(r['text']) or comparable(r['text']) in norm) and
                    r['required'] == (not optional))]
        if matches:
            for row in matches:
                row['required'] = not optional and not bool(re.search(r'(?i)\bpreferred|optional|nice.to.have',text))
                if (qualification_section or re.search(r'(?i)certif|credential',text)) and row['kind'] != 'logistics':
                    row['kind'] = 'qualification'
            continue
        if requirement_kind(text,'') == 'logistics':
            kind = "logistics"
        elif qualification_section or requirement_kind(text,'') == 'qualification':
            kind = "qualification"
        elif requirement_kind(text,'') == 'knowledge':
            kind = 'knowledge'
        else:
            # Unknown named tools and implementation concepts remain assessable.
            kind = "capability" if len(text.split()) > 3 else "technology"
        if re.fullmatch(r"(?i)strong|good|average|very good|India|Pune", text):
            continue
        rows.append({'id': f"U{len(rows)+1:03}", 'text': text, 'kind': kind,
                     'required': not optional and not bool(re.search(r"(?i)\bpreferred|optional|nice.to.have", text)),
                     'terms': skill_terms(text) if kind in {'capability','technology','knowledge'} else [],
                     'source_passage': original})
    # A duration does not erase the technologies in the same JD passage.
    # Keep the qualification row for experience review and add a technical row
    # whose owner and evidence can be planned independently.
    technical_rows = []
    for row in rows:
        if row['kind'] != 'qualification' or not re.search(r'(?i)\b(?:years?|yrs?|YOE)\b', row['text']):
            continue
        terms = skill_terms(row['text'])
        if terms:
            technical_rows.append({**copy.deepcopy(row), 'id': row['id']+'T',
                                   'kind': 'technology', 'terms': terms,
                                   'experience_requirement_id': row['id']})
    return rows + technical_rows


def build(jd, source, headline):
    from desktop.project_experience import experience_profile
    from desktop.project_rules import classify, capabilities
    requirements = classify(jd)
    preferred_rows=[]
    for row in requirements:
        row['source_passage'] = row.get('source_passage') or next((line.strip() for line in jd.splitlines() if row['text'].strip() in line), row['text'])
        row['alternatives'] = bool(re.search(r'(?i)\bor equivalent\b|\bsuch as\b|\be\.g\.|\bfor example\b|\bor\b', row['text']))
        row['terms'] = list(dict.fromkeys(re.sub(r'(?i)\s+(?:concepts|applications|practices)$', '', t).replace('llms','llm') for t in row['terms']))
        if re.search(r'(?i)React\.js', row['text']) and not re.search(r'(?i)\bJavaScript\b', row['text']):
            row['terms'] = [t for t in row['terms'] if t != 'javascript']
        for term in ('pytest','Jest','GitHub Copilot','Cursor','ChatGPT','Vibe Coding'):
            if re.search(r'(?i)(?<!\w)'+re.escape(term)+r'(?!\w)', row['text']):
                if term.casefold() not in {t.casefold() for t in row['terms']}:row['terms'].append(term)
        if not row['terms']:
            for pattern,term in [(r'\bAPIs?\b','api'),(r'\bdatabases?\b','database'),(r'\bunit tests?\b','unit testing'),(r'\bcode quality\b','code quality')]:
                if re.search(pattern,row['text'],re.I):row['terms'].append(term)
        # Parenthetical preferences do not turn the main language into an optional requirement.
        preference=re.search(r'(?i)\(([^)]*preferred)\)',row['text'])
        if preference and not re.search(r'(?i)^AWS',row['text']):
            from desktop.evidence_quality import skill_terms
            optional=skill_terms(preference[1])
            row['terms']=[t for t in row['terms'] if t not in optional]
            row['text']=(row['text'][:preference.start()]+row['text'][preference.end():]).strip()
            row['required']=True
            if optional:
                preferred_rows.append({'id':row['id']+'P','text':', '.join(optional)+' (preferred)',
                    'terms':optional,'kind':'technology','required':False,'source_passage':row['source_passage'],'alternatives':False})

    requirements.extend(preferred_rows)
    from desktop.requirement_ledger import alternative_groups
    from desktop.skill_coverage import pattern
    all_caps=capabilities(jd)
    by_id={r['id']:r for r in requirements}
    existing=set()
    for cap in all_caps:
        row=by_id.get(cap.get('requirement_id'))
        if not row:continue
        existing.add(row['id'])
        cap.update(label=row['text'],required=row['required'])
        if row['terms']:
            groups=alternative_groups(row['text'],row['terms']);options={t for g in groups for t in g}
            cap['facets']=[pattern(t).pattern for t in row['terms'] if t not in options]+['|'.join(pattern(t).pattern for t in g) for g in groups]
    all_caps += [{'label':r['text'],'facets':[pattern(t).pattern for t in r['terms']], 'required':r['required'],'requirement_id':r['id']} for r in preferred_rows if r['id'] not in existing]
    overview = re.search(r'(?is)(?:position|job) overview\s*:\s*(.*?)(?=\n\s*(?:key responsibilities|required skills|mandatory skills|preferred skills)\s*:|\Z)',jd)
    scope = ''
    if overview:
        sentences = re.split(r'(?<=[.!?])\s+',overview[1])
        scope = next((s.strip() for s in sentences if re.search(r'(?i)\b(?:rather than|primary technical|core mission|role is|role sits|focuses on)\b',s)), '')
    return {'version': VERSION, 'target_role': headline,
            'experience': experience_profile(source, jd), 'requirements': requirements,
            'role_context': scope,
            'mandatory_ids': [r['id'] for r in requirements if r['required']],
            'preferred_ids': [r['id'] for r in requirements if not r['required']],
            'technologies': sorted({t for r in requirements if r['kind'] in {'capability','technology','knowledge'} for t in r['terms']}),
            'capabilities': all_caps,
            'certification_requirements': [r for r in requirements if re.search(r'(?i)certif|credential|\bCTA\b|\bCKA\b', r['text'])],
            'logistics': [r['text'] for r in requirements if r['kind'] == 'logistics']}


def planning_text(brief, limit=None):
    """Never truncate a ledger. The caller batches by rendered token count."""
    rows = sorted(brief['requirements'], key=lambda r: (not r['required'], r['kind']))
    return ('Role context: '+brief['role_context']+'\n' if brief.get('role_context') else '') + '\n'.join(r['id'] + (' mandatory: ' if r['required'] else ' preferred: ') + r['text']
                     for r in rows if r['kind'] in {'capability', 'technology'})


def assign(brief, roles):
    """Use model-owned IDs, then semantic fit and bounded balancing, never index slicing."""
    rows = [r for r in brief['requirements'] if r['kind'] in {'capability', 'technology'}]
    by_id = {r['id']: r for r in rows}
    for role in roles:
        ids = role.get('requirement_ids', [])
        if isinstance(ids, str):
            ids = re.findall(r'[A-Z]+\d+', ids)
        role['requirement_ids'] = list(dict.fromkeys(v for v in ids if v in by_id))
        role['assigned_capabilities'] = []
    def score(role, text):
        scope = ' '.join(str(role.get(k, '')) for k in ('project_name', 'problem', 'contribution', 'stack', 'capabilities'))
        return len(words(scope) & words(text)) * 3 - len(role['requirement_ids']) * .15
    for row in rows:
        owners = [r for r in roles if row['id'] in r['requirement_ids']]
        if len(owners) > 1:
            best = max(owners, key=lambda r: score(r,row['text']))
            for role in owners:
                if role is not best:
                    role['requirement_ids'].remove(row['id'])
    for row in sorted(rows, key=lambda r: not r['required']):
        if any(row['id'] in role['requirement_ids'] for role in roles):
            continue
        best = max(roles, key=lambda r: score(r, row['text']))
        best['requirement_ids'].append(row['id'])
    for cap in brief['capabilities']:
        text = cap['label'] + ' ' + ' '.join(cap['facets'])
        def cap_score(role):
            owned = ' '.join(by_id[i]['text'] for i in role['requirement_ids'])
            return score(role, text) + len(words(owned) & words(cap['label'])) - len(role['assigned_capabilities']) * .3
        owners = [r for r in roles if cap.get('requirement_id') in r['requirement_ids']]
        best = max(owners or roles, key=cap_score)
        best['assigned_capabilities'].append(copy.deepcopy(cap))
    for role in roles:
        role['assigned_requirements'] = [by_id[i] for i in role['requirement_ids']]
        from desktop.skill_coverage import evidence_slots
        role['evidence_slots'] = evidence_slots(role)
    return roles


def scope_text(brief, role, slots=None):
    owned = role.get('assigned_requirements', [])
    lines = [r['id'] + ': ' + r['text'] for r in sorted(owned, key=lambda r: not r['required'])]
    mechanisms = role.get('evidence_slots', {})
    fields = ['data_flow','implementation','integration','security','evaluation_delivery','collaboration','ownership']
    selected = [fields[int(slot)]+': '+', '.join(values) for slot,values in mechanisms.items()
                if slots is None or int(slot) in slots]
    return ('Target role: ' + brief['target_role'] + '\nOverall/specialty experience: ' +
            str(brief['experience']['overall_years']) + '+ overall; ' +
            ', '.join(str(s['years']) + '+ ' + s['label'] for s in brief['experience']['specialties']) +
            '\nOwn contribution: ' + role['contribution'] + '\nArchitecture/ownership focus: ' + role.get('capabilities','') + '\nAssigned stack: ' + role['stack'] +
            '\nOwned JD requirements:\n' + '\n'.join(lines) +
            ('\nRequired mechanisms by output field:\n'+'\n'.join(selected) if selected else ''))
