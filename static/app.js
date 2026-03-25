const variantEl = document.getElementById("variant");
const jdTextEl = document.getElementById("jdText");
const jdUrlEl = document.getElementById("jdUrl");
const companyNameEl = document.getElementById("companyName");
const companyUrlEl = document.getElementById("companyUrl");
const generateBtn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");

const scorecardPre = document.getElementById("scorecardPre");
const companyResearchPre = document.getElementById("companyResearchPre");

const missingModal = document.getElementById("missingModal");
const missingModalText = document.getElementById("missingModalText");
const missingModalClose = document.getElementById("missingModalClose");

const companyUrlModal = document.getElementById("companyUrlModal");
const companyUrlModalClose = document.getElementById("companyUrlModalClose");
const companyUrlModalText = document.getElementById("companyUrlModalText");

function escapeHtml(input) {
  const s = String(input || "");
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderScorecard(scorecard) {
  const overall = Number(scorecard.overall_score_percent || 0);
  const categories = Array.isArray(scorecard.categories) ? scorecard.categories : [];

  const categoryBlocks = categories
    .map((c, idx) => {
      const cat = escapeHtml(c.category || `Category ${idx + 1}`);
      const pct = Number(c.score_percent || 0);
      const missing = Array.isArray(c.missing_items) ? c.missing_items : [];
      const missingList = missing.length
        ? `<ul style="margin:6px 0 0 18px;">${missing.map((m) => `<li>${escapeHtml(m)}</li>`).join("")}</ul>`
        : `<div class="muted" style="margin-top:6px;">No missing items.</div>`;

      return `
        <section style="margin-top:12px;">
          <h3 style="margin:0;font-size:16px;">${cat}</h3>
          <div><strong>score_percent:</strong> ${pct}%</div>
          <h4 style="margin:8px 0 0 0;font-size:14px;">missing_items</h4>
          ${missingList}
        </section>
      `;
    })
    .join("");

  return `
    <h1 style="margin:0 0 8px 0;font-size:20px;">Scorecard</h1>
    <h2 style="margin:0 0 10px 0;font-size:16px;">overall_score_percent: ${overall}%</h2>
    ${categoryBlocks || '<div class="muted">No categories returned.</div>'}
  `;
}

function showMissingModal() {
  if (!missingModal) return;
  missingModalText.textContent = "Either Job Description or Job Description URL is required.";
  missingModal.style.display = "block";
}

function hideMissingModal() {
  if (!missingModal) return;
  missingModal.style.display = "none";
}

if (missingModalClose) {
  missingModalClose.addEventListener("click", hideMissingModal);
}

function showCompanyUrlModal() {
  if (!companyUrlModal) return;
  if (companyUrlModalText) {
    companyUrlModalText.textContent = "Company URL for the Company Applying for should be listed";
  }
  companyUrlModal.style.display = "block";
}

function hideCompanyUrlModal() {
  if (!companyUrlModal) return;
  companyUrlModal.style.display = "none";
}

if (companyUrlModalClose) {
  companyUrlModalClose.addEventListener("click", hideCompanyUrlModal);
}

function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  statusEl.textContent = isLoading ? "Generating via Gemini..." : "";
  errorEl.textContent = "";

  if (isLoading) {
    // Clear previous scorecard so the user sees progress immediately.
    if (scorecardPre) {
      scorecardPre.style.background = "#f8fafc";
      scorecardPre.style.borderColor = "#e2e8f0";
      scorecardPre.innerHTML = `
        <h2 style="margin:0 0 8px 0;font-size:16px;">Scorecard</h2>
        <div class="muted">Processing scorecard...</div>
      `;
    }

    if (companyResearchPre) {
      companyResearchPre.style.background = "#f8fafc";
      companyResearchPre.style.borderColor = "#e2e8f0";
      companyResearchPre.innerHTML = `
        <h2 style="margin:0 0 8px 0;font-size:16px;">Company Research</h2>
        <div class="muted">Processing company research...</div>
      `;
    }
  }
}

function normalizeText(s) {
  return (s || "").trim();
}

