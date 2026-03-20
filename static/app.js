const variantEl = document.getElementById("variant");
const jdTextEl = document.getElementById("jdText");
const jdUrlEl = document.getElementById("jdUrl");
const companyNameEl = document.getElementById("companyName");
const generateBtn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");

const scorecardPre = document.getElementById("scorecardPre");

const missingModal = document.getElementById("missingModal");
const missingModalText = document.getElementById("missingModalText");
const missingModalClose = document.getElementById("missingModalClose");

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

function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  statusEl.textContent = isLoading ? "Generating via Gemini..." : "";
  errorEl.textContent = "";
}

function normalizeText(s) {
  return (s || "").trim();
}

generateBtn.addEventListener("click", async () => {
  const variant = variantEl.value;
  const job_description_text = normalizeText(jdTextEl.value);
  const job_description_url = normalizeText(jdUrlEl.value);
  const company_name = normalizeText(companyNameEl.value);

  if (!job_description_text && !job_description_url) {
    errorEl.textContent = "";
    showMissingModal();
    return;
  }

  setLoading(true);
  try {
    const payload = {
      variant,
      job_description_text: job_description_text ? job_description_text : null,
      job_description_url: !job_description_text && job_description_url ? job_description_url : null,
      company_name: company_name ? company_name : null,
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
    scorecardPre.textContent = JSON.stringify(scorecard, null, 2);

    if (overall < 75) {
      scorecardPre.style.background = "#fef9c3";
      scorecardPre.style.borderColor = "#eab308";
      statusEl.textContent = `Score ${overall}%. Manual review recommended.`;
    } else {
      scorecardPre.style.background = "#f8fafc";
      scorecardPre.style.borderColor = "#e2e8f0";
      statusEl.textContent = `Score ${overall}%.`;
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

