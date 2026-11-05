"""Date-free fictional career totals, separate from specialty requirements.

Reported durations are claims in the edited resume, never verified employment.
"""
from __future__ import annotations

import re
import unicodedata

VERSION = "experience-6"
YEARS = re.compile(r"(?i)(?<![\w.])(\d{1,2}(?:\.\d+)?)(?:\s*\+|\s*(?:[-–—]|to)\s*\d{1,2}(?:\.\d+)?)?\s*(?:years?|yrs?|YOE)\b")
SPECIALTIES = [
    ("full-stack development", r"full[\s-]*stack"),
    ("frontend development", r"front[\s-]*end"),
    ("backend development", r"back[\s-]*end"),
    ("Python development", r"\bPython\b"),
    ("React development", r"\bReact(?:\.js)?\b"),
    ("SQL development", r"\bSQL\b|\bPostgreSQL\b"),
    ("Kubernetes", r"\bKubernetes\b|\bEKS\b"),
    ("Terraform", r"\bTerraform\b"),
    ("Databricks", r"\bDatabricks\b"),
    ("AWS", r"\bAWS\b"),
    ("Azure", r"\bAzure\b"),
    ("Salesforce", r"\bSalesforce\b"),
    ("technical architecture", r"(?:Technical|Lead)\s+Architect(?:ure)?"),
    ("Java development", r"\bJava\b"),
    ("test automation", r"test automation|QA automation"),
]


def durations(text):
    """Read lower bounds; calendar dates and workload retention are irrelevant."""
    matches = list(YEARS.finditer(text))
    result = []
    for index, match in enumerate(matches):
        value = float(match[1])
        years = int(value) if value.is_integer() else value
        if not 0 < years < 60:
            continue
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        tail = text[match.end():stop].splitlines()[0] if text[match.end():stop] else ""
        tail = re.split(r"[;]|\.(?:\s|$)", tail, maxsplit=1)[0][:180]
        head = text[max(0, match.start() - 55):match.start()]
        # The qualification immediately after the duration determines scope.
        # Tools later in 'software development using Python' are not a Python total.
        qualifier = re.sub(r"(?i)^\s*(?:(?:of|in|with|as)\s+)?(?:experience\s+(?:(?:of|in|with|using|as)\s+)?)?", "", tail)
        qualifier = re.sub(r"(?i)^hands[\s-]*on\s+(?:with|in|using)\s+", "", qualifier)
        overall = bool(re.match(r"(?i)(?:software\s+(?:development|engineering)|(?:data|cloud|platform)\s+engineering|(?:total|overall|professional|industry|work|working|relevant)\s+(?:experience|development))\b", qualifier))
        specialty = None
        if not overall:
            for name, pattern in SPECIALTIES:
                if re.match(r"(?i)" + pattern, qualifier):
                    specialty = name
                    break
        labelled = bool(re.search(r"(?i)\b(?:(?:total|overall|professional)\s+)?(?:experience|exp\.?)\s*[:–—-]\s*$", head))
        generic = bool(re.match(r"(?i)^\s*(?:of\s+)?(?:(?:total|overall|professional|industry|relevant|work|working)\s+){0,2}experience\b", tail))
        generic = generic or bool(re.search(r'(?i)YOE\b', match[0])) or bool(re.match(
            r'(?i)^\s*(?:of\s+)?(?:delivering|building|leading|designing|developing|managing)\b', tail))
        if not (overall or specialty or labelled or generic):
            continue
        result.append({"years": years, "specialty": specialty, "start": match.start(),
                       "end": match.end(), "passage": text[max(0, match.start()-25):match.end()+len(tail)].strip()})
    return result


