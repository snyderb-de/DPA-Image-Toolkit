const GITHUB_REPO = "snyderb-de/DPA-Image-Toolkit";
const GITHUB_API  = "https://api.github.com/repos/" + GITHUB_REPO;

// ── DOM helpers ────────────────────────────────────────────────────────────

function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls)  node.className   = cls;
    if (text) node.textContent = text;
    return node;
}

function append(parent, ...children) {
    children.forEach(c => parent.appendChild(c));
    return parent;
}

// ── Data loading ───────────────────────────────────────────────────────────

async function loadStaticData() {
    let data = window.DPA_DASHBOARD_DATA;
    if (!data) {
        const r = await fetch("data.json");
        data = await r.json();
    }
    return data;
}

async function loadGitHub() {
    const [repo, commits, issues, prs, langs] = await Promise.allSettled([
        fetch(GITHUB_API).then(r => r.json()),
        fetch(GITHUB_API + "/commits?per_page=8").then(r => r.json()),
        fetch(GITHUB_API + "/issues?state=open&per_page=20").then(r => r.json()),
        fetch(GITHUB_API + "/pulls?state=open&per_page=5").then(r => r.json()),
        fetch(GITHUB_API + "/languages").then(r => r.json()),
    ]);
    return {
        repo:    repo.status    === "fulfilled" ? repo.value    : null,
        commits: commits.status === "fulfilled" ? commits.value : null,
        issues:  issues.status  === "fulfilled" ? issues.value  : null,
        prs:     prs.status     === "fulfilled" ? prs.value     : null,
        langs:   langs.status   === "fulfilled" ? langs.value   : null,
    };
}

// ── Static sections ────────────────────────────────────────────────────────

function renderProject(project) {
    document.getElementById("project-name").textContent    = project.name;
    document.getElementById("project-tagline").textContent = project.tagline;
    document.getElementById("project-summary").textContent = project.summary;
    document.getElementById("project-version").textContent = "Version " + project.version;
    document.getElementById("project-status").textContent  = project.status;
    if (project.github) {
        document.getElementById("github-link").href = project.github;
    }
}

function renderHighlights(highlights) {
    const root = document.getElementById("highlights");
    highlights.forEach(item => {
        const card = el("article", "stat-card");
        append(card,
            el("p", "stat-label", item.label),
            el("h3", "stat-value", item.value),
            el("p", "stat-detail", item.detail),
        );
        root.appendChild(card);
    });
}

function renderTools(tools) {
    const root = document.getElementById("tools");
    tools.forEach(tool => {
        const card = el("article", "tool-card");

        const iconEl  = el("div", "tool-icon", tool.icon);
        const nameEl  = el("h3", null, tool.name);
        const summEl  = el("p", null, tool.summary);
        const headDiv = el("div");
        append(headDiv, nameEl, summEl);
        const head = el("div", "tool-head");
        append(head, iconEl, headDiv);

        const meta = el("div", "tool-meta");
        const inputP = el("p");
        inputP.append(el("strong", null, "Input: "), document.createTextNode(tool.inputs));
        meta.appendChild(inputP);

        const outDiv = el("div");
        outDiv.appendChild(el("strong", null, "Output:"));
        const outUl = el("ul");
        tool.outputs.forEach(o => outUl.appendChild(el("li", null, o)));
        outDiv.appendChild(outUl);
        meta.appendChild(outDiv);

        const notesDiv = el("div");
        notesDiv.appendChild(el("strong", null, "Notes:"));
        const notesUl = el("ul");
        tool.notes.forEach(n => notesUl.appendChild(el("li", null, n)));
        notesDiv.appendChild(notesUl);
        meta.appendChild(notesDiv);

        append(card, head, meta);
        root.appendChild(card);
    });
}

function renderOpenIssues(issues) {
    const root = document.getElementById("open-issues-list");
    const areaColors = {
        "QA":          "#e8f0ff",
        "Auto Crop":   "#fff3e8",
        "Merge TIFFs": "#f0ffe8",
        "OCR to PDF":  "#f5e8ff",
        "General":     "#f8f8f0",
        "Future Tool": "#fff8e8",
    };
    issues.forEach(issue => {
        const item   = el("div", "issue-item");
        const header = el("div", "issue-header");
        const badge  = el("span", "issue-area", issue.area);
        badge.style.background = areaColors[issue.area] || "#f8f8f0";
        header.appendChild(badge);
        append(item,
            header,
            el("p", "issue-title", issue.title),
            el("p", "issue-detail", issue.detail),
        );
        root.appendChild(item);
    });
}

