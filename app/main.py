from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import GenerateRequest, GenerateResponse, ScrapeRequest, ScrapeResponse
from app.workflow import generate_scorecard_and_rewrite
from app.scrape import scrape_job_description


app = FastAPI(title="JobSearch Local Resume Builder")

# The UI is local, but allowing CORS makes development easier.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.post("/api/scrape", response_model=ScrapeResponse)
def scrape(req: ScrapeRequest) -> ScrapeResponse:
    try:
        text = scrape_job_description(req.url)
        if not text.strip():
            return ScrapeResponse(source_url=req.url, extracted_text="", warning="No visible text extracted.")
        return ScrapeResponse(source_url=req.url, extracted_text=text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/generate")
def generate(req: GenerateRequest) -> Dict[str, Any]:
    if not req.job_description_text and not req.job_description_url:
        raise HTTPException(
            status_code=400,
            detail="Missing Information: Either Job Description or Job Description URL is required.",
        )

    job_text: Optional[str] = req.job_description_text
    warnings: List[str] = []

    if req.job_description_url and not job_text:
        try:
            job_text = scrape_job_description(req.job_description_url, max_chars=req.max_input_chars)
            if not job_text.strip():
                warnings.append("Scrape succeeded but returned no visible text.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Scrape failed: {e}")

    if not job_text or not job_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty after scraping/truncation.")

    try:
        result = generate_scorecard_and_rewrite(
            variant=req.variant,
            job_description_text=job_text,
            company_name=req.company_name,
            company_url=req.company_url,
            max_input_chars=req.max_input_chars,
        )
    except RuntimeError as e:
        # GeminI client setup failures (for example, missing GEMINI_API_KEY).
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise HTTPException(
                status_code=429,
                detail="Gemini quota exceeded (RESOURCE_EXHAUSTED). Wait for quota reset or use a different API key/plan.",
            )
        raise HTTPException(status_code=500, detail=msg)

    # Keep the HTTP response shape stable for the UI.
    return {
        "scorecard": result["scorecard"],
        "company_research": result.get("company_research"),
        "warnings": warnings + result.get("warnings", []),
    }

