const variantEl = document.getElementById("variant");
const jdTextEl = document.getElementById("jdText");
const jdUrlEl = document.getElementById("jdUrl");
const generateBtn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");

const qualityPre = document.getElementById("qualityPre");
const resumePre = document.getElementById("resumePre");
const linkedinPre = document.getElementById("linkedinPre");

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

  if (!job_description_text && !job_description_url) {
    errorEl.textContent = "Provide job description text or a URL.";
    return;
  }

  setLoading(true);
  try {
    const payload = {
      variant,
      job_description_text: job_description_text ? job_description_text : null,
      job_description_url: !job_description_text && job_description_url ? job_description_url : null,
      max_input_chars: 12000,
    };

    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const msg = await resp.text();
      throw new Error(msg || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    qualityPre.textContent = JSON.stringify(data.quality_report || {}, null, 2);
    resumePre.textContent = data.resume_md || "";
    linkedinPre.textContent = data.linkedin_md || "";

    if (data.warnings && data.warnings.length) {
      errorEl.textContent = `Warnings: ${data.warnings.join(" | ")}`;
    }
  } catch (e) {
    errorEl.textContent = e.message || String(e);
  } finally {
    setLoading(false);
  }
});

