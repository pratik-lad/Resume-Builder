"""Project Edition spelling-level coverage, separate from legacy semantic aliases.

These checks preserve named requirements; they do not certify implementation.
"""
from __future__ import annotations

import re
from functools import lru_cache

VERSION = 'explicit-skills-1'
NON_TOOL_ATOMS = set('and or with using including such as equivalent similar etc strong good average very required mandatory preferred optional skills skill experience years yoe knowledge familiarity communication collaboration leadership mentoring english india remote pune engineer developer architect manager professional responsibilities unit test define audit identify establish patching clear concise persuasive structured cost quality integrity rationale timelines'.split())

# Real spelling variants only. Generic parents (testing, SQL, containers, Git)
# must never satisfy a named child tool or operation.
SPELLINGS = {
    'pytest': r'pytest', 'SQLAlchemy': r'SQL\s*Alchemy',
    'Python 3': r'Python\s*3(?:\.\d+)*',
    'Docker': r'Docker', 'Kubernetes': r'Kubernetes|K8s',
    'Vue.js': r'Vue(?:\s*\.\s*js|\s*js)?', 'React.js': r'React(?:\s*\.\s*js|\s*js)?',
    'JavaScript': r'JavaScript', 'TypeScript': r'TypeScript',
    'Git Rebase': r'(?:Git\s+)?rebas(?:e|ed|es|ing)',
    'Git Cherry-Pick': r'(?:Git\s+)?cherry[\s-]*pick(?:ed|s|ing)?',
    'Merge Conflict Resolution': r'merge[\s-]+conflict(?:s|[\s-]+resolution)?|resolv\w*\s+merge\s+conflicts?',
    'Unit Testing': r'unit\s+(?:and\s+integration\s+)?test(?:s|ing)?',
    'Integration Testing': r'integration\s+test(?:s|ing)?',
    'Asynchronous Programming': r'async(?:hronous)?\s+programming|async\s*/\s*await|asynchronous',
    'CI/CD': r'CI\s*[/&-]\s*CD|continuous integration(?:\s+and\s+(?:continuous\s+)?delivery)?',
    'IaC': r'IaC|Infrastructure as Code',
    'Linux': r'Linux', 'ORM': r'ORM|object[\s-]+relational\s+mapping',
    'PostgreSQL': r'PostgreSQL|Postgres', 'MySQL': r'MySQL',
    'RabbitMQ': r'Rabbit\s*MQ', 'Kafka': r'(?:Apache\s+)?Kafka',
    'OAuth2': r'OAuth\s*2(?:\.0)?', 'JWT': r'JWT|JSON\s+Web\s+Tokens?',
    'FastAPI': r'Fast\s*API', 'GraphQL': r'Graph\s*QL',
    'GitHub Copilot': r'GitHub\s+Copilot', 'Cursor': r'Cursor',
    'GitHub Actions': r'GitHub\s+Actions', 'GitLab CI/CD': r'GitLab\s+CI(?:\s*/\s*CD)?',
    'AWS': r'AWS|Amazon Web Services', 'Azure': r'(?:Microsoft\s+)?Azure',
    'GCP': r'GCP|Google Cloud(?: Platform)?',
    'LLM': r'LLMs?|large language models?', 'GenAI': r'GenAI|generative AI',
    'RAG': r'RAG|retrieval[\s-]+augmented generation',
    'LWC': r'LWC|Lightning Web Components?',
    'MCP': r'MCP|Model Context Protocol',
    'API': r'APIs?', 'REST API': r'REST(?:ful)?\s+APIs?',
}


def _boundary(pattern):
    return r'(?<![\w+#])(?:' + pattern + r')(?![\w+#])'


@lru_cache(maxsize=1024)
def pattern(term):
    spelling = next((v for k, v in SPELLINGS.items() if k.casefold() == term.casefold()), None)
    return re.compile(_boundary(spelling or re.escape(term).replace(r'\ ', r'\s+')), re.I)


def present(text, term):
    return bool(pattern(term).search(text))


