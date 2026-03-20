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
        description="Variant key to target (e.g., 'CPTO', 'CTO', 'CPO'). Must map to a resumes/*.docx file.",
    )
    job_description_text: Optional[str] = Field(
        default=None,
        description="Raw job description text (preferred).",
    )
    job_description_url: Optional[str] = Field(
        default=None,
        description="URL to scrape for job description text, used when text is not provided.",
    )
    company_name: Optional[str] = Field(
        default=None,
        description="Company name for export. Used to create opportunities/<CompanyNameSansSpaces>/.",
    )
    max_input_chars: int = Field(
        default=12000,
        description="Maximum characters of job description text to send to Gemini.",
    )


class ScorecardCategory(BaseModel):
    category: str
    score_percent: int
    missing_items: List[str] = Field(default_factory=list)


class Scorecard(BaseModel):
    overall_score_percent: int
    categories: List[ScorecardCategory] = Field(default_factory=list)


class GapItem(BaseModel):
    requirement: str
    category: str
    classification: Literal["addable_from_existing_data", "needs_new_information"]
    recommended_resume_change: str


class QualityReport(BaseModel):
    passed: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    gap_items: List[GapItem] = Field(default_factory=list)


class ExportInfo(BaseModel):
    exported: bool
    company_folder: Optional[str] = None
    version: Optional[int] = None
    files: List[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    scorecard: Scorecard
    warnings: List[str] = Field(default_factory=list)

