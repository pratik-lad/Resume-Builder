"""Verified credential titles and deterministic, JD-ranked offline selection.

Possession remains fictional. The catalogue verifies names, not candidate claims.
No network access is required at runtime; unrecognised qualifications are reported.
"""
from __future__ import annotations

import hashlib
import re

VERSION = 'credentials-1'
REVIEWED = '2026-10-26'


def credential(title, trigger, url, aliases=(), group=None, status='active'):
    return {'title': title, 'trigger': trigger, 'url': url, 'aliases': list(aliases),
            'group': group or title, 'status': status, 'reviewed': REVIEWED}


CATALOGUE = [
    credential('Salesforce Certified Application Architect', r'\bSalesforce\b', 'https://trailhead.salesforce.com/credentials/applicationarchitect', ['Salesforce Application Architect', 'Application Architect']),
    credential('Salesforce Certified System Architect', r'\bSalesforce\b', 'https://trailhead.salesforce.com/credentials/systemarchitect', ['Salesforce System Architect', 'System Architect']),
    credential('Salesforce Certified Technical Architect', r'\bSalesforce\b', 'https://trailhead.salesforce.com/credentials/technicalarchitect', ['CTA']),
    credential('Salesforce Certified Revenue Management Consultant', r'Salesforce.{0,100}(?:CPQ|Revenue)|(?:CPQ|Revenue).{0,100}Salesforce', 'https://trailhead.salesforce.com/credentials/revenuemanagementconsultant', ['Revenue Cloud Consultant', 'Revenue Management Consultant']),
    credential('AWS Certified Solutions Architect - Associate', r'\bAWS\b|Amazon|\bEKS\b', 'https://aws.amazon.com/certification/certified-solutions-architect-associate/', ['AWS Solutions Architect'], 'aws-architecture'),
    credential('AWS Certified Solutions Architect - Professional', r'\bAWS\b|Amazon', 'https://aws.amazon.com/certification/certified-solutions-architect-professional/', [], 'aws-architecture'),
    credential('AWS Certified DevOps Engineer - Professional', r'\bAWS\b|\bEKS\b', 'https://aws.amazon.com/certification/certified-devops-engineer-professional/', ['AWS Certified DevOps Engineer']),
    credential('AWS Certified Developer - Associate', r'\bAWS\b', 'https://aws.amazon.com/certification/certified-developer-associate/'),
    credential('AWS Certified Data Engineer - Associate', r'(?:AWS|Amazon).{0,100}(?:data|analytics)|(?:data engineer).{0,100}AWS', 'https://aws.amazon.com/certification/certified-data-engineer-associate/'),
    credential('Microsoft Certified: Azure Solutions Architect Expert', r'\bAzure\b', 'https://learn.microsoft.com/credentials/certifications/azure-solutions-architect/'),
    credential('Microsoft Certified: DevOps Engineer Expert', r'(?=.*\bAzure\b)(?=.*(?:DevOps|CI/CD|deploy|release|infrastructure))', 'https://learn.microsoft.com/credentials/certifications/devops-engineer/'),
    credential('Microsoft Certified: Azure AI Cloud Developer Associate', r'(?=.*\bAzure\b)(?=.*(?:\bAI\b|GenAI|LLM|application|developer|development|FastAPI|Python))', 'https://learn.microsoft.com/credentials/certifications/azure-ai-cloud-developer-associate/', ['Azure AI Cloud Developer']),
    credential('Microsoft Certified: Azure AI Engineer Associate', r'\bAzure\b', 'https://learn.microsoft.com/credentials/support/credential-retirement', ['AI-102'], status='retired'),
    credential('Microsoft Certified: Azure Developer Associate', r'\bAzure\b', 'https://learn.microsoft.com/credentials/support/credential-retirement', ['AZ-204'], status='retired'),
    credential('Databricks Certified Data Engineer Professional', r'Databricks|Spark|Delta Lake', 'https://www.databricks.com/learn/certification/data-engineer-professional', [], 'databricks-data'),
    credential('Databricks Certified Data Engineer Associate', r'Databricks|Spark|Delta Lake', 'https://www.databricks.com/learn/certification/data-engineer-associate', [], 'databricks-data'),
    credential('Databricks Certified Machine Learning Professional', r'Databricks.{0,120}(?:machine learning|MLflow)|(?:MLflow|machine learning).{0,120}Databricks', 'https://www.databricks.com/learn/certification/machine-learning-professional'),
    credential('HashiCorp Certified: Terraform Associate', r'Terraform|\bIaC\b|infrastructure as code', 'https://developer.hashicorp.com/certifications/infrastructure-automation', ['Terraform Associate']),
    credential('Certified Kubernetes Administrator (CKA)', r'Kubernetes|\bEKS\b|\bAKS\b|\bGKE\b|Helm', 'https://www.cncf.io/training/certification/cka/', ['CKA']),
    credential('Certified Kubernetes Application Developer (CKAD)', r'Kubernetes|\bEKS\b|\bAKS\b|\bGKE\b', 'https://www.cncf.io/training/certification/ckad/', ['CKAD']),
    credential('Google Cloud Professional Cloud Architect', r'Google Cloud|\bGCP\b', 'https://cloud.google.com/learn/certification/cloud-architect'),
    credential('Google Cloud Professional Data Engineer', r'Google Cloud|\bGCP\b|BigQuery', 'https://cloud.google.com/learn/certification/data-engineer'),
    credential('PCAP - Certified Associate Python Programmer', r'\bPython\b|FastAPI|Flask', 'https://pythoninstitute.org/pcap', ['PCAP'], 'python-language'),
    credential('PCPP1 - Certified Professional Python Programmer Level 1', r'\bPython\b|FastAPI|Flask', 'https://pythoninstitute.org/pcpp1', ['PCPP1'], 'python-language'),
    credential('Oracle Certified Professional: Java SE 21 Developer', r'\bJava\b|Spring Boot', 'https://mylearn.oracle.com/ou/exam/java-se-21-developer-professional-1z0-830/88323/139080/220555', ['Java SE 21 Developer Professional']),
    credential('ISTQB Certified Tester Foundation Level (CTFL)', r'\bQA\b|test automation|software testing|quality assurance|Selenium|Playwright', 'https://istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/', ['ISTQB', 'CTFL']),
    credential('ISTQB Certified Tester Advanced Level Test Automation Engineering (CTAL-TAE)', r'test automation|Selenium|Playwright|\bQA\b', 'https://www.istqb.org/certifications/test-automation-engineer', ['CTAL-TAE']),
]


