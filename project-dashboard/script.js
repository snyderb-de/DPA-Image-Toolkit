async function loadDashboard() {
    let data = window.DPA_DASHBOARD_DATA;

    if (!data) {
        const response = await fetch("data.json");
        data = await response.json();
    }

    renderProject(data.project);
    renderHighlights(data.highlights);
    renderTools(data.tools);
    renderList("workflow", data.workflow, true);
    renderList("architecture", data.architecture);
    renderLanguages(data.languages, data.languageNote);
    renderList("open-issues", data.openIssues);
    renderList("future-ideas", data.futureIdeas);
    renderList("limitations", data.limitations);
    renderList("dependencies", data.dependencies);
    renderList("source-repos", data.sourceRepos);
    renderDocs(data.docs);
    renderList("recent-commits", data.recentCommits);
    renderGeneratedAt();
}

function renderProject(project) {
    document.getElementById("project-name").textContent = project.name;
    document.getElementById("project-tagline").textContent = project.tagline;
    document.getElementById("project-summary").textContent = project.summary;
    document.getElementById("project-version").textContent = `Version ${project.version}`;
    document.getElementById("project-status").textContent = project.status;
}

function renderHighlights(highlights) {
    const root = document.getElementById("highlights");
    root.innerHTML = "";

    highlights.forEach((item) => {
        const card = document.createElement("article");
        card.className = "stat-card";
        card.innerHTML = `
            <p class="stat-label">${item.label}</p>
            <h3 class="stat-value">${item.value}</h3>
            <p class="stat-detail">${item.detail}</p>
        `;
        root.appendChild(card);
    });
}

function renderTools(tools) {
    const root = document.getElementById("tools");
    root.innerHTML = "";

    tools.forEach((tool) => {
        const card = document.createElement("article");
        card.className = "tool-card";

        const outputs = tool.outputs.map((item) => `<li>${item}</li>`).join("");
        const notes = tool.notes.map((item) => `<li>${item}</li>`).join("");

        card.innerHTML = `
            <div class="tool-head">
                <div class="tool-icon">${tool.icon}</div>
                <div>
                    <h3>${tool.name}</h3>
                    <p>${tool.summary}</p>
                </div>
            </div>
            <div class="tool-meta">
                <p><strong>Input:</strong> ${tool.inputs}</p>
                <div>
                    <strong>Output:</strong>
                    <ul>${outputs}</ul>
                </div>
                <div>
                    <strong>Notes:</strong>
                    <ul>${notes}</ul>
                </div>
            </div>
        `;

        root.appendChild(card);
    });
}

function renderList(id, items, ordered = false) {
    const root = document.getElementById(id);
    root.innerHTML = "";

    items.forEach((item) => {
        const entry = document.createElement("li");
        entry.textContent = item;
        root.appendChild(entry);
    });

    if (ordered) {
        root.classList.add("numbered");
    }
}

function renderLanguages(languages, note) {
    const root = document.getElementById("languages");
    root.innerHTML = "";

    languages.forEach((lang) => {
        const row = document.createElement("div");
        row.className = "language-row";
        row.innerHTML = `
            <div class="language-meta">
                <span class="language-name">${lang.name}</span>
                <span class="language-stats">${lang.files} files · ${lang.percent}%</span>
            </div>
            <div class="language-bar">
                <div class="language-fill" style="width:${lang.percent}%"></div>
            </div>
        `;
        root.appendChild(row);
    });

    document.getElementById("language-note").textContent = note;
}

function renderDocs(docs) {
    const root = document.getElementById("docs");
    root.innerHTML = "";

    docs.forEach((doc) => {
        const card = document.createElement("article");
        card.className = "doc-card";
        card.innerHTML = `
            <h3>${doc.name}</h3>
            <p>${doc.description}</p>
            <a href="${doc.path}">${doc.path}</a>
        `;
        root.appendChild(card);
    });
}

function renderGeneratedAt() {
    const now = new Date();
    document.getElementById("generated-at").textContent =
        `Generated ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
}

loadDashboard().catch((error) => {
    document.body.innerHTML = `<pre style="padding:2rem;">Failed to load dashboard data.\n${error}</pre>`;
});
