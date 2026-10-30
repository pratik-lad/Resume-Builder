"""Canonical grouped layout and output masking for the separate Project Edition."""
from __future__ import annotations
import copy
import re
from html import escape
from desktop.quality import date_free_document, without_dates, project_markdown

TITLE = "Relevant Project Experience"
CLIENT = "Confidential client"
COMPANY = "#Confidential"
COMPANY_LABEL_VERSION = "company-confidential-2"
COMPANY_LABEL_VERSIONS = {"company-confidential-1", COMPANY_LABEL_VERSION}


def report_shell(document):
    if document.get("template_version") == "reference-2":
        from desktop.reference_layout import html
        return html(document, include_jd=True)
    """Render edited section text safely; never expose raw Markdown as HTML."""
    def rich(value):
        return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',escape(value))
    rows=[]
    for section in document.get('sections',[]):
        rows.append('<section class="resume-section">')
        if section['key']!='header':rows.append('<h2>'+escape(section['title'])+'</h2>')
        in_list=False
        for index,line in enumerate(section['text'].splitlines()):
            if not line.strip():continue
            bullet=line.startswith('- ')
            if in_list and not bullet:rows.append('</ul>');in_list=False
            if bullet:
                if not in_list:rows.append('<ul>');in_list=True
                rows.append('<li>'+rich(line[2:])+'</li>')
            elif section['key']=='header' and index==0:rows.append('<h1>'+rich(line)+'</h1>')
            elif line.startswith('#### '):rows.append('<h4>'+rich(line[5:])+'</h4>')
            elif line.startswith('### '):rows.append('<h3>'+rich(line[4:])+'</h3>')
            else:
                value=rich(line)
                if section['key']=='projects' and re.match(r'^(Client|Company name|Role|Target Role|Contribution|Designation|Platform|Tools|Team Size):',line):
                    label,body=value.split(':',1);value='<strong>'+label+':</strong>'+body
                rows.append('<p>'+value+'</p>')
        if in_list:rows.append('</ul>')
        rows.append('</section>')
    style="body{max-width:960px;margin:32px auto;padding:0 20px;font:16px/1.5 Arial,sans-serif;color:#172b3a}h1,h2,h3,h4{color:#17324d}h2{border-bottom:1px solid #cbd5df}h3,h4{margin-bottom:6px}p{margin:5px 0}li{margin:6px 0}table{width:100%;border-collapse:collapse;margin:16px 0}th,td{border:1px solid #d8e0e8;padding:8px;text-align:left;vertical-align:top}pre{white-space:pre-wrap}"
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Resume and implementation report</title><style>'+style+'</style></head><body>'+''.join(rows)+
            '<h2>Original job description</h2><pre>'+escape(document.get('jd',''))+'</pre></body></html>')

def mask_text(text, aliases=(), company_label=False):
    placeholder = COMPANY if company_label else CLIENT
    text = re.sub(r"(?i)#confidentail", placeholder, text)
    # Do not consume a newline for an empty field: the next Role line is not
    # a company name and must remain intact when the user edits a draft.
    discovered = re.findall(r"(?im)^(?:Client|Company name):[ \t]*([^\r\n]+)", text)
    names = {v.strip() for v in [*aliases, *discovered] if isinstance(v, str) and v.strip()
             and v.strip().casefold() not in {CLIENT.casefold(), COMPANY.casefold()}}
    from matching import technology_catalog
    result = []
    for line in without_dates(text).splitlines():
        if re.match(r"(?i)^(?:Client|Company name):", line):
            label = ("Company Name: " if line.startswith("Company Name:") else "Company name: ") if company_label else "Client: "
            result.append(label + placeholder)
            continue
        # Company headings, titles and named technologies must remain visible.
        if line.startswith("#") or re.match(r"(?i)^(?:Designation|Title|Tools|Platform|Operating System):", line):
            result.append(line)
            continue
        for name in sorted(names, key=len, reverse=True):
            if technology_catalog.entry_for(name):
                pattern = r"(?i)(\b(?:client|customer)(?: company)?(?: named| called)?\s+)" + re.escape(name) + r"(?!\w)"
                line = re.sub(pattern, lambda m: m[1] + placeholder, line)
            else:
                line = re.sub(r"(?i)(?<!\w)" + re.escape(name) + r"(?!\w)", placeholder, line)
        result.append(line)
    return "\n".join(result)

