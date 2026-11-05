"""Immutable generation provenance and separate, local-only JD comparison."""
from __future__ import annotations

import copy
import hashlib
import re
from functools import lru_cache
from pathlib import Path

VERSION = 'jd-binding-1'


def fingerprint(jd):
    return hashlib.sha256(jd.strip().encode('utf-8')).hexdigest()


def snapshot(payload, jd, policy, fallback_id):
    return {'version':VERSION, 'job_id':payload.get('_job_id', fallback_id),
            'jd_sha256':fingerprint(jd), 'resume_path':str(Path(payload['resume']).resolve()),
            'project_count_policy':copy.deepcopy(policy)}


def warnings(document):
    jd = document.get('jd', '')
    context = document.get('generation_context')
    if context:
        if context.get('jd_sha256') != fingerprint(jd):
            return ['Saved JD differs from the submitted generation JD; regenerate to establish a consistent job association.']
        if context.get('project_count_policy') != document.get('project_count_policy'):
            return ['Saved project policy differs from the submitted generation target; review this draft.']
    else:
        passages = document.get('project_count_policy', {}).get('supporting_passages', [])
        if any(p not in jd for p in passages):
            return ['Historical draft contains JD evidence absent from its saved JD; the original JD cannot be reconstructed. Regenerate using the current JD.']
        policy = document.get('project_count_policy', {})
        if policy:
            from desktop.project_policy import select
            if policy.get('project_count') != select(jd)['project_count']:
                return ['Historical draft target differs from the current JD interpretation; saved text is preserved. Generate again to apply the corrected project count.']
    return []


@lru_cache(maxsize=8)
def _brief(jd, source, headline):
    from desktop.job_brief import build
    from desktop.project_profile import target_role
    return build(jd, source, target_role(jd, headline))


def assessment_view(document):
    """Never mutate saved career text, generation metadata or original brief."""
    if document.get('edition') != 'projects' or document.get('_assessment_view'):
        return document
    original = document.get('jd', '').strip()
    selected = document.get('comparison_jd', '').strip() or original
    view = dict(document)
    view['_assessment_view'] = True
    view['_generation_jd'] = original
    view['jd'] = selected
    from desktop.job_brief import VERSION as BRIEF_VERSION
    brief = document.get('job_brief')
    if not brief or brief.get('jd_sha256') != fingerprint(selected) or brief.get('version') != BRIEF_VERSION:
        header = next((s['text'].splitlines() for s in document.get('sections', []) if s['key']=='header'), [])
        brief = _brief(selected, document.get('source', ''), header[1] if len(header)>1 else 'Professional')
    view['job_brief'] = brief
    view['experience_profile'] = brief['experience']
    view['_jd_binding'] = {'version':VERSION, 'comparison':selected != original,
        'warnings':warnings(document), 'assessment_jd_sha256':fingerprint(selected),
        'assessment_project_policy':brief['project_count_policy'],
        'generation_verified':bool(document.get('generation_context')) and not warnings(document)}
    return view


def comparison_note(document):
    if document.get('comparison_jd', '').strip() and document['comparison_jd'].strip()!=document.get('jd', '').strip():
        from desktop.project_policy import select
        count = select(document['comparison_jd'])['project_count']
        return f'Comparing the current resume with a different JD. Generate again to create its {count}-project resume.'
    return ' '.join(warnings(document))


def validate_completed(document):
    context = document['generation_context']
    count = context['project_count_policy']['project_count']
    text = next((s['text'] for s in document['sections'] if s['key']=='projects'), '')
    if (warnings(document) or len(document['projects']) != count or len(document['roles']) != count
            or len(re.findall(r'^#### ', text, re.M)) != count
            or len(re.findall(r'^### Company Name:', text, re.M)) != count
            or any(len(p['bullets']) != 7 for p in document['projects'])):
        raise ValueError(f'Incomplete generation: expected {count} complete projects. Completed work remains recoverable.')