generateBtn.addEventListener("click", async () => {
  const variant = variantEl.value;
  const job_description_text = normalizeText(jdTextEl.value);
  const job_description_url = normalizeText(jdUrlEl.value);
  const company_name = normalizeText(companyNameEl.value);
  const company_url = normalizeText(companyUrlEl ? companyUrlEl.value : "");

  if (!job_description_text && !job_description_url) {
    errorEl.textContent = "";
    showMissingModal();
    return;
  }

  if (company_name && !company_url) {
    errorEl.textContent = "";
    showCompanyUrlModal();
    return;
  }

  setLoading(true);
  try {
    const payload = {
      variant,
      job_description_text: job_description_text ? job_description_text : null,
      job_description_url: !job_description_text && job_description_url ? job_description_url : null,
      company_name: company_name ? company_name : null,
      company_url: company_url ? company_url : null,
      max_input_chars: 12000,
    };

    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const raw = await resp.text();
      let msg = raw || `HTTP ${resp.status}`;
      try {
        const j = JSON.parse(raw);
        // FastAPI typically returns { "detail": "..." }.
        msg = j.detail || j.error || msg;
      } catch (err) {
        // raw isn't JSON; keep msg as-is.
      }
      throw new Error(msg);
    }

    const data = await resp.json();
    const scorecard = data.scorecard || {};
    const overall = Number(scorecard.overall_score_percent || 0);
    scorecardPre.innerHTML = renderScorecard(scorecard);

    const companyResearch = data.company_research || null;
    if (companyResearchPre) {
      if (companyResearch) {
        companyResearchPre.innerHTML = renderCompanyResearch(companyResearch);
      } else {
        companyResearchPre.innerHTML = `
          <h2 style="margin:0 0 8px 0;font-size:16px;">Company Research</h2>
          <div class="muted">No company research available.</div>
        `;
      }
    }

    if (overall < 75) {
      scorecardPre.style.background = "#fef9c3";
      scorecardPre.style.borderColor = "#eab308";
      statusEl.textContent = `Score ${overall}%. Manual review recommended.`;
    } else {
      scorecardPre.style.background = "#f8fafc";
      scorecardPre.style.borderColor = "#e2e8f0";
      statusEl.textContent = `Score ${overall}%.`;
    }

function renderCompanyResearch(cr) {
  const safe = (s) => escapeHtml(s);
  const list = (arr) => {
    if (!Array.isArray(arr) || arr.length === 0) {
      return `<div class="muted" style="margin-top:6px;">None.</div>`;
    }
    return `<ul style="margin:6px 0 0 18px;">${arr.map((x) => `<li>${safe(x)}</li>`).join("")}</ul>`;
  };

  return `
    <h2 style="margin:0 0 10px 0;font-size:16px;">Company Research</h2>

    <h3 style="margin:0;font-size:14px;">Executive Overview</h3>
    <div style="margin-top:6px;white-space:pre-wrap;">${safe(cr.executive_overview)}</div>

    <h3 style="margin:12px 0 0 0;font-size:14px;">Inferred Company Priorities</h3>
    ${list(cr.inferred_company_priorities)}

    <h3 style="margin:12px 0 0 0;font-size:14px;">Inferred How Executives Operate</h3>
    ${list(cr.how_executives_operate)}

    <h3 style="margin:12px 0 0 0;font-size:14px;">Interview Prep Answers</h3>
    <div style="margin-top:6px;white-space:pre-wrap;"><strong>Tell us about yourself:</strong> ${safe(cr.tell_us_about_yourself_answer)}</div>
    <div style="margin-top:8px;white-space:pre-wrap;"><strong>Greatest impact:</strong> ${safe(cr.greatest_impact_answer)}</div>
    <div style="margin-top:8px;">
      <strong>Top 3 attributes for thriving:</strong>
      ${list(cr.top_3_attributes_for_thrive).replace("<div class=\"muted\" style=\"margin-top:6px;\">None.</div>", "")}
    </div>

    ${Array.isArray(cr.scrape_notes) && cr.scrape_notes.length
      ? `<h3 style="margin:12px 0 0 0;font-size:14px;">Scrape Notes</h3>${list(cr.scrape_notes)}`
      : ""}
  `;
}

    if (data.warnings && data.warnings.length) {
      errorEl.textContent = `Warnings: ${data.warnings.join(" | ")}`;
    }
  } catch (e) {
    const msg = e && e.message ? e.message : String(e);
    console.error("Generate failed:", e);
    errorEl.textContent = msg;
    statusEl.textContent = "Generation failed.";
  } finally {
    setLoading(false);
  }
});

