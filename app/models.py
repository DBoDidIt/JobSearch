from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="A public URL to scrape for job description text.")


class ScrapeResponse(BaseModel):
    source_url: str
    extracted_text: str
    warning: Optional[str] = None


class GenerateRequest(BaseModel):
    variant: str = Field(
        default="CPTO",
        description="Variant key to target (e.g., 'CPTO', 'CTO', 'CPO'). Can also be a relative docx path like 'resumes/CPTO.docx'.",
    )
    job_description_text: Optional[str] = Field(
        default=None,
        description="Raw job description text (preferred).",
    )
    job_description_url: Optional[str] = Field(
        default=None,
        description="URL to scrape for job description text, used when text is not provided.",
    )
    max_input_chars: int = Field(
        default=12000,
        description="Maximum characters of job description text to send to Gemini.",
    )


class GenerateResponse(BaseModel):
    resume_md: str
    linkedin_md: str
    quality_report: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)