function renderCompleted(items) {
    const root = document.getElementById("completed-list");
    items.forEach(item => {
        const li     = el("li");
        const strong = el("strong", null, item.title);
        const detail = el("span", "item-detail", item.detail);
        const br     = document.createElement("br");
        append(li, strong, br, detail);
        root.appendChild(li);
    });
}

function renderRoadmap(items) {
    const root = document.getElementById("roadmap-list");
    const priorityColor = { High: "#a25c4e", Medium: "#557492", Low: "#777" };
    items.forEach(item => {
        const wrap   = el("div", "roadmap-item");
        const header = el("div", "roadmap-header");
        const badge  = el("span", "priority-badge", "● " + item.priority);
        badge.style.color = priorityColor[item.priority] || "#777";
        header.appendChild(badge);
        append(wrap,
            header,
            el("p", "roadmap-title", item.title),
            el("p", "roadmap-detail", item.detail),
        );
        root.appendChild(wrap);
    });
}

function renderHCR(hcr) {
    const root = document.getElementById("hcr-section");
    root.appendChild(el("p", "hcr-summary", hcr.summary));

    const dec   = el("p", "hcr-decision");
    dec.append(el("strong", null, "Decision: "), document.createTextNode(hcr.decision));
    root.appendChild(dec);

    root.appendChild(el("p", "subsection-label", "Candidates"));
    hcr.candidates.forEach(c => {
        const wrap = el("div", "hcr-candidate");
        const head = el("div", "hcr-candidate-head");
        append(head, el("strong", null, c.name), el("span", "hcr-verdict", c.verdict));
        append(wrap,
            head,
            el("p", "hcr-pros", "✓ " + c.pros),
            el("p", "hcr-cons", "✗ " + c.cons),
        );
        root.appendChild(wrap);
    });

    const nextLabel = el("p", "subsection-label", "Next Steps");
    nextLabel.style.marginTop = "14px";
    root.appendChild(nextLabel);
    const ul = el("ul", "stacked-list");
    ul.style.paddingLeft = "18px";
    hcr.nextSteps.forEach(s => {
        const li = el("li", null, s);
        li.style.color = "var(--muted)";
        ul.appendChild(li);
    });
    root.appendChild(ul);
}

function renderSimpleList(id, items, ordered) {
    const root = document.getElementById(id);
    items.forEach(item => root.appendChild(el("li", null, item)));
    if (ordered) root.classList.add("numbered");
}

function renderDocs(docs) {
    const root = document.getElementById("docs");
    docs.forEach(doc => {
        const card  = el("article", doc.highlight ? "doc-card doc-card-highlight" : "doc-card");
        const link  = el("a", null, doc.path);
        link.href   = doc.path;
        link.target = "_blank";
        link.rel    = "noreferrer";
        append(card, el("h3", null, doc.name), el("p", null, doc.description), link);
        root.appendChild(card);
    });
}

function renderQuestions(questions) {
    const root = document.getElementById("questions-list");
    questions.forEach((q, i) => {
        const item = el("div", "question-item");
        append(item,
            el("p", "question-num", "Q" + (i + 1)),
            el("p", "question-text", q.question),
            el("p", "question-context", q.context),
        );
        root.appendChild(item);
    });
}

function renderDashboardTodo(items) {
    const root = document.getElementById("dashboard-todo-list");
    const statusColor = { planned: "#395572", idea: "#777" };
    items.forEach(item => {
        const wrap   = el("div", "dashboard-todo-item");
        const header = el("div", "dtodo-header");
        const status = el("span", "dtodo-status", item.status);
        status.style.color = statusColor[item.status] || "#777";
        append(header, el("strong", null, item.title), status);
        append(wrap, header, el("p", "dtodo-detail", item.detail));
        root.appendChild(wrap);
    });
}

function renderGeneratedAt() {
    const now = new Date();
    document.getElementById("generated-at").textContent =
        "Generated " + now.toLocaleDateString() + " " + now.toLocaleTimeString();
}

// ── GitHub dynamic sections ────────────────────────────────────────────────

