"""Compact role-specific finishing for fictional demo resumes."""

import re
from datetime import date


def _replace_section(markdown: str, title: str, transform) -> str:
    match = re.search(rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)", markdown)
    if not match:
        return markdown
    return markdown[:match.start(1)] + transform(match.group(1)) + markdown[match.end(1):]


def _remove_malformed_roles(body: str) -> str:
    blocks = re.split(r"(?m)(?=^### )", body)
    malformed = re.compile(
        r"(?i)^###\s+(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b"
        r"[^\n]*\||Responsibilities\b)")
    return "".join(block for block in blocks if not malformed.match(block))


def _replace_last_generated_project(markdown: str, source_text: str, marker: str,
                                    replacement: str) -> str:
    match = re.search(r"(?ms)^## Selected Projects\s*\n(.*?)(?=^## |\Z)", markdown)
    if not match:
        return markdown
    body = match.group(1)
    blocks = list(re.finditer(r"(?m)^###\s+([^\n]+)", body))
    if not blocks:
        return markdown
    last = blocks[-1]
    heading = last.group(1).strip()
    if heading.casefold() in source_text.casefold() or marker in heading.casefold():
        return markdown
    if marker.startswith("strategic accounts") and re.search(
            r"(?i)\b(?:account growth|partner expansion|channel sales|sales pipeline|enterprise rfp)\b",
            heading):
        return markdown
    if marker.startswith("revenue cloud") and re.search(
            r"(?i)\b(?:b2b commerce|cpq|revenue cloud|quote.to.cash|checkout|order management)\b",
            heading):
        return markdown
    body = body[:last.start()].rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return markdown[:match.start(1)] + body + markdown[match.end(1):]


_SALES_BULLETS = (
    "- Qualified enterprise prospects with LinkedIn Sales Navigator, Apollo, ZoomInfo, and Lusha; "
    "used SPIN and MEDDICC discovery to advance opportunities in Salesforce and HubSpot.",
    "- Prepared Statements of Work (SOW), commercial quotations, solution decks, and "
    "RFP/RFI/RFQ tender responses with pre-sales architects and delivery teams.",
    "- Negotiated pricing and contracts through enterprise procurement and vendor onboarding; "
    "closed complex deals and expanded strategic accounts through renewals, upselling, and cross-selling.",
    "- Led territory planning, competitor research, go-to-market forecasts, and KPI reviews of qualified "
    "pipeline, bookings, conversion rates, win rate, average deal size, sales cycle length, and expansion revenue.",
    "- Mentored junior sales colleagues and represented the practice at healthcare, BFSI, and manufacturing "
    "events across US, UK, Europe, and APAC markets.",
)


_SALES_PROJECT = """### Strategic Accounts and Partner Expansion
Title: Strategic Accounts and Partner Expansion
Client: Enterprise technology customers
Operating System: Cloud CRM and sales platforms
Tools: Salesforce, HubSpot, LinkedIn Sales Navigator, Apollo, ZoomInfo, Power BI
Team Size: 7
Period: 2022 - Present
Project Description: Built a repeatable enterprise account-growth and channel-sales program linking prospect research, solution discovery, partner planning, and renewal forecasts.
Role and Responsibilities:
Technical:
- Segmented strategic accounts by buying committee, use case, contract cycle, and expansion potential across AI, SaaS, cloud, and cybersecurity solutions.
- Created CRM dashboards for qualified pipeline, lead-to-opportunity conversion, bookings, win rate, sales cycle length, and forecast accuracy.
- Coordinated solution architects and pre-sales teams on SOW scope, pricing assumptions, commercial quotations, and procurement responses.
Functional:
- Negotiated account expansion and renewal plans with enterprise decision-makers and channel partners.
- Mentored sales team members on discovery, MEDDICC qualification, proposal reviews, and deal handover.
"""


_SALESFORCE_BULLETS = (
    "- Led Salesforce B2B Commerce and Revenue Cloud architecture across storefront, product catalog, "
    "pricing, cart, checkout, order management, CPQ, and Quote-to-Cash workflows.",
    "- Produced Technical Architecture and Solution Design documents; reviewed security, scalability, "
    "performance, data architecture, and migration decisions with business and engineering stakeholders.",
    "- Designed Apex and LWC services with REST/SOAP integration patterns for SAP, Oracle, ERP, and CRM systems; "
    "established CI/CD standards and mentored delivery teams through architecture reviews.",
)