def jd_analysis(text):
    """Parse a normalized view only; retain raw JD passages and scope."""
    def clean(value):
        value = unicodedata.normalize('NFKC', value)
        value = re.sub(r'[\u2010-\u2015\u2212]', '-', value)
        value = re.sub(r'\*\*|__|`', '', value)
        return re.sub(r'\s+', ' ', value).strip(' \t-*#\u2022\u25cf')
    label = re.compile(r'(?i)^(?:(?:minimum|required|total|overall|professional|relevant)\s+)*(?:experience|exp\.?|YOE)(?:\s+(?:required|minimum|total|overall))?\s*[:=-]?\s*(?:(?:at least|a minimum of|minimum of|minimum|min\.?|required)\s+)*')
    modifier = r'(?:(?:hands[ -]on|relevant|professional|overall|total|industry|working|work|practical|demonstrable|IT)\s+)'
    originals = text.splitlines()
    rows, warnings = [], []
    index = 0
    while index < len(originals):
        original = originals[index]; line = clean(original); index += 1
        if re.match(r'(?i)^(?:project duration|contract(?: duration)?|engagement|notice|retention|salary|budget|timezone|work timings?|weeks?\s*\d|months?\s*\d)\b', line):
            continue
        heading = label.match(line)
        if heading and not line[heading.end():].strip() and index < len(originals):
            next_line = clean(originals[index])
            if re.match(r'\d', next_line):
                original += '\n' + originals[index]; line += ' ' + next_line; index += 1
                heading = label.match(line)
        if heading:
            rest = line[heading.end():]
            bare = re.fullmatch(r'(\d{1,2}(?:\.\d+)?(?:\s*(?:-|to)\s*\d{1,2}(?:\.\d+)?)?\s*\+?)', rest)
            if bare:
                line += ' years'
        matches = list(YEARS.finditer(line))
        found = False
        for n, match in enumerate(matches):
            value = float(match[1]); years = int(value) if value.is_integer() else value
            if not 0 < years < 60: continue
            before = line[:match.start()]
            if re.search(r'(?i)(?:up to|less than|under|maximum|max)\s*$', before):
                found = True; continue
            end = matches[n+1].start() if n+1 < len(matches) else len(line)
            tail = re.split(r'[;]|\.(?:\s|$)', line[match.end():end], maxsplit=1)[0].strip(' ,')
            prefix = re.split(r'(?i)[,;]|\b(?:including|and)\b', before)[-1].strip()
            qualified = tail
            for _ in range(3):
                qualified = re.sub(r'(?i)^(?:of|in|with|as|using)\s+', '', qualified)
                qualified = re.sub(r'(?i)^experience\s*(?:(?:in|with|using|as|of)\s+)?', '', qualified)
                qualified = re.sub(r'(?i)^'+modifier+'+', '', qualified)
            overall = bool(re.search(r'(?i)\b(?:overall|total)\b', prefix+' '+tail))
            specialty = None
            if not overall:
                for name, pattern in SPECIALTIES:
                    if re.match(r'(?i)(?:'+pattern+r')', qualified) or re.search(r'(?i)(?:'+pattern+r')\s+(?:development\s+)?(?:experience|exp\.?)\s*[:=-]?\s*$', prefix):
                        specialty = name; break
                scope = re.fullmatch(r'(?i)([\w+#./ -]+?)\s+(?:experience|exp\.?)\s*[:=-]\s*', prefix)
                if not specialty and scope and not label.match(prefix):
                    specialty = scope[1].strip()
                if (not specialty and re.search(r'(?i)experience\s+(?:with|using)\b', tail)
                        and re.fullmatch(r'[A-Z][\w+#.-]*', qualified)):
                    specialty = qualified
            labelled = bool(heading and not before[heading.end():].strip())
            generic = bool(re.match(r'(?i)^(?:experience\b|(?:software|data|cloud|platform|infrastructure)\s+(?:development|engineering)|(?:delivering|building|leading|designing|developing|managing)\b)', qualified))
            generic = generic or bool(re.search(r'(?i)\bexperience\b', tail)) or bool(re.search(r'(?i)YOE',match[0]))
            standalone = not tail and bool(re.fullmatch(r'(?i)(?:(?:minimum|at least|a minimum of|required)\s+)?', prefix))
            if overall or specialty or labelled or generic or standalone:
                found = True
                rows.append({'years':years, 'specialty':specialty, 'passage':original.strip(), 'start':match.start(), 'end':match.end()})
        numeric_header = heading and re.match(r'\d', line[heading.end():])
        if not found and (matches or numeric_header) and re.search(r'(?i)\b(?:experience|exp|YOE)\b',line) and re.search(r'\d',line):
            warnings.append('Unrecognized JD experience wording; review: '+original.strip())
    return {'rows': rows, 'warnings':list(dict.fromkeys(warnings))}


def jd_durations(text):
    return jd_analysis(text)['rows']