def mentioned(text, alias):
    return bool(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text, re.I))


def select(jd, seed=0, requirements=None):
    if requirements is None:
        from desktop.project_rules import classify
        requirements = classify(jd)
    explicit_lines = [r for r in requirements if r['kind'] == 'qualification'
                      and not re.search(r'(?i)\byears?\b|\bdegree\b|bachelor|master',r['text'])
                      and (re.search(r'(?i)certif|credential|\bexam\b',r['text'])
                           or any(mentioned(r['text'],a) for c in CATALOGUE for a in [c['title'],*c['aliases']]))]
    ranked, warnings, matched = [], [], set()
    for entry in CATALOGUE:
        if not re.search(entry['trigger'], jd, re.I | re.S):
            continue
        hits = [r for r in explicit_lines if any(mentioned(r['text'], a) for a in [entry['title'], *entry['aliases']])]
        if entry['status'] != 'active' and not hits:
            continue
        score = 100 if any(r['required'] for r in hits) else 80 if hits else 10
        # Explicit requirement priority always dominates optional variety.
        if not hits:
            title_words = set(re.findall(r'[a-z]+', entry['title'].lower())) - {'certified', 'associate', 'professional', 'microsoft', 'google', 'cloud'}
            score += sum(bool(re.search(r'(?i)\b' + re.escape(w) + r'\b', jd)) for w in title_words) * 3
        tie = hashlib.sha256((str(seed) + entry['title']).encode()).hexdigest()
        ranked.append((score, tie, entry, hits))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    selected, groups = [], set()
    explicit_count = sum(bool(hits) for _, _, _, hits in ranked)
    target = min(4, max(3, explicit_count))
    for score, _, entry, hits in ranked:
        if len(selected) >= target:
            break
        if entry['group'] in groups and not hits:
            continue
        groups.add(entry['group'])
        selected.append({k: entry[k] for k in ('title', 'url', 'status', 'reviewed')})
        selected[-1].update(priority='required' if any(r['required'] for r in hits) else 'preferred' if hits else 'relevant',
                            requirement_ids=[r['id'] for r in hits])
        matched.update(r['id'] for r in hits)
        if entry['status'] != 'active':
            warnings.append('Explicit JD credential is retired; review historical credential status: ' + entry['title'])
    for row in explicit_lines:
        if row['id'] not in matched:
            warnings.append('Credential requirement needs manual review; no selected exact catalogue match: ' + row['text'])
    if len(selected) < 2:
        warnings.append('Fewer than two relevant recognised credentials were found; unrelated titles were not added.')
    return {'version': VERSION, 'method': 'offline-ranked-catalogue', 'selected': selected, 'warnings': warnings,
            'possession': 'fictional', 'reviewed': REVIEWED}


def candidates(jd):
    return [c['title'] for c in CATALOGUE if c['status'] == 'active' and re.search(c['trigger'], jd, re.I | re.S)]