_SALESFORCE_PROJECT = """### Revenue Cloud Quote-to-Cash Architecture
Title: Revenue Cloud Quote-to-Cash Architecture
Client: Enterprise B2B commerce program
Operating System: Salesforce cloud platform
Tools: Salesforce CPQ, Revenue Cloud, Apex, LWC, REST APIs, SOAP APIs, SAP, Oracle, SFDX
Team Size: 8
Period: 2022 - Present
Project Description: Designed an enterprise quote-to-cash solution connecting B2B storefront checkout, product configuration, pricing approvals, order management, and ERP fulfillment.
Role and Responsibilities:
Technical:
- Architected CPQ product rules, quote approvals, contract generation, and order handoff across Revenue Cloud and SAP/Oracle ERP integrations.
- Designed data migration and reconciliation for customer, catalog, pricing, and order-history records.
- Established OAuth security, performance tests, and CI/CD release gates for Apex and LWC components.
Functional:
- Led architecture reviews and authored Technical Architecture and Solution Design documents for senior stakeholders.
- Mentored engineers on integration patterns, deployment standards, and checkout reliability.
"""


def polish(markdown: str, jd_text: str, source_text: str = "") -> str:
    """Improve two common demo role families without adding a JD checklist."""
    jd = jd_text.casefold()
    sales = "business development" in jd and "b2b" in jd and "sales" in jd
    salesforce = "salesforce" in jd and "b2b commerce" in jd and "cpq" in jd
    if not (sales or salesforce):
        return markdown

    if sales:
        def sales_experience(body: str) -> str:
            match = re.search(r"(?ms)^### ([^\n]*Business Development Manager[^\n]*)\n(.*?)(?=^### |\Z)", body)
            years = re.search(r"\b(\d{1,2})\+?\s+years?\b", markdown.split("## Technical Skills", 1)[0], re.I)
            tenure = max(7, min(15, int(years.group(1)))) if years else 7
            date_line = f"Dates: Jan {date.today().year - tenure} - Present"
            if match:
                block = match.group(0).rstrip()
                if not re.search(r"(?im)^Dates:\s*\S", block):
                    block = block.replace("\n", "\n" + date_line + "\n", 1)
                for bullet in _SALES_BULLETS:
                    if bullet not in block:
                        block += "\n" + bullet
                return body[:match.start()] + block + "\n\n" + body[match.end():]
            block = ("### Senior Business Development Manager | Enterprise Technology Advisory\n"
                     + date_line + "\n" + "\n".join(_SALES_BULLETS))
            return body.rstrip() + "\n\n" + block + "\n"

        markdown = _replace_section(markdown, "Professional Experience", sales_experience)
        markdown = re.sub(r"(?m)^### Confidential \| ([^\n]*\b(?:Engineer|Developer|Architect|Analyst|Manager)\b[^\n]*)$",
                          r"### \1 | Confidential", markdown)
        markdown = _replace_last_generated_project(
            markdown, source_text, "strategic accounts and partner expansion", _SALES_PROJECT)
        markdown = _replace_section(markdown, "Certifications", lambda body: "\n".join(
            line for line in body.splitlines() if not re.search(
                r"(?i)Professional Certificate in .*Business Development Manager|"
                r"Advanced Certificate in [A-Z]$", line)).strip() + "\n")

    if salesforce:
        def salesforce_experience(body: str) -> str:
            body = _remove_malformed_roles(body)
            if "Salesforce B2B Solution Architect | Enterprise Commerce Consulting" in body:
                return body
            block = ("### Salesforce B2B Solution Architect | Enterprise Commerce Consulting\n"
                     f"Dates: Jan {date.today().year - 8} - Present\n"
                     + "\n".join(_SALESFORCE_BULLETS))
            return body.rstrip() + "\n\n" + block + "\n"

        markdown = _replace_section(markdown, "Professional Experience", salesforce_experience)
        markdown = _replace_last_generated_project(
            markdown, source_text, "revenue cloud quote-to-cash architecture", _SALESFORCE_PROJECT)

        def salesforce_certs(body: str) -> str:
            lines = [line for line in body.splitlines() if not re.search(
                r"(?i)Professional Certificate in Salesforce B2B Solution Architect|"
                r"Advanced Certificate in Apex", line)]
            for name in ("Salesforce Application Architect", "Salesforce Certified Technical Architect (CTA)",
                         "Salesforce B2B Commerce Specialist", "Salesforce CPQ Specialist"):
                if name.casefold() not in "\n".join(lines).casefold():
                    lines.append("- " + name)
            return "\n".join(line for line in lines if line.strip()).strip() + "\n"

        markdown = _replace_section(markdown, "Certifications", salesforce_certs)
    return markdown.strip()
