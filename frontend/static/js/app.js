document.addEventListener("DOMContentLoaded", () => {
    let analysisData = null;
    let optimizedData = null;

    const form = document.getElementById("analysis-form");
    const loading = document.getElementById("loading");
    const loadingText = document.getElementById("loading-text");
    const errorEl = document.getElementById("error");
    const results = document.getElementById("results");
    const gapSection = document.getElementById("gap-section");
    const optimizedSection = document.getElementById("optimized-section");
    const steps = document.getElementById("steps");
    const submitBtn = document.getElementById("submit-btn");
    const optimizeBtn = document.getElementById("optimize-btn");
    const generateBtn = document.getElementById("generate-btn");
    const gapForm = document.getElementById("gap-form");
    const noGaps = document.getElementById("no-gaps");

    form.addEventListener("submit", handleAnalyze);
    optimizeBtn.addEventListener("click", handleLoadGapQuestions);
    generateBtn.addEventListener("click", handleOptimize);

    document.querySelectorAll(".btn-download").forEach((btn) => {
        btn.addEventListener("click", () => handleDownload(btn.dataset.format));
    });

    async function handleAnalyze(event) {
        event.preventDefault();

        const resumeInput = document.getElementById("resume");
        const jobInput = document.getElementById("job_description");

        if (!resumeInput.files.length) {
            showError("Please select a resume file.");
            return;
        }

        const formData = new FormData();
        formData.append("resume", resumeInput.files[0]);
        formData.append("job_description", jobInput.value.trim());

        setLoading(true, "Analyzing your resume...");
        hideError();
        hideAllSections();

        try {
            const response = await fetch("/api/analyze", { method: "POST", body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(parseError(data));

            analysisData = data;
            renderResults(data);
            results.classList.remove("hidden");
            steps.classList.remove("hidden");
            setActiveStep(1);
            results.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleLoadGapQuestions() {
        if (!analysisData) return;

        setLoading(true, "Generating gap questions...");
        hideError();

        try {
            const response = await fetch("/api/gap-questions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    resume: analysisData.resume,
                    job: analysisData.job,
                    match: analysisData.match,
                }),
            });

            const data = await response.json();
            if (!response.ok) throw new Error(parseError(data));

            renderGapQuestions(data);
            gapSection.classList.remove("hidden");
            setActiveStep(2);
            gapSection.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleOptimize() {
        if (!analysisData) return;

        const answers = collectAnswers();
        setLoading(true, "Optimizing your resume...");
        hideError();

        try {
            const response = await fetch("/api/optimize", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    resume: analysisData.resume,
                    job: analysisData.job,
                    match: analysisData.match,
                    answers,
                }),
            });

            const data = await response.json();
            if (!response.ok) throw new Error(parseError(data));

            optimizedData = data;
            renderOptimized(data);
            optimizedSection.classList.remove("hidden");
            setActiveStep(3);
            optimizedSection.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleDownload(format) {
        if (!optimizedData) return;

        setLoading(true, `Generating ${format.toUpperCase()}...`);

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    optimized_resume: optimizedData.optimized_resume,
                    format,
                    filename: "optimized_resume",
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(parseError(data));
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `optimized_resume.${format}`;
            link.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    }

    function collectAnswers() {
        const answers = [];
        gapForm.querySelectorAll(".gap-answer").forEach((input) => {
            answers.push({
                question_id: input.dataset.questionId,
                skill: input.dataset.skill,
                answer: input.value.trim(),
            });
        });
        return answers;
    }

    function renderGapQuestions(data) {
        gapForm.innerHTML = "";
        const aiBadge = document.getElementById("ai-badge");

        if (data.ai_powered) {
            aiBadge.classList.remove("hidden");
        } else {
            aiBadge.classList.add("hidden");
        }

        if (!data.questions || data.questions.length === 0) {
            noGaps.classList.remove("hidden");
            gapForm.classList.add("hidden");
            return;
        }

        noGaps.classList.add("hidden");
        gapForm.classList.remove("hidden");

        data.questions.forEach((q) => {
            const group = document.createElement("div");
            group.className = "form-group gap-question";

            const label = document.createElement("label");
            label.innerHTML = `<span class="gap-skill gap-skill--${q.importance}">${q.skill}</span> ${q.question}`;

            const textarea = document.createElement("textarea");
            textarea.className = "gap-answer";
            textarea.dataset.questionId = q.id;
            textarea.dataset.skill = q.skill;
            textarea.rows = 3;
            textarea.placeholder = "Describe your verified experience (leave blank if none)...";

            group.appendChild(label);
            group.appendChild(textarea);
            gapForm.appendChild(group);
        });
    }

    function renderOptimized(data) {
        const { optimized_resume: resume, ats, match_score_before, match_score_after } = data;

        document.getElementById("ats-score").textContent = `${ats.score}%`;
        const atsRing = document.getElementById("ats-ring");
        atsRing.style.borderColor = scoreColor(ats.score);

        const delta = (match_score_after - match_score_before).toFixed(1);
        const deltaText = delta > 0 ? `+${delta}` : delta;
        document.getElementById("match-improvement").textContent =
            `Match score: ${match_score_before}% → ${match_score_after}% (${deltaText}%)`;

        document.getElementById("ats-summary").textContent = getAtsSummary(ats.score);

        renderSkillList("ats-matched", ats.matched_keywords, "No matched keywords yet.");
        renderSkillList("ats-missing", ats.missing_keywords, "All keywords matched.");

        const recsEl = document.getElementById("ats-recommendations");
        recsEl.innerHTML = "";
        ats.recommendations.forEach((rec) => {
            const li = document.createElement("li");
            li.textContent = rec;
            recsEl.appendChild(li);
        });

        renderPreview(resume);
    }

    function renderPreview(resume) {
        const el = document.getElementById("resume-preview");
        let html = "";

        if (resume.summary) {
            html += `<div class="preview-block"><h5>Summary</h5><p>${escapeHtml(resume.summary)}</p></div>`;
        }
        if (resume.skills && resume.skills.length) {
            html += `<div class="preview-block"><h5>Skills</h5><p>${escapeHtml(resume.skills.join(", "))}</p></div>`;
        }
        if (resume.experience && resume.experience.length) {
            html += `<div class="preview-block"><h5>Experience</h5>`;
            resume.experience.forEach((exp) => {
                const header = [exp.title, exp.company, exp.duration].filter(Boolean).join(" | ");
                html += `<div class="preview-exp"><strong>${escapeHtml(header)}</strong>`;
                if (exp.description) {
                    html += `<pre class="preview-bullets">${escapeHtml(exp.description)}</pre>`;
                }
                html += `</div>`;
            });
            html += `</div>`;
        }
        if (resume.education && resume.education.length) {
            html += `<div class="preview-block"><h5>Education</h5><ul>`;
            resume.education.forEach((edu) => {
                html += `<li>${escapeHtml(edu)}</li>`;
            });
            html += `</ul></div>`;
        }

        el.innerHTML = html || "<p>No content generated.</p>";
    }

    function renderResults(data) {
        const { match, job, resume } = data;
        const score = match.score;

        document.getElementById("score-value").textContent = `${score}%`;
        document.getElementById("job-title").textContent = job.title || "Job Match Analysis";
        document.getElementById("score-ring").style.borderColor = scoreColor(score);
        document.getElementById("score-summary").textContent = getScoreSummary(score);

        renderSkillList("matching-skills", match.matching_skills, "No matching skills found.");
        renderSkillList("missing-required", match.missing_required, "All required skills matched.");
        renderSkillList("missing-preferred", match.missing_preferred, "All preferred skills matched.");
        renderSkillList("resume-skills", resume.skills, "No skills extracted from resume.");

        const suggestionsEl = document.getElementById("suggestions");
        suggestionsEl.innerHTML = "";
        match.improvement_suggestions.forEach((s) => {
            const li = document.createElement("li");
            li.textContent = s;
            suggestionsEl.appendChild(li);
        });
    }

    function renderSkillList(elementId, skills, emptyMessage) {
        const el = document.getElementById(elementId);
        el.innerHTML = "";
        if (!skills || skills.length === 0) {
            const li = document.createElement("li");
            li.className = "empty";
            li.textContent = emptyMessage;
            el.appendChild(li);
            return;
        }
        skills.forEach((skill) => {
            const li = document.createElement("li");
            li.textContent = skill;
            el.appendChild(li);
        });
    }

    function setActiveStep(step) {
        document.querySelectorAll(".step").forEach((el) => {
            el.classList.toggle("step--active", parseInt(el.dataset.step) === step);
            el.classList.toggle("step--done", parseInt(el.dataset.step) < step);
        });
    }

    function hideAllSections() {
        results.classList.add("hidden");
        gapSection.classList.add("hidden");
        optimizedSection.classList.add("hidden");
    }

    function setLoading(isLoading, text) {
        loading.classList.toggle("hidden", !isLoading);
        if (text) loadingText.textContent = text;
        submitBtn.disabled = isLoading;
        optimizeBtn.disabled = isLoading;
        generateBtn.disabled = isLoading;
    }

    function showError(message) {
        errorEl.textContent = message;
        errorEl.classList.remove("hidden");
    }

    function hideError() {
        errorEl.classList.add("hidden");
    }

    function parseError(data) {
        if (typeof data.detail === "string") return data.detail;
        if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg).join(", ");
        return "Request failed. Please try again.";
    }

    function scoreColor(score) {
        if (score >= 80) return "#22c55e";
        if (score >= 60) return "#f59e0b";
        return "#ef4444";
    }

    function getScoreSummary(score) {
        if (score >= 80) return "Excellent match — you're well aligned for this role.";
        if (score >= 60) return "Good match — a few gaps to address before applying.";
        if (score >= 40) return "Moderate match — focus on closing required skill gaps.";
        return "Low match — significant gaps detected. Consider upskilling or tailoring your resume.";
    }

    function getAtsSummary(score) {
        if (score >= 80) return "Strong ATS compatibility — keywords align well with the job description.";
        if (score >= 60) return "Moderate ATS score — a few more keywords could improve parsing.";
        return "Low ATS score — incorporate more job-specific keywords naturally.";
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
