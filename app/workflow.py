import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from pydantic import BaseModel
from app.scrape import scrape_url_text

from app.gemini_client import generate_json
from app.models import CompanyResearch, Scorecard


class ScoreOnlyOutput(BaseModel):
    scorecard: Scorecard


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _truncate_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    return text[:max_chars]


def _read_docx_text(path: Path, *, max_chars: int = 12000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    doc = Document(str(path))
    parts: List[str] = []
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)[:max_chars]


def _resolve_variant_docx_text(*, variant: str) -> str:
    root = _repo_root()
    resumes_dir = root / "resumes"

    v = (variant or "").strip()
    if not v:
        return ""

    # If it's a path like resumes/CPTO.docx, try to load it repo-relative.
    if "/" in v or v.lower().endswith(".docx"):
        rel = v.lstrip("/")
        candidate = root / rel
        if candidate.exists():
            return _read_docx_text(candidate)
        return ""

    key = v.upper()
    key_to_filename = {
        "CPTO": "CPTO.docx",
        "CTO": "CTO.docx",
        "CPO": "CPO.docx",
    }
    desired = key_to_filename.get(key)
    if not desired or not resumes_dir.exists():
        return ""

    for p in resumes_dir.glob("*.docx"):
        if p.name.lower() == desired.lower():
            return _read_docx_text(p)
    return ""


def _sanitize_company_name(company_name: str) -> str:
    # Requirement: no spaces. Also remove other filesystem-risk characters.
    s = (company_name or "").strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Za-z0-9_-]", "", s)
    return s


def _next_export_version(*, company_folder: Path) -> int:
    # Look for scorecard_v#.json and increment.
    if not company_folder.exists():
        return 1
    pattern = re.compile(r"^scorecard_v(\d+)\.json$")
    max_v = 0
    for p in company_folder.glob("scorecard_v*.json"):
        m = pattern.match(p.name)
        if m:
            max_v = max(max_v, int(m.group(1)))
    return max_v + 1


def _requirements_prompt(*, job_description: str, variant: str, baseline_resume_text: str) -> str:
    return f"""
You are a scoring and gap analysis agent.

Goal:
Score how well the user's selected executive resume variant matches the job description.

Variant key:
{variant}

Job description:
{job_description}

Baseline resume variant text (source of truth for what the resume already says):
---
{baseline_resume_text}
---

Additional materials for factual support and classification (may help decide whether something is addable_from_existing_data):
---
v2_ExecResume_Strategy.md:
{_read_text(_repo_root() / "v2_ExecResume_Strategy.md")[:2500]}
---
goldmaster_resumes.md:
{_read_text(_repo_root() / "goldmaster_resumes.md")[:2500]}
---
ElevationsCU.md:
{_read_text(_repo_root() / "ElevationsCU.md")[:2500]}
---
resumes/MasterResume.md:
{_read_text(_repo_root() / "resumes" / "MasterResume.md")[:2500]}
---

Output strictly as JSON matching:
Scorecard:
- overall_score_percent: integer 0-100
- categories: array of {{category, score_percent, missing_items[]}}
Limit:
- Return ONLY a single JSON object with no extra text.
- categories: max 2
- missing_items per category: max 2
- missing_items: each string <= 45 characters
- Keep total JSON size compact; do not include long explanations.

Hard constraints:
- Zero-dash policy: do not output em-dash (—) or en-dash (–) anywhere.
""".strip()


def _company_research_prompt(
    *,
    company_url: str,
    company_name: Optional[str],
    company_page_text: str,
) -> str:
    name_line = company_name if company_name else "UnknownCompany"
    return f"""
You are a Chief of Staff researching an applicant's target company for executive interview readiness.

Inputs:
- company_name: {name_line}
- company_url: {company_url}
- company_page_text (scraped on-page text, may be incomplete):
---
{company_page_text}
---

Goal:
Produce an executive research summary that helps the user prepare for interviews and broad prompts like:
- "Tell us about yourself."
- "What is the greatest impact that you had in your prior role?"
- "What are the top 3 attributes you seek in a work environment in which you thrive?"

Rules:
- Use only the provided company_page_text for factual claims about the company.
- If you infer details that are not directly supported by the company_page_text, prefix the statement with "Inferred:" at the start of the sentence.
- Do not include any em-dash (—) or en-dash (–). Use commas or periods.
- Be direct, executive tone, and human-readable.

Use the user's executive background docs to ground the interview answers (do not invent new metrics):
- v2_ExecResume_Strategy.md:
{_read_text(_repo_root() / "v2_ExecResume_Strategy.md")[:2000]}
- goldmaster_resumes.md:
{_read_text(_repo_root() / "goldmaster_resumes.md")[:2000]}
- resumes/MasterResume.md:
{_read_text(_repo_root() / "resumes" / "MasterResume.md")[:2000]}
""".strip()


