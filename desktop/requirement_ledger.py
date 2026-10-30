"""Auditable requirement-to-edited-passage mapping, separate from keyword counts."""
import re
from html import escape

VERSION = 'requirements-3'


def alternatives(text):
    return bool(re.search(r'(?i)\bor (?:equivalent|similar)\b|\bsuch as\b|\bfor example\b|\be\.g\.|\bor\b', text))


def alternative_groups(text, terms):
    """Examples are options; required wording outside the example remains required."""
    spans=[]
    for match in re.finditer(r'\(([^)]*\bor (?:equivalent|similar)\b[^)]*)\)',text,re.I):
        spans.append(match[1])
    example=re.search(r'(?i)\b(?:such as|for example|e\.g\.)\s+(.+?)(?=,?\s+etc\.?|;|$)',text)
    if example:spans.append(example[1])
    groups=[]
    for span in spans:
        group=[t for t in terms if re.search(r'(?i)(?<!\w)'+re.escape(t)+r'(?!\w)',span)]
        if group and group not in groups:groups.append(group)
    if not spans and re.search(r'(?i)\bor\b',text):
        from desktop.skill_coverage import pattern
        for clause in re.split(r'(?i);|\bplus\b|\bas well as\b|,\s*(?:and|with|including)\b',text):
            if not re.search(r'(?i)\bor\b',clause):continue
            hits=sorted((m.start(),m.end(),term) for term in terms for m in pattern(term).finditer(clause))
            # Only punctuation/OR connects a list; "testing using pytest"
            # keeps testing as a core requirement outside the tool options.
            chain=[];has_or=False
            def emit():
                group=list(dict.fromkeys(t for _,_,t in chain))
                if has_or and group and group not in groups:groups.append(group)
            for hit in hits:
                if chain:
                    between=clause[chain[-1][1]:hit[0]]
                    if not re.fullmatch(r'(?i)\s*[,/()\s]*(?:or\s*)?[,/()\s]*',between):
                        emit();chain=[];has_or=False
                    else:has_or=has_or or bool(re.search(r'(?i)\bor\b',between))
                chain.append(hit)
            has_or=has_or or bool(chain and re.search(r'(?i)^\s*[,()\s]*or (?:equivalent|similar)\b',clause[chain[-1][1]:]))
            emit()
    return groups


def term_present(text, term):
    from desktop.skill_coverage import present
    aliases={'llms':['LLM','LLMs','large language models'], 'llm':['LLM','LLMs','large language models'],
             'rag':['RAG','retrieval-augmented generation'], 'rag concepts':['RAG','retrieval-augmented generation'],
             'genai':['GenAI','generative AI'], 'genai applications':['GenAI','generative AI'],
             'react':['React','React.js','ReactJS'], 'api integration':['API integration','integrated API','integrated REST','integrated FastAPI'],
             'api':['API','APIs','FastAPI','endpoints'], 'database':['database','databases','PostgreSQL','MySQL','SQL','MongoDB'],
             'unit testing':['unit test','unit tests','unit testing','pytest','Jest','JUnit','NUnit'],
             'testing':['testing','tested','unit test','integration test','pytest','Jest','JUnit','NUnit']}
    if term.casefold()=='code quality':
        return bool(re.search(r'(?i)code review|reviewed.{0,25}code|\blint|style.{0,35}rules|Sonar',text))
    if term.casefold()=='api integration' and re.search(r'(?i)\b(?:integrat|connect)\w*.{0,70}\b(?:APIs?|FastAPI|endpoints?)\b',text):return True
    return any(present(text, value) for value in aliases.get(term.casefold(),[term]))


def report(document):
    from desktop.job_brief import build, words
    from desktop.quality import contains_skill
    brief = document.get('job_brief') or build(document.get('jd',''), '', '')
    passages = []
    project = ''
    all_text = '\n'.join(s['text'] for s in document.get('sections',[]))
    for section in document.get('sections',[]):
        if section['key'] != 'projects': continue
        number = 0
        for line in section['text'].splitlines():
            if line.startswith('#### '): project=line[5:]
            if line.startswith('- '):
                number += 1
                passages.append({'project':project,'text':line[2:],'anchor':f'projects-bullet-{number}'})
    rows=[]
    for requirement in brief['requirements']:
        terms=requirement.get('terms',[])
        is_alternative=alternatives(requirement['text'])
        option_groups=alternative_groups(requirement['text'], terms)
        option_terms={t for g in option_groups for t in g}
        core_terms=set(terms)-option_terms
        evidence=[]
        covered=set()
        anchors=words(requirement['text']) - {'proficiency','familiarity','exposure','concepts','practices','capable','including'}
        for passage in passages:
            text=passage['text']
            # A token mention alone does not establish implementation.
            mechanism=bool(re.search(r'(?i)\b(using|via|through|with|by|into|against)\b',text))
            action=bool(re.search(r'(?i)\b(built|developed|implemented|designed|integrated|configured|secured|automated|tested|evaluated|validated|deployed|maintained|reviewed|resolved|documented|coordinated|led|established|optimized|mapped|authored|enforced|diagnosed|supported|orchestrated|delivered|owned|conducted|collaborated|used|generated)\b',text))
            action=action or bool(re.search(r'(?i)\b(?:is|are|was|were)\s+(?:ingested|processed|validated|configured|integrated|deployed|secured|tested|evaluated)\b',' '.join(text.split()[:9])))
            matched=[t for t in terms if term_present(text,t)]
            if len(text.split())>=12 and mechanism and action and (matched or not terms and len(anchors & words(text)) >= min(3,len(anchors)) and anchors):
                evidence.append({**passage,'matched_terms':matched})
                covered.update(matched)
        keyword_hits=[t for t in terms if term_present(all_text,t)]
        if requirement['kind'] in {'qualification','logistics','knowledge'}:
            status='review separately'
        elif terms:
            complete=core_terms<=covered and all(any(t in covered for t in group) for group in option_groups)
            status='supported' if complete else 'partial' if evidence else 'missing'
        else:
            # Unknown capabilities require review, even when lexical anchors match.
            status='partial' if evidence else 'missing'
        rows.append({**requirement,'alternatives':is_alternative,'status':status,
                     'keyword_hits':keyword_hits,'evidence':evidence,
                     'alternative_groups':option_groups,
                     'missing_terms':[t for t in core_terms if t not in covered] + ['one of: '+', '.join(g) for g in option_groups if not any(t in covered for t in g)]})
    return {'version':VERSION,'rows':rows,'scope':'Local passage matching supports review; it does not certify technical correctness or an external ATS score.'}


def html(result):
    rows=[]
    for row in result['rows']:
        links='<br>'.join('<a href="#'+escape(p['anchor'],quote=True)+'">'+escape(p['project'])+'</a>: '+escape(p['text']) for p in row['evidence'])
        rows.append('<tr><td>'+escape(row['id'])+'</td><td>'+('Mandatory' if row['required'] else 'Preferred')+'</td><td>'+escape(row.get('source_passage',row['text']))+'</td><td>'+escape(row['status'])+'</td><td>'+links+'</td></tr>')
    return '<h2>Complete JD requirement ledger</h2><p>'+escape(result['scope'])+'</p><table><tr><th>ID</th><th>Priority</th><th>JD passage</th><th>Evidence status</th><th>Implementation passages</th></tr>'+''.join(rows)+'</table>'
