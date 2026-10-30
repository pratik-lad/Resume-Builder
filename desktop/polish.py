from __future__ import annotations

import copy
import re

from llm.client import clean_model_text
from validation import entity_guard


def supported(original, generated, source):
    allowed = entity_guard.build_allowed(source, [])
    if entity_guard.check(generated, allowed):
        return False
    if set(re.findall(r"\d+(?:[.,]\d+)?", generated)) != set(re.findall(r"\d+(?:[.,]\d+)?", original)):
        return False
    # Employment/project metadata is carried through unchanged. Only factual
    # bullet lines and summary prose may be rewritten in source mode.
    return True


def polish(payload, runtime, progress):
    document = copy.deepcopy(payload["document"])
    selected = payload["section"]
    section = document["sections"][selected]
    demo = document["mode"] == "demo"
    if section["key"] in {"header", "education"} or (section["key"] == "certifications" and not demo):
        raise ValueError("Contact, education, and certification details remain editable manually. Select summary, skills, experience, or projects for AI polishing.")
    runtime.start(payload.get("low_resource", False), progress)
    if demo:
        from pipeline.ideal_resume import SYSTEM_PROMPT
        system = SYSTEM_PROMPT + (
            "\nThis is the explicitly selected fictional/demo mode. Invent relevant experience, "
            "skills, concrete project details, responsibilities, and quantified outcomes as needed. "
            "Return only the requested section body, with jobs/projects separated. "
            "Do not apply source-only claim restrictions to this mode. "
            "For this request the app handles the rest of the resume: override the "
            "full-resume output instructions above. Write ONLY this section, without "
            "repeating the candidate name or other sections. For a summary write "
            "one paragraph of at most 120 words; for another block write at most 220 words.")
    else:
        system = ("Polish resume wording only. Do not invent skills, names, employers, dates, "
                  "numbers, qualifications, duties or achievements. Preserve all original facts. "
                  "Return only the selected text, no explanations, headings or reasoning.")
    jd = document["jd"]
    def messages(chunk):
        return [{"role": "system", "content": system},
                {"role": "user", "content": f"JOB DESCRIPTION:\n{jd}\n\nSECTION: {section['title']}\nTEXT:\n{chunk}\n\n"
                 f"Return ONLY the polished {section['title']} body. Do not produce a complete resume. "
                 "Keep the answer under 120 words for a summary or 220 words for another block."}]
    # Source mode preserves metadata lines verbatim. Demo mode intentionally
    # accepts invented claims and can expand every selected block.
    if not demo and section["key"] in {"experience", "projects", "skills"}:
        pieces = [(line, bool(re.match(r"^\s*[-*•]\s+", line))) for line in section["text"].splitlines()]
    else:
        pieces = [(part, True) for part in re.split(r"\n\s*\n", section["text"]) if part.strip()]
    chunks = []
    for piece, editable in pieces:
        if not editable:
            chunks.append((piece, False))
            continue
        if runtime.token_count(messages(piece)) + 768 <= 4096:
            chunks.append((piece, True))
            continue
        lines = piece.splitlines()
        buffer = ""
        for line in lines:
            candidate = (buffer + "\n" + line).strip()
            if runtime.token_count(messages(candidate)) + 768 > 4096:
                if not buffer or runtime.token_count(messages(line)) + 768 > 4096:
                    raise ValueError("The JD or one paragraph is too long for AI polishing. Shorten it; the complete draft is preserved.")
                chunks.append((buffer, True))
                buffer = line
            else:
                buffer = candidate
        if buffer:
            chunks.append((buffer, True))
    result = []
    editable_count = sum(editable for _, editable in chunks)
    index = 0
    for original, editable in chunks:
        if not editable:
            result.append(original)
            continue
        index += 1
        progress("polish", f"Polishing {section['title']} ({index}/{editable_count})")
        generated = clean_model_text(runtime.chat(messages(original)))
        if not generated.strip():
            raise RuntimeError("The model returned empty content. Your original text was kept.")
        if not demo and not supported(original, generated, document["source"]):
            raise ValueError("The model changed source claims. Your original text was kept. Fictional/demo mode permits invented claims.")
        result.append(generated)
    section["text"] = ("\n" if not demo and section["key"] in {"experience", "projects", "skills"} else "\n\n").join(result)
    return document