def block_text(block, hide_employer=False):
    project = block["project"]
    if "bullets" in project:
        text = "### " + project["name"] + "\n" + project["description"] + "\n\n" + "\n".join([
            *([] if hide_employer else ["Company Name: " + COMPANY if project.get('client') == COMPANY else "Client: " + CLIENT]),
            *(["Role: " + project['target_role']] if project.get('target_role') else []),
            *(["Contribution: " + project['contribution']] if project.get('contribution') else []),
            "Platform: " + project["platform"], "Tools: " + project["tools"],
            "Team Size: " + project["team_size"], "",
            *((["##### Technical Responsibilities"] + ["- "+b for b in project["bullets"][:5]] +
               ["##### Functional Responsibilities"] + ["- "+b for b in project["bullets"][5:]]) if len(project["bullets"])==7 else ["- "+b for b in project["bullets"]])])
    else:
        text = project_markdown(project)
    # One parent employer header and one nested project title, not two sections.
    text = re.sub(r"^### ", "#### ", text, count=1)
    employer = "Company Name: " + COMPANY if hide_employer else block["employer"]
    return "### " + employer + "\nDesignation: " + block["designation"] + "\n\n" + text

def assemble(document, aliases=()):
    result = date_free_document(document)
    company_label = result.get('client_label_version') in COMPANY_LABEL_VERSIONS
    hide_employer = result.get('client_label_version') == COMPANY_LABEL_VERSION
    client = COMPANY if company_label else CLIENT
    roles, projects = result["roles"], result["projects"]
    aliases = tuple(aliases) + (tuple(role['employer'] for role in roles) if hide_employer else ())
    blocks = []
    for role, project in zip(roles, projects):
        assert project["role_id"] == role["role_id"]
        project["client"] = client
        for key, value in list(project.items()):
            if key in {"employer", "role", "role_id", "name", "tools", "platform"}:
                continue
            if isinstance(value, str):
                project[key] = mask_text(value, aliases, company_label)
            elif isinstance(value, list):
                project[key] = [mask_text(v, aliases, company_label) for v in value]
        blocks.append({"role_id": role["role_id"], "employer": role["employer"],
                       "designation": role["title"], "project": copy.deepcopy(project)})
    section = {"key": "projects", "title": TITLE,
               "text": mask_text("\n\n".join(block_text(b, hide_employer) for b in blocks), aliases, company_label)}
    result["sections"] = [s for s in result["sections"] if s["key"] not in {"experience", "projects"}]
    result["sections"].insert(4 if result.get("template_version") else 3, section)
    if hide_employer:
        # Remove generated employer names even if the model repeats one in a
        # project title or summary. Preserve named technologies and old drafts.
        from matching import technology_catalog
        for name in sorted({r['employer'].strip() for r in roles if r.get('employer')}, key=len, reverse=True):
            if technology_catalog.entry_for(name):
                continue
            pattern = r'(?i)(?<!\w)' + re.escape(name) + r'(?!\w)'
            for part in result['sections']:
                if part['key'] in {'summary', 'projects'}:
                    part['text'] = re.sub(pattern, COMPANY, part['text'])
    result.update(schema_version=6 if result.get("profile_version") else 5 if result.get("quality_version") else 4, edition="projects", experience_blocks=blocks)
    from desktop.draft import requirements
    from desktop.quality import evidence_report
    result["evidence"] = evidence_report(result, requirements(result["jd"]))
    return result

def sanitize(document):
    result = date_free_document(document)
    if result.get("edition") != "projects":
        return result
    company_label = result.get('client_label_version') in COMPANY_LABEL_VERSIONS
    client = COMPANY if company_label else CLIENT
    for section in result.get("sections", []):
        if section["key"] == "projects":
            if result.get('client_label_version') == COMPANY_LABEL_VERSION:
                # Remove only the duplicated default row beneath a matching
                # confidential heading; retain other edited rows and old drafts.
                lines = []
                confidential_heading = False
                for line in section['text'].splitlines():
                    if line.startswith('### '):
                        confidential_heading = bool(re.fullmatch(r'###\s+Company Name:\s*#Confidential\s*', line, re.I))
                    if confidential_heading and re.fullmatch(r'Company Name:\s*#Confidential\s*', line, re.I):
                        continue
                    lines.append(line)
                section['text'] = '\n'.join(lines)
            section.update(title=TITLE, text=mask_text(section["text"], company_label=company_label))
        if section["key"] == "skills":
            section["text"] = re.sub(r"(?im)^.*Additional Capabilities\s*:.*(?:\n|$)", "", section["text"])
    for project in result.get("projects", []):
        project["client"] = client
    for block in result.get("experience_blocks", []):
        block["project"]["client"] = client
    # Full evidence analysis belongs to generation/export workers, not the GUI
    # restore/preview path. Export always recomputes it from current section text.
    return result