def generate_company_research(
    *,
    company_url: str,
    company_name: Optional[str],
    max_input_chars: int = 6000,
) -> CompanyResearch:
    page_text = scrape_url_text(company_url, max_chars=9000)
    if not page_text.strip():
        page_text = "Inferred: Unable to extract meaningful on-page text from the provided URL."

    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    prompt = _company_research_prompt(
        company_url=company_url,
        company_name=company_name,
        company_page_text=_truncate_text(page_text, max_input_chars),
    )

    # Keep output compact to reduce quota and avoid JSON truncation.
    return generate_json(
        schema=CompanyResearch,
        prompt=prompt,
        model=model,
        max_output_tokens=3500,
        temperature=0.3,
    )


def generate_scorecard_and_rewrite(
    *,
    variant: str,
    job_description_text: str,
    company_name: Optional[str] = None,
    company_url: Optional[str] = None,
    max_input_chars: int = 12000,
) -> Dict[str, Any]:
    warnings: List[str] = []
    jd = _truncate_text(job_description_text or "", min(max_input_chars, 8000))

    baseline_resume_text = _resolve_variant_docx_text(variant=variant)
    baseline_resume_text = _truncate_text(baseline_resume_text, 6000)
    if not baseline_resume_text.strip():
        raise RuntimeError(
            f"Could not read baseline resume variant text for variant='{variant}'. Expected resumes/{variant}.docx to exist."
        )

    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

    requirements_prompt = _requirements_prompt(
        job_description=jd,
        variant=variant,
        baseline_resume_text=baseline_resume_text,
    )
    try:
        score_only = generate_json(
            schema=ScoreOnlyOutput,
            prompt=requirements_prompt,
            model=model,
            max_output_tokens=3000,
        )
    except Exception:
        # Retry once with even tighter limits if JSON got truncated.
        retry_prompt = (
            requirements_prompt
            + "\n\nTighter limits for retry: categories max 1, missing_items per category max 1."
        )
        score_only = generate_json(
            schema=ScoreOnlyOutput,
            prompt=retry_prompt,
            model=model,
            max_output_tokens=2500,
        )

    company_research: Optional[CompanyResearch] = None
    if company_url and company_url.strip():
        try:
            company_research = generate_company_research(
                company_url=company_url,
                company_name=company_name,
            )
        except Exception:
            # Best-effort: never fail scorecard export if company research fails.
            company_research = None
            warnings.append("Company research unavailable (Gemini scrape or quota issue).")

    # Optional export: keep scorecard history by company and version.
    if company_name and company_name.strip():
        sanitized = _sanitize_company_name(company_name)
        if sanitized:
            opportunities_dir = _repo_root() / "opportunities"
            company_folder = opportunities_dir / sanitized
            company_folder.mkdir(parents=True, exist_ok=True)

            version = _next_export_version(company_folder=company_folder)
            scorecard_filename = f"scorecard_v{version}.json"
            company_research_filename = f"company_research_v{version}.json"
            (company_folder / scorecard_filename).write_text(
                json.dumps(
                    {
                        "metadata": {
                            "company_name": company_name,
                            "company_url": company_url,
                        },
                        "scorecard": score_only.scorecard.model_dump(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            if company_research is not None:
                (company_folder / company_research_filename).write_text(
                    json.dumps(
                        {
                            "metadata": {
                                "company_name": company_name,
                                "company_url": company_url,
                            },
                            "company_research": company_research.model_dump(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

    return {
        "scorecard": score_only.scorecard,
        "company_research": company_research,
        "warnings": warnings,
    }