@lru_cache(maxsize=512)
def explicit_terms(text):
    """Supplement existing extraction and undo its lossy parent substitutions."""
    from desktop.evidence_quality import _skill_terms, NON_SKILLS
    terms = set(_skill_terms(text))
    # A mapped semantic parent is retained only when it was actually named.
    for term in list(terms):
        if not present(text, term):
            terms.remove(term)
    terms.update(name.casefold() for name in SPELLINGS if present(text, name))
    # Bare/listed product names need not be in a catalogue or use CamelCase.
    # Restrict this fallback to single product-shaped atoms, never sentences,
    # requirement fragments or logistical phrases.
    chunks=[]
    for item in re.split(r',|;|/|\s+\bor\b\s+|\s+\band\b\s+', text, flags=re.I):
        item = re.sub(r'(?i)^(?:(?:hands.on\s+)?(?:experience|familiarity|proficiency|knowledge)\s+(?:with|in|of)|using|including|tools?|technologies|skills)\s*:?\s+', '', item.strip(' \t-*•()[]').rstrip('.'))
        item = re.sub(r'(?i)\s*\((?:preferred|optional)\)\s*$', '', item)
        if item:chunks.append(item)
    atom=lambda item: bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.+#-]{1,39}',item))
    # Unknown bare terms are safe to retain in compact skill lists. Do not
    # harvest adjectives or verbs from the tail of long responsibility prose.
    compact = bool(chunks) and all(atom(item) or (len(item.split()) <= 4 and ':' not in item
                         and any(present(item,known) for known in terms)) for item in chunks)
    if compact:
        for item in chunks:
            if atom(item) and item.casefold() not in NON_TOOL_ATOMS | NON_SKILLS:
                terms.add(item.casefold())
    # A versioned language remains explicit without two redundant language items.
    if 'python 3' in terms:
        terms.discard('python')
    if 'react.js' in terms:
        terms.discard('react')
    if 'vue.js' in terms:
        terms.discard('vue')
    if 'git rebase' in terms:
        terms.discard('rebase')
    if 'git cherry-pick' in terms:
        terms.discard('cherry-pick')
    if 'github' in terms and not re.search(r'(?i)\bGitHub\b(?!\s+(?:Copilot|Actions))',text):
        terms.discard('github')
    # ORM is a concept as well as SQLAlchemy's category, never its substitute.
    return tuple(sorted(terms))


def named_rows(brief):
    return [r for r in brief.get('requirements', [])
            if r['kind'] in {'technology', 'capability', 'knowledge'}]


def terms_by_priority(brief, required):
    return sorted({t for r in named_rows(brief) if r['required'] == required for t in r['terms']})


# Compact evidence contracts are attached to existing responsibility slots, not
# emitted as canned project prose. Only terms actually owned by the project apply.
MECHANISMS = [
    ('python 3', 1, 'Python 3 service implementation'),
    ('pytest', 2, 'pytest fixtures, mocks and failure assertions'),
    ('unit testing', 2, 'unit tests for handlers and services'),
    ('integration testing', 2, 'integration tests across API/database boundaries'),
    ('docker', 2, 'Docker image build and release validation'),
    ('kubernetes', 4, 'Kubernetes workload deployment and health checks'),
    ('ci/cd', 4, 'CI/CD build, test, deployment and rollback gates'),
    ('linux', 6, 'Linux service/log diagnostics and recovery'),
    ('sqlalchemy', 1, 'SQLAlchemy ORM sessions and transaction rollback'),
    ('git rebase', 5, 'Git rebase with review and validation'),
    ('git cherry-pick', 5, 'Git cherry-pick for reviewed release fixes'),
    ('merge conflict resolution', 5, 'merge conflict resolution followed by tests'),
]


def evidence_slots(role):
    from desktop.requirement_ledger import alternative_groups
    result = {}
    for row in role.get('assigned_requirements', []):
        if not row['required']:
            continue
        groups = alternative_groups(row['text'], row['terms'])
        options = {t for group in groups for t in group}
        for term, slot, mechanism in MECHANISMS:
            if term in row['terms'] and term not in options:
                result.setdefault(slot, []).append(mechanism)
    return {str(slot): list(dict.fromkeys(items)) for slot, items in result.items()}