def experience_profile(source, jd):
    analysis = jd_analysis(jd)
    source_rows, required_rows = durations(source), analysis['rows']
    source_total = max((r['years'] for r in source_rows if not r['specialty']), default=None)
    required_total = max((r['years'] for r in required_rows if not r['specialty']), default=None)
    overall = required_total if required_total is not None else source_total if source_total is not None else 9
    specialties = []
    warnings = list(analysis['warnings'])
    required_totals = sorted({r['years'] for r in required_rows if not r['specialty']})
    if len(required_totals) > 1:
        warnings.append('The JD supplies conflicting overall durations (' + ', '.join(map(str, required_totals)) +
                        ' years); the fictional career uses the higher explicit total.')
    for name, _ in SPECIALTIES:
        source_years = max((r['years'] for r in source_rows if r['specialty']==name), default=None)
        required = max((r['years'] for r in required_rows if r['specialty']==name), default=None)
        if source_years is None and required is None:
            continue
        value = required if required is not None else source_years
        if required is None and required_total is not None and value > overall:
            warnings.append(f"Source-only {name} duration exceeds the JD overall total; limited to {overall}+ years for consistency.")
            value = overall
        if value > overall:
            warnings.append(f"Specialty duration {value}+ years of {name} exceeds the supplied overall total; fictional overall total raised to match.")
            overall = value
        specialties.append({'label':name,'years':value,'required_years':required,'source_years':source_years})
    tools = [label for pattern,label in [(r'\bPython\b','Python'),(r'\bReact(?:\.js)?\b','React'),(r'\bSQL\b|\bPostgreSQL\b','SQL/PostgreSQL')] if re.search(pattern,jd,re.I)]
    return {'version':VERSION,'policy':'jd-first-overall-and-specialty',
            'overall_origin':'jd' if required_total is not None else 'source' if source_total is not None else 'default',
            'jd_requirements':required_rows, 'jd_parse_warnings':analysis['warnings'],
            'overall_years':overall,'source_overall_years':source_total,
            'required_overall_years':required_total,'specialties':specialties,'full_stack_tools':tools,'warnings':warnings}


def normalize_experience(text, profile):
    """Normalize generated duration spans only; exports never rewrite edited claims."""
    specialties = {s['label']:s['years'] for s in profile['specialties']}
    for row in reversed(durations(text)):
        years = specialties.get(row['specialty']) if row['specialty'] else profile['overall_years']
        if years is not None:
            text = text[:row['start']] + f"{years}+ years" + text[row['end']:]
    return text


def career_opening(headline, years, profile=None):
    prefix = f"{headline} with {years}+ years of experience"
    if profile and profile['specialties']:
        if re.search(r'(?i)full[\s-]*stack', headline):
            prefix += " in software development"
        prefix += ", including " + " and ".join(f"{s['years']}+ years of {s['label']}" for s in profile['specialties'])
        if re.search(r'(?i)full[\s-]*stack', headline) and any(s['label']=='full-stack development' for s in profile['specialties']) and profile.get('full_stack_tools'):
            prefix += " using " + (', '.join(profile['full_stack_tools'][:-1])+' and '+profile['full_stack_tools'][-1] if len(profile['full_stack_tools'])>1 else profile['full_stack_tools'][0])
        prefix += ";"
    return prefix


def review_experience(document):
    """Read edited section text; stale metadata cannot satisfy a requirement."""
    profile = document.get('experience_profile')
    if not profile:
        return None
    text = '\n'.join(s['text'] for s in document.get('sections',[]) if s['key'] in {'summary','projects','experience'})
    claims = durations(text)
    rows = []
    requirements = [('Overall software/career experience',None,profile.get('required_overall_years'))]
    requirements += [(s['label'],s['label'],s['required_years']) for s in profile['specialties'] if s.get('required_years') is not None]
    for label, specialty, required in requirements:
        stated = [r for r in claims if r['specialty']==specialty]
        values = sorted({r['years'] for r in stated})
        status = ('inconsistent' if len(values)>1 else 'missing' if not values else
                  'below requirement' if required is not None and values[0]<required else 'stated')
        rows.append({'label':label,'required_years':required,'stated_years':values,'status':status,
                     'passages':list(dict.fromkeys(r['passage'] for r in stated))})
    totals = [r['years'] for r in claims if r['specialty'] is None]
    warnings = list(profile.get('warnings',[]))
    if totals and any(r['specialty'] and r['years']>min(totals) for r in claims):
        warnings.append('An edited specialty duration exceeds the stated overall experience.')
    return {'version':VERSION,'rows':rows,'warnings':warnings,
            'scope':'Stated fictional durations only; employment history and eligibility are not verified.'}