function renderGitHubStats(repo) {
    if (!repo || repo.message) return;
    document.getElementById("gh-stars").textContent  = "⭐ " + (repo.stargazers_count ?? 0) + " stars";
    document.getElementById("gh-forks").textContent  = "⑂ " + (repo.forks_count ?? 0) + " forks";
    document.getElementById("gh-issues").textContent = "⊙ " + (repo.open_issues_count ?? 0) + " open issues";
    if (repo.pushed_at) {
        const d = new Date(repo.pushed_at);
        document.getElementById("gh-pushed").textContent = "↑ " + d.toLocaleDateString();
    }
    document.getElementById("github-stats").style.display = "flex";
}

function renderGitHubCommits(commits) {
    const root = document.getElementById("recent-commits");
    if (!Array.isArray(commits)) return;
    commits.forEach(c => {
        const msg  = (c.commit.message || "").split("\n")[0];
        const sha  = (c.sha || "").slice(0, 7);
        const date = new Date(c.commit.author.date).toLocaleDateString();

        const li      = el("li");
        const shaSpan = el("span", "commit-sha", sha);
        const dateSpan = el("span", "commit-date", date);
        append(li, shaSpan, document.createTextNode(" " + msg + " "), dateSpan);
        root.appendChild(li);
    });
    document.getElementById("commits-live-badge").style.display = "flex";
}

function renderGitHubPRs(prs) {
    const root = document.getElementById("open-prs");
    const open = Array.isArray(prs) ? prs.filter(p => p.state === "open") : [];
    if (open.length === 0) {
        root.appendChild(el("p", "muted-note", "No open pull requests."));
        return;
    }
    open.forEach(pr => {
        const wrap  = el("div", "pr-item");
        const title = el("a", "pr-title", "#" + pr.number + " " + (pr.title || ""));
        title.href   = pr.html_url;
        title.target = "_blank";
        title.rel    = "noreferrer";
        const date   = new Date(pr.created_at).toLocaleDateString();
        const meta   = el("span", "pr-meta", (pr.user?.login || "") + " · " + date);
        append(wrap, title, meta);
        root.appendChild(wrap);
    });
    document.getElementById("prs-live-badge").style.display = "flex";
}

function renderGitHubLanguages(langs) {
    const root = document.getElementById("languages");
    if (!langs || typeof langs !== "object") return;

    const total  = Object.values(langs).reduce((a, b) => a + b, 0);
    const sorted = Object.entries(langs).sort((a, b) => b[1] - a[1]);

    sorted.forEach(([name, bytes]) => {
        const pct = ((bytes / total) * 100).toFixed(1);
        const row  = el("div", "language-row");
        const meta = el("div", "language-meta");
        append(meta, el("span", "language-name", name), el("span", "language-stats", pct + "%"));
        const bar  = el("div", "language-bar");
        const fill = el("div", "language-fill");
        fill.style.width = pct + "%";
        bar.appendChild(fill);
        append(row, meta, bar);
        root.appendChild(row);
    });

    document.getElementById("language-note").textContent =
        "Live from GitHub API — byte counts, not line counts.";
    document.getElementById("langs-live-badge").style.display = "flex";
}

// ── Boot ───────────────────────────────────────────────────────────────────

async function boot() {
    const [staticData, gh] = await Promise.all([
        loadStaticData(),
        loadGitHub(),
    ]);

    renderProject(staticData.project);
    renderHighlights(staticData.highlights);
    renderTools(staticData.tools);
    renderOpenIssues(staticData.openIssues);
    renderCompleted(staticData.completed);
    renderRoadmap(staticData.roadmap);
    renderHCR(staticData.hcrInvestigation);
    renderSimpleList("workflow", staticData.workflow, true);
    renderSimpleList("architecture", staticData.architecture, false);
    renderSimpleList("dependencies", staticData.dependencies, false);
    renderDocs(staticData.docs);
    renderQuestions(staticData.questionsForBryan);
    renderDashboardTodo(staticData.dashboardTodo);
    renderGeneratedAt();

    renderGitHubStats(gh.repo);
    renderGitHubCommits(gh.commits);
    renderGitHubPRs(gh.prs);
    renderGitHubLanguages(gh.langs);
}

boot().catch(err => {
    document.body.textContent = "Failed to load dashboard. " + err;
});
