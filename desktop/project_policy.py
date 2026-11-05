"""JD-only project tiers, independent of invented/source career totals."""
from desktop.project_experience import jd_analysis

VERSION = 'project-count-2'


def select(jd, experience=None):
    analysis = jd_analysis(jd) if experience is None else {'rows':experience['jd_requirements'], 'warnings':experience['jd_parse_warnings']}
    rows = [r for r in analysis['rows'] if not r['specialty']]
    totals = sorted({r['years'] for r in rows})
    years = max(totals) if totals else None
    count = 6 if years is not None and years >= 12 else 5 if years is not None and years >= 8 else 3
    return {'version': VERSION, 'tier': '12-plus' if count == 6 else '8-to-11' if count == 5 else 'standard',
            'project_count': count, 'jd_overall_years': years,
            'supporting_passages': list(dict.fromkeys(r['passage'] for r in rows)),
            'warnings': analysis['warnings'] + (['Conflicting JD overall experience requirements; selected the highest explicit total.'] if len(totals) > 1 else [])}


def expected_count(document):
    policy = document.get('project_count_policy', {})
    return policy.get('project_count', len(document.get('projects', [])) or 3)
