"""Adapt legacy proposal annotations to explicit IDs without promoting to gold."""
from copy import deepcopy
import re

from matching.normalizer import canonical, expand


def skill_spans(text, skills):
    """Resolve canonical terms to literal source spans, longest match first."""
    found = []
    for skill in skills:
        variants = expand(canonical(skill)) | {skill}
        for variant in variants:
            for hit in re.finditer(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", text, re.I):
                found.append((hit.start(), hit.end(), hit.group()))
    chosen = []
    for hit in sorted(set(found), key=lambda x: (-(x[1]-x[0]), x[0])):
        if not any(hit[0] < other[1] and other[0] < hit[1] for other in chosen):
            chosen.append(hit)
    return sorted(chosen)


def requirement_atoms(item):
    """Separate skill conjunctions; retain an OR group as one expectation.

    These are review adapters, not an assertion that arbitrary natural language
    can be proved atomic. Source phrases and unsplit responsibilities stay visible.
    """
    r = deepcopy(item)
    text = r['text']
    skills = r.get('canonical_skills', [])
    qualification = bool(re.search(r"\b(degree|bachelor|master|ph\.?d|certificat\w*|\d+\s*\+?\s*years?)\b", text, re.I))
    if qualification:
        r['type'] = 'qualification'
    elif r.get('type') == 'qualification' and skills:
        r['type'] = 'hard_skill'
    if re.search(r'\b(preferred|nice.to.have|optional|bonus)\b', text, re.I):
        r['must_have'] = False
    spans = skill_spans(text, skills)
    r.setdefault('logic', 'single')
    # Responsibilities are actions, not mere possession of their named tools.
    if r['type'] not in ('hard_skill', 'tool') or len(spans) < 2:
        return [r]
    gaps = [text[a[1]:b[0]].strip() for a,b in zip(spans, spans[1:])]
    is_or = all(re.fullmatch(r'[/,\s]*(?:or\s*)?[/,\s]*', gap, re.I) is not None for gap in gaps) and any('/' in gap or re.search(r'\bor\b', gap, re.I) for gap in gaps)
    # CI/CD and names containing '/' are single spans and cannot reach here.
    if is_or:
        r['logic'] = 'any'
        r['canonical_skills'] = [canonical(s[2]) for s in spans]
        return [r]
    # Parenthesized examples (Jenkins, GitHub Actions, etc.) do not make all
    # examples mandatory. Keep that source clause for the reviewer.
    examples = '(' in text[:spans[0][0]] and bool(re.search(r'\betc\.?|such as|e\.g\.', text, re.I))
    if not examples and all(re.fullmatch(r'[,\s&]*(?:and\s*)?[,\s&]*', gap, re.I) is not None for gap in gaps):
        return [{**r, 'text': s[2], 'canonical_skills': [canonical(s[2])], 'logic': 'single', 'source_text': text} for s in spans]
    return [r]


def explicit_skill_match(req, options):
    """Evidence for an isolated skill (or alternatives) must name that skill."""
    wanted = req.get('canonical_skills', [])
    hit_by_skill = {s: [f['key'] for f in options if f['type']=='skill' and canonical(f['text'])==canonical(s)] for s in wanted}
    hits = [s for s, keys in hit_by_skill.items() if keys]
    keys = list(dict.fromkeys(k for s in hits for k in hit_by_skill[s]))
    covered = bool(hits) if req.get('logic') == 'any' else len(hits)==len(wanted) and bool(wanted)
    status = 'covered' if covered else 'partial' if hits else 'missing'
    return {'fact_keys': keys, 'status': status, 'method': 'lexical' if keys else 'none', 'score': 1.0 if covered else 0.55 if hits else 0.0}


def prefill(seed, options, normalize=False):
    """One browser contract for proposals, saved gold, and resumable drafts."""
    seed = deepcopy(seed or {})
    options_by_key = {f['key']: f for f in options}
    source_facts = seed.get('facts', [])
    keys = seed.get('fact_keys')
    if keys is None:
        keys = []
        for f in source_facts:
            candidate = next((o['key'] for o in options if o['text']==f['text'] and o['context']==f.get('context', o['context'])), None)
            if candidate: keys.append(candidate)
    seed['fact_keys'] = keys or []
    id_to_key = {f'F{i:02d}': key for i,key in enumerate(seed['fact_keys'],1)}
    for f in source_facts:
        candidate = next((k for k in seed['fact_keys'] if options_by_key[k]['text']==f['text']), None)
        if candidate: id_to_key[f['fact_id']] = candidate
    old_matches = seed.get('matches', [])
    by_req = {m['req_id']: m for m in old_matches if m.get('req_id')}
    reqs, matches, notes = [], [], []
    for i, original in enumerate(seed.get('requirements', []),1):
        old_id = original.get('req_id', f'R{i:02d}')
        m = deepcopy(by_req.get(old_id, old_matches[i-1] if i<=len(old_matches) and not by_req else {}))
        if 'fact_keys' not in m:
            m['fact_keys'] = [id_to_key.get(fid, 'INVALID:'+fid) for fid in m.get('fact_ids', [])]
        atoms = requirement_atoms(original) if normalize else [original]
        for atom in atoms:
            new = {**atom, 'req_id': f'R{len(reqs)+1:02d}' if normalize else old_id}
            if normalize:
                skills = new.get('canonical_skills', [])
                supported = [s for s in skills if skill_spans(new['text'], [s])]
                if supported != skills:
                    notes.append(f"{new['req_id']}: omitted canonical terms without a literal or known alias in the JD phrase; verify the complete requirement text.")
                    new['canonical_skills'] = supported
            updated = deepcopy(m)
            if normalize and (len(atoms)>1 or new.get('logic')=='any' or new.get('type')!=original.get('type')):
                if new['type'] in ('hard_skill','tool') and new.get('canonical_skills'):
                    updated = explicit_skill_match(new, [o for o in options if o['key'] in seed['fact_keys']])
                notes.append(f"{new['req_id']}: checked skill classification and conjunction/alternative evidence.")
            updated.setdefault('status','missing'); updated.setdefault('method','none')
            if normalize and updated['status']!='missing' and not updated.get('fact_keys'):
                updated.update(status='missing',method='none',score=0.0)
                notes.append(f"{new['req_id']}: original match had no supporting fact; review evidence before changing from missing.")
            if normalize and updated['status']=='missing' and (updated.get('fact_keys') or updated['method']!='none'):
                updated['fact_keys']=[]; updated['method']='none'
                notes.append(f"{new['req_id']}: removed weak references from a missing match.")
            updated['req_id'] = new['req_id']
            updated.setdefault('score', None)
            reqs.append(new); matches.append(updated)
    seed.update(requirements=reqs, matches=matches)
    seed['prefill_notes'] = notes
    return seed
