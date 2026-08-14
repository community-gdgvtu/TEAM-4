(() => {
    "use strict";

    const runtimeConfig = window.SKILLPASSPORT_CONFIG || {};
    const API_BASE = normalizeRuntimeBase(runtimeConfig.apiBase, "/api");
    const PUBLIC_APP_BASE = normalizeRuntimeBase(runtimeConfig.publicAppBase, "");
    const SESSION_KEY = "skillpassport.session.v1";
    const OPPORTUNITY_KEY = "skillpassport.lastOpportunityId";
    const PROTECTED_ROUTES = new Set(["dashboard", "proofgraph", "prooflab", "opportunities", "passport"]);

    const main = document.getElementById("mainContent");
    const header = document.getElementById("siteHeader");
    const footer = document.getElementById("siteFooter");
    const toastRegion = document.getElementById("toastRegion");
    const evidenceDialog = document.getElementById("evidenceDialog");
    const evidenceDialogTitle = document.getElementById("evidenceDialogTitle");
    const evidenceDialogBody = document.getElementById("evidenceDialogBody");
    const routeProgress = document.getElementById("routeProgress");

    const state = {
        session: readStorage(SESSION_KEY),
        signupStep: 1,
        signupDraft: {},
        proofgraph: null,
        passport: null,
        opportunities: [],
        coverage: null,
        challengesByClaim: new Map(),
        challengeResult: null,
        evidenceById: new Map(),
        routeVersion: 0,
        lastRouteName: null,
        mobileNavOpen: false,
    };

    class ApiError extends Error {
        constructor(message, status = 0, payload = null) {
            super(message);
            this.name = "ApiError";
            this.status = status;
            this.payload = payload;
        }
    }

    function normalizeRuntimeBase(value, fallback) {
        const normalized = String(value || fallback || "").trim();
        return normalized === "/" ? "" : normalized.replace(/\/+$/, "");
    }

    function publicVerificationUrl(passportId) {
        const appBase = PUBLIC_APP_BASE || window.location.origin;
        return `${appBase}/#/verify/${encodeURIComponent(passportId)}`;
    }

    function readStorage(key) {
        try {
            const raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : null;
        } catch (_error) {
            return null;
        }
    }

    function writeStorage(key, value) {
        try {
            if (value === null || value === undefined || value === "") {
                localStorage.removeItem(key);
            } else {
                localStorage.setItem(key, typeof value === "string" ? value : JSON.stringify(value));
            }
        } catch (_error) {
            // The app remains usable if storage is unavailable.
        }
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    const e = escapeHtml;

    function asArray(value) {
        if (Array.isArray(value)) return value;
        if (value === null || value === undefined) return [];
        return [value];
    }

    function firstDefined(...values) {
        return values.find((value) => value !== undefined && value !== null && value !== "");
    }

    function initials(name) {
        const parts = String(name || "Skill Passport").trim().split(/\s+/).filter(Boolean);
        return parts.slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "SP";
    }

    function titleCase(value) {
        return String(value || "")
            .toLowerCase()
            .replaceAll("_", " ")
            .replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    function formatDate(value, fallback = "Not recorded") {
        if (!value) return fallback;
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return fallback;
        return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(date);
    }

    function shortHash(value) {
        const hash = String(value || "");
        return hash.length > 22 ? `${hash.slice(0, 12)}…${hash.slice(-8)}` : hash || "Not available";
    }

    function stateKey(value) {
        return String(value || "DETECTED").toLowerCase().replaceAll("_", "-");
    }

    function trustLabel(value) {
        const labels = {
            DETECTED: "Detected",
            EVIDENCE_BACKED: "Evidence backed",
            CHALLENGE_VERIFIED: "Challenge verified",
            MISSING: "Missing",
        };
        return labels[String(value || "").toUpperCase()] || titleCase(value || "Detected");
    }

    function renderTrustBadge(value) {
        const normalized = String(value || "DETECTED").toUpperCase();
        return `<span class="trust-badge trust-${e(stateKey(normalized))}">${e(trustLabel(normalized))}</span>`;
    }

    function routePath(name, parameter = "") {
        return `#/${name}${parameter ? `/${encodeURIComponent(parameter)}` : ""}`;
    }

    function navigate(path) {
        const hash = path.startsWith("#") ? path : `#${path.startsWith("/") ? path : `/${path}`}`;
        if (window.location.hash === hash) {
            renderRoute();
        } else {
            window.location.hash = hash;
        }
    }

    function parseRoute() {
        const raw = window.location.hash.replace(/^#\/?/, "");
        const [pathPart] = raw.split("?");
        const parts = pathPart.split("/").filter(Boolean).map((part) => decodeURIComponent(part));
        if (!parts.length) return { name: "landing", parameter: null };
        const name = parts[0].toLowerCase();
        const known = new Set(["login", "signup", "dashboard", "proofgraph", "prooflab", "opportunities", "passport", "verify"]);
        return known.has(name) ? { name, parameter: parts[1] || null } : { name: "notfound", parameter: null };
    }

    function setSession(session) {
        state.session = session;
        writeStorage(SESSION_KEY, session);
    }

    function clearSession() {
        state.session = null;
        state.proofgraph = null;
        state.passport = null;
        state.opportunities = [];
        state.coverage = null;
        state.challengesByClaim.clear();
        state.challengeResult = null;
        state.evidenceById.clear();
        writeStorage(SESSION_KEY, null);
        writeStorage(OPPORTUNITY_KEY, null);
    }

    function studentId() {
        return firstDefined(state.session?.student_id, state.session?.studentId, state.session?.user?.student_id, state.session?.candidate?.student_id);
    }

    function displayName() {
        return firstDefined(
            state.proofgraph?.profile?.display_name,
            state.proofgraph?.profile?.name,
            state.session?.display_name,
            state.session?.name,
            state.session?.user?.name,
            "SkillPassport candidate",
        );
    }

    async function apiRequest(path, options = {}) {
        const headers = new Headers(options.headers || {});
        headers.set("Accept", "application/json");
        const request = { method: options.method || "GET", headers };

        if (state.session?.token) headers.set("Authorization", `Bearer ${state.session.token}`);
        if (options.body !== undefined) {
            headers.set("Content-Type", "application/json");
            request.body = JSON.stringify(options.body);
        }

        let response;
        try {
            response = await fetch(`${API_BASE}${path}`, request);
        } catch (_error) {
            throw new ApiError("SkillPassport could not reach the configured API. Check the public API URL and service availability.");
        }

        let payload = null;
        const text = await response.text();
        if (text) {
            try {
                payload = JSON.parse(text);
            } catch (_error) {
                payload = text;
            }
        }

        if (!response.ok) {
            const detail = typeof payload === "object" && payload
                ? firstDefined(payload.detail, payload.message, payload.error)
                : payload;
            const message = Array.isArray(detail)
                ? detail.map((item) => item.msg || item.message || String(item)).join(" ")
                : String(detail || `Request failed with status ${response.status}.`);
            throw new ApiError(message, response.status, payload);
        }
        return payload;
    }

    function unwrap(payload, ...keys) {
        if (!payload || typeof payload !== "object") return payload;
        for (const key of keys) {
            if (payload[key] !== undefined) return payload[key];
        }
        return payload;
    }

    function normalizeSession(payload) {
        const root = payload || {};
        const dashboard = root.dashboard || {};
        const student = firstDefined(root.student, dashboard.student, root.candidate, root.profile, {});
        const user = firstDefined(root.user, root.session?.user, {});
        const id = firstDefined(root.student_id, root.studentId, student.student_id, student.id, user.student_id, root.session?.student_id);
        if (!id) throw new ApiError("The API response did not include a student ID.");
        return {
            student_id: String(id),
            display_name: firstDefined(root.display_name, root.name, student.display_name, student.name, user.display_name, user.name, "SkillPassport candidate"),
            token: firstDefined(root.access_token, root.token, root.session_token, root.session?.token, null),
            repository_url: firstDefined(root.repository_url, student.repository_url, user.repository_url, null),
            github_username: firstDefined(root.github_username, student.github_username, user.github_username, null),
            demo: Boolean(firstDefined(root.demo, student.demo, user.demo, false)),
        };
    }

    function normalizeProofgraph(payload) {
        const graph = unwrap(payload, "proofgraph", "graph") || {};
        const profile = firstDefined(graph.profile, graph.student, graph.candidate, payload?.profile, payload?.student, {});
        const claims = asArray(firstDefined(graph.claims, graph.skill_claims, payload?.claims, payload?.skill_claims, []));
        const evidence = asArray(firstDefined(graph.evidence, graph.evidence_items, payload?.evidence, payload?.evidence_items, []));

        for (const claim of claims) {
            for (const item of asArray(claim.evidence)) {
                if (!evidence.some((existing) => existing.id === item.id)) evidence.push(item);
            }
        }

        return { profile: profile || {}, claims, evidence };
    }

    function normalizePassport(payload) {
        const passport = unwrap(payload, "passport", "public_passport");
        if (!passport || !passport.id) return null;
        return { ...passport, stamps: asArray(passport.stamps) };
    }

    function normalizeChallenge(payload) {
        return unwrap(payload, "challenge", "proof_challenge") || payload;
    }

    function normalizeOpportunities(payload) {
        const list = unwrap(payload, "opportunities", "items");
        return asArray(list).filter((item) => item && item.id);
    }

    function normalizeCoverage(payload) {
        const coverage = unwrap(payload, "coverage", "match", "result") || payload;
        if (!coverage || !coverage.opportunity) return null;
        return { ...coverage, matches: asArray(coverage.matches) };
    }

    function startRouteProgress() {
        routeProgress.className = "route-progress active";
    }

    function finishRouteProgress() {
        routeProgress.className = "route-progress done";
        window.setTimeout(() => { routeProgress.className = "route-progress"; }, 220);
    }

    function toast(message, type = "success") {
        const item = document.createElement("div");
        item.className = `toast ${type}`;
        const symbol = document.createElement("span");
        symbol.className = "toast-symbol";
        symbol.setAttribute("aria-hidden", "true");
        symbol.textContent = type === "error" ? "!" : "✓";
        const text = document.createElement("span");
        text.textContent = message;
        item.append(symbol, text);
        toastRegion.appendChild(item);
        window.setTimeout(() => item.remove(), 5200);
    }

    function setButtonBusy(button, busy, label = "Working…") {
        if (!button) return;
        if (busy) {
            button.dataset.originalLabel = button.textContent;
            button.textContent = label;
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
        } else {
            button.textContent = button.dataset.originalLabel || button.textContent;
            button.disabled = false;
            button.removeAttribute("aria-busy");
            delete button.dataset.originalLabel;
        }
    }

    function brandMarkup() {
        return `<a class="brand" href="#/" aria-label="SkillPassport home">
            <span class="brand-mark" aria-hidden="true">SP</span>
            <span class="brand-word">Skill<span class="brand-word-light">Passport</span></span>
        </a>`;
    }

    function headerMarkup(route) {
        if (PROTECTED_ROUTES.has(route.name) && state.session) {
            const links = [
                ["dashboard", "Dashboard"],
                ["proofgraph", "ProofGraph"],
                ["opportunities", "Opportunities"],
                ["passport", "Passport"],
            ];
            return `<div class="header-inner">
                ${brandMarkup()}
                <nav class="site-nav app-nav ${state.mobileNavOpen ? "open" : ""}" id="appNav" aria-label="Product navigation">
                    ${links.map(([name, label]) => `<a class="nav-link" href="#/${name}" ${route.name === name ? 'aria-current="page"' : ""}>${label}</a>`).join("")}
                </nav>
                <div class="user-menu">
                    <span class="user-chip"><span class="avatar" aria-hidden="true">${e(initials(displayName()))}</span><span>${e(displayName())}</span></span>
                    <button class="button button-quiet" type="button" data-action="logout">Log out</button>
                    <button class="icon-button mobile-menu-button" type="button" data-action="toggle-menu" aria-controls="appNav" aria-expanded="${state.mobileNavOpen}"><span aria-hidden="true">≡</span><span class="visually-hidden">Menu</span></button>
                </div>
            </div>`;
        }

        if (route.name === "verify") {
            return `<div class="header-inner">${brandMarkup()}<div class="header-actions"><a class="button button-secondary button-small" href="#/">About SkillPassport</a></div></div>`;
        }

        return `<div class="header-inner">
            ${brandMarkup()}
            <div class="header-actions">
                <a class="button button-quiet" href="#/login">Log in</a>
                <a class="button button-primary button-small" href="#/signup">Build my passport</a>
            </div>
        </div>`;
    }

    function footerMarkup() {
        return `<div class="footer-inner"><span>SkillPassport · Japan ↔ India talent proof</span><span class="footer-principle">AI proposes. Engines prove.</span></div>`;
    }

    function updateChrome(route) {
        header.innerHTML = headerMarkup(route);
        footer.innerHTML = footerMarkup();
        const titles = {
            landing: "SkillPassport — Inspect the evidence. Challenge the proof.",
            login: "Log in · SkillPassport",
            signup: "Build your SkillPassport",
            dashboard: "Dashboard · SkillPassport",
            proofgraph: "ProofGraph · SkillPassport",
            prooflab: "Proof Lab · SkillPassport",
            opportunities: "Opportunity Lens · SkillPassport",
            passport: "My SkillPassport",
            verify: "Public verification · SkillPassport",
            notfound: "Page not found · SkillPassport",
        };
        document.title = titles[route.name] || titles.landing;
    }

    function loadingView(title = "Loading SkillPassport", message = "Reading inspectable evidence and server-owned trust state…") {
        return `<section class="loading-view" aria-labelledby="loadingTitle"><div class="loading-content"><div class="loading-mark" aria-hidden="true"></div><h1 id="loadingTitle">${e(title)}</h1><p>${e(message)}</p></div></section>`;
    }

    function errorView(error, context = "this page") {
        const message = error instanceof Error ? error.message : String(error || "An unexpected error occurred.");
        return `<section class="error-view"><div class="error-content"><div class="error-icon" aria-hidden="true">!</div><p class="eyebrow">Could not load ${e(context)}</p><h1>There is a clear way back.</h1><p>${e(message)}</p><div class="inline-actions"><button class="button button-primary" type="button" data-action="retry-route">Try again</button><a class="button button-secondary" href="#/">Return home</a></div></div></section>`;
    }

    function landingView() {
        return `<section class="landing-hero">
            <div class="shell hero-grid">
                <div class="hero-copy">
                    <p class="eyebrow">Skills you can inspect. Proof you can challenge.</p>
                    <h1>A resume is a claim.<span>SkillPassport shows the evidence — and lets you challenge it.</span></h1>
                    <p>Turn academic records and real project work into inspectable skill claims, prove uncertain capabilities through live challenges, and see exactly what you have demonstrated for an opportunity.</p>
                    <div class="hero-actions">
                        <a class="button button-primary" href="#/signup">Build my SkillPassport <span aria-hidden="true">→</span></a>
                        <button class="button button-secondary" type="button" data-action="judge-demo">View Judge Demo</button>
                    </div>
                    <p class="hero-note"><span class="hero-note-dot" aria-hidden="true"></span>Deterministic demo mode works without GitHub, Gemini, or MongoDB.</p>
                </div>
                <div class="hero-proof-card" aria-label="Skill claim example">
                    <div class="mini-profile"><div class="mini-profile-person"><span class="mini-avatar">AR</span><div><h2>Ananya Rao</h2><p>Fictional demo candidate · Bengaluru → Tokyo</p></div></div><span class="source-badge">ProofGraph</span></div>
                    <div class="mini-claim"><div class="mini-claim-top"><div><h3>FastAPI</h3><p>Multiple inspectable signals support this claim.</p></div><span class="trust-badge trust-evidence-backed">Evidence backed</span></div><div class="mini-evidence"><span class="mini-node">APIRouter<br>routes/users.py</span><span class="mini-node">API tests<br>test_users.py</span><span class="mini-node">Coursework<br>Web API Engineering</span></div><div class="mini-uncertainty"><strong>Still uncertain:</strong> request validation and duplicate handling. Challenge this exact gap.</div></div>
                </div>
            </div>
        </section>
        <section class="flow-strip" aria-label="SkillPassport product flow"><ol class="shell flow-list"><li><span class="flow-number">1</span>Evidence</li><li><span class="flow-number">2</span>ProofGraph</li><li><span class="flow-number">3</span>Challenge</li><li><span class="flow-number">4</span>Verified Skill</li><li><span class="flow-number">5</span>Opportunity</li></ol></section>
        <section class="section-block" id="problem"><div class="shell problem-grid"><div class="problem-statement"><p class="eyebrow">The problem</p><blockquote>Academic context gets lost across borders. Resume claims are hard to inspect.</blockquote><p>Early-career talent has real work to show, but employers see a flat list of technologies with no clear trust model.</p></div><div class="problem-points"><article class="problem-point"><span class="point-number">01</span><div><h3>Claims hide the evidence</h3><p>A framework name cannot show which files, tests, contributions, or coursework support it.</p></div></article><article class="problem-point"><span class="point-number">02</span><div><h3>Evidence still leaves doubt</h3><p>Using FastAPI once does not prove request validation, error handling, or an intermediate capability level.</p></div></article><article class="problem-point"><span class="point-number">03</span><div><h3>Opportunity matching hides the gaps</h3><p>Opaque fit scores do not tell candidates what is proven, merely detected, or still missing.</p></div></article></div></div></section>
        <section class="section-block" id="how"><div class="shell"><div class="section-heading"><p class="eyebrow">How SkillPassport works</p><h2>Claim → Doubt → Challenge → Proof → Opportunity</h2><p>One connected trust loop, built around inspectable evidence and deterministic verification.</p></div><div class="feature-grid"><article class="feature-card"><span class="feature-icon">PG</span><h3>ProofGraph</h3><p>See exactly why a skill claim exists: source files, dependencies, tests, contribution signals, and clearly labeled demo academic evidence.</p><span class="feature-kicker">Why this skill?</span></article><article class="feature-card"><span class="feature-icon">PL</span><h3>Proof Challenge</h3><p>Challenge the remaining uncertainty with a targeted concept check and a live task grounded in the candidate's own evidence.</p><span class="feature-kicker">Did the deterministic tests pass?</span></article><article class="feature-card"><span class="feature-icon">OL</span><h3>Opportunity Lens</h3><p>Compare required and preferred capabilities against verified, evidence-backed, detected, and missing states—without a mystery percentage.</p><span class="feature-kicker">What does this proof unlock?</span></article></div></div></section>
        <section class="section-block region-section" id="region"><div class="shell"><div class="section-heading"><p class="eyebrow">Starting with Japan ↔ India</p><h2>Technical talent crosses institutions. Evidence needs to travel with it.</h2><p>SkillPassport begins with students and early-career builders navigating different educational and hiring contexts between India and Japan.</p></div><div class="region-grid"><article class="region-card"><h3>India: deep project evidence</h3><p>Coursework, hackathons, GitHub projects, and candidate-authored contributions become visible proof—not just a technology list.</p></article><span class="region-bridge" aria-hidden="true">↔</span><article class="region-card"><h3>Japan: inspectable opportunity fit</h3><p>English, Japanese, or mixed descriptions become structured requirements that map back to demonstrated capability.</p></article></div></div></section>
        <section class="section-block" id="principle"><div class="shell"><div class="section-heading"><p class="eyebrow">Disciplined intelligence</p><h2>AI proposes. Engines prove.</h2><p>Gemini may interpret context and personalize wording. It cannot create a verified skill.</p></div><div class="principle-grid"><article class="principle-card"><h3>AI interprets</h3><p>Evidence gaps, challenge context, multilingual requirements, and concise explanations—always structured and validated.</p></article><article class="principle-card"><h3>Evidence supports</h3><p>Inspectable provenance makes every claim defensible. Academic records corroborate; repository signals show the work.</p></article><article class="principle-card"><h3>Engines verify</h3><p>Only deterministic test results create a persistent VerificationEvent and promote a claim to Challenge Verified.</p></article></div></div></section>
        <section class="section-block-compact"><div class="shell final-cta"><p class="eyebrow">Make capability inspectable</p><h2>Build proof that survives the next question.</h2><p>Start with your evidence, expose what is still uncertain, then prove the exact capability an opportunity needs.</p><div class="inline-actions"><a class="button button-green" href="#/signup">Build my SkillPassport</a><button class="button button-secondary" type="button" data-action="judge-demo">View Judge Demo</button></div></div></section>`;
    }

    function authStoryMarkup() {
        return `<aside class="auth-story"><div><p class="eyebrow">SkillPassport</p><h2>Proof travels farther than a claim.</h2><p>Connect real work, inspect every signal, and challenge what remains uncertain.</p></div><ul class="auth-story-list"><li><span class="story-check">✓</span>Inspectable provenance</li><li><span class="story-check">✓</span>Deterministic proof</li><li><span class="story-check">✓</span>Transparent opportunity fit</li></ul></aside>`;
    }

    function loginView() {
        return `<section class="auth-page"><div class="auth-layout">${authStoryMarkup()}<div class="auth-panel"><div class="auth-panel-header"><p class="eyebrow">Welcome back</p><h1>Open your SkillPassport</h1><p>Use your account, or return home for the stable Judge Demo.</p></div><form id="loginForm"><div class="field-grid"><div class="field-full"><label for="loginEmail">Email address</label><input id="loginEmail" name="email" type="email" autocomplete="email" required></div><div class="field-full"><label for="loginPassword">Password</label><input id="loginPassword" name="password" type="password" autocomplete="current-password" minlength="8" required></div></div><aside class="demo-login-hint" aria-label="Demo login credentials"><strong>Demo login</strong><span><code>ananya.demo@skillpassport.local</code></span><span><code>proof-demo-2026</code></span></aside><p class="form-error" id="loginError" hidden></p><div class="form-actions"><a class="button button-quiet" href="#/">Back home</a><button class="button button-primary" type="submit">Log in</button></div></form><p class="auth-switch">New to SkillPassport? <a href="#/signup">Build yours</a></p></div></div></section>`;
    }

    function signupView() {
        return `<section class="auth-page"><div class="auth-layout">${authStoryMarkup()}<div class="auth-panel auth-panel-wide"><div class="auth-panel-header"><p class="eyebrow">Guided setup</p><h1>Build your SkillPassport</h1><p>Four short steps. Demo academic records are always labeled.</p></div><div class="stepper" aria-label="Signup progress">${["Profile", "Evidence", "Academic", "Analyze"].map((label, index) => `<span class="stepper-item ${index + 1 === state.signupStep ? "active" : index + 1 < state.signupStep ? "done" : ""}" data-stepper="${index + 1}"><span class="stepper-line"></span>${label}</span>`).join("")}</div>
        <form id="signupForm">
            <section class="signup-step" data-signup-step="1" ${state.signupStep === 1 ? "" : "hidden"} aria-labelledby="step1Title"><h2 id="step1Title">1. Basic profile</h2><div class="field-grid"><div class="field-full"><label for="signupName">Full name</label><input id="signupName" name="name" autocomplete="name" minlength="2" required></div><div class="field"><label for="signupEmail">Email</label><input id="signupEmail" name="email" type="email" autocomplete="email" required></div><div class="field"><label for="signupPassword">Demo password</label><input id="signupPassword" name="password" type="password" autocomplete="new-password" minlength="8" required><span class="field-help">Stored by the server as a password hash.</span></div><div class="field-full"><label for="signupInstitution">Institution</label><input id="signupInstitution" name="institution" autocomplete="organization" placeholder="Waseda University or VTU-affiliated college" required></div><div class="field"><label for="signupCountry">Country</label><select id="signupCountry" name="country" required><option value="">Choose country</option><option>India</option><option>Japan</option><option>Other</option></select></div><div class="field"><label for="signupStudy">Study area</label><input id="signupStudy" name="study_area" placeholder="Computer Science" required></div></div></section>
            <section class="signup-step" data-signup-step="2" ${state.signupStep === 2 ? "" : "hidden"} aria-labelledby="step2Title"><h2 id="step2Title">2. Evidence setup</h2><p class="muted">Public repositories work without OAuth where GitHub permits. The demo fallback keeps setup reliable offline.</p><div class="field-grid"><div class="field-full"><label for="githubUsername">GitHub username <span class="muted">(optional)</span></label><input id="githubUsername" name="github_username" autocomplete="off" placeholder="octocat"></div><div class="field-full"><label for="repositoryUrl">Repository URL <span class="muted">(optional)</span></label><input id="repositoryUrl" name="repository_url" type="url" inputmode="url" placeholder="https://github.com/username/project"></div></div></section>
            <section class="signup-step" data-signup-step="3" ${state.signupStep === 3 ? "" : "hidden"} aria-labelledby="step3Title"><h2 id="step3Title">3. Academic source</h2><p class="muted">Academic records support a claim. They never independently challenge-verify a skill.</p><div class="choice-grid"><label class="choice-card"><input type="radio" name="academic_source" value="demo" checked><strong>Use bundled demo record</strong><span>Clearly shown as Demo academic evidence. No institution system connection is implied.</span></label><label class="choice-card"><input type="radio" name="academic_source" value="manual"><strong>Enter coursework manually</strong><span>Add one relevant course now. You can analyze repository evidence alongside it.</span></label></div><div class="manual-coursework" id="manualCoursework" hidden><div class="field"><label for="courseName">Course name</label><input id="courseName" name="course_name" placeholder="Database Management Systems"></div><div class="field-grid"><div class="field"><label for="courseGrade">Grade</label><input id="courseGrade" name="course_grade" placeholder="A"></div><div class="field"><label for="courseSkills">Skills supported</label><input id="courseSkills" name="course_skills" placeholder="SQL, data modelling"></div></div></div></section>
            <section class="signup-step" data-signup-step="4" ${state.signupStep === 4 ? "" : "hidden"} aria-labelledby="step4Title"><h2 id="step4Title">4. Analyze your evidence</h2><p class="muted">Review the setup, then let deterministic engines create inspectable skill claims.</p><dl class="review-list"><div class="review-row"><dt>Candidate</dt><dd id="reviewName">—</dd></div><div class="review-row"><dt>Institution</dt><dd id="reviewInstitution">—</dd></div><div class="review-row"><dt>Repository</dt><dd id="reviewRepository">Demo repository fallback</dd></div><div class="review-row"><dt>Academic source</dt><dd id="reviewAcademic">Demo academic evidence</dd></div></dl></section>
            <p class="form-error" id="signupError" hidden></p><div class="form-actions"><button class="button button-secondary" type="button" data-action="signup-back" ${state.signupStep === 1 ? "disabled" : ""}>Back</button><button class="button button-primary" type="${state.signupStep === 4 ? "submit" : "button"}" data-action="${state.signupStep === 4 ? "signup-submit" : "signup-next"}">${state.signupStep === 4 ? "Analyze My Evidence" : "Continue"}</button></div>
        </form><p class="auth-switch">Already have a passport? <a href="#/login">Log in</a></p></div></div></section>`;
    }

    async function fetchProofgraph(force = false) {
        if (state.proofgraph && !force) return state.proofgraph;
        const payload = await apiRequest(`/students/${encodeURIComponent(studentId())}/proofgraph`);
        state.proofgraph = normalizeProofgraph(payload);
        state.evidenceById.clear();
        state.proofgraph.evidence.forEach((item) => {
            if (item?.id) state.evidenceById.set(String(item.id), item);
        });
        return state.proofgraph;
    }

    async function fetchPassport(force = false, issueIfMissing = false) {
        if (state.passport && !force) return state.passport;
        try {
            const payload = await apiRequest(`/students/${encodeURIComponent(studentId())}/passport`);
            state.passport = normalizePassport(payload);
        } catch (error) {
            if (!(error instanceof ApiError) || error.status !== 404) throw error;
            state.passport = null;
        }
        if (!state.passport && issueIfMissing) {
            const payload = await apiRequest(`/students/${encodeURIComponent(studentId())}/passport`, { method: "POST" });
            state.passport = normalizePassport(payload);
        }
        return state.passport;
    }

    async function fetchCore(force = false) {
        const [graphResult, passportResult] = await Promise.allSettled([fetchProofgraph(force), fetchPassport(force, false)]);
        if (graphResult.status === "rejected") throw graphResult.reason;
        if (passportResult.status === "rejected" && !(passportResult.reason instanceof ApiError && passportResult.reason.status === 404)) {
            console.warn("Passport is not issued yet.", passportResult.reason);
        }
        return graphResult.value;
    }

    function dashboardView(graph) {
        const claims = graph.claims;
        const artifactCount = new Set(graph.evidence.map((item) => `${item.source_type || "SOURCE"}:${item.source_ref || item.id || "UNKNOWN"}`)).size;
        const evidenceBacked = claims.filter((claim) => String(claim.state).toUpperCase() === "EVIDENCE_BACKED").length;
        const verified = claims.filter((claim) => String(claim.state).toUpperCase() === "CHALLENGE_VERIFIED").length;
        const challenges = claims.filter((claim) => claim.challenge_available).length;
        const firstName = String(displayName()).split(/\s+/)[0];
        const timeline = [
            ["Evidence connected", `${artifactCount} inspectable artifacts`, artifactCount > 0],
            ["Claims created", `${claims.length} skill claims`, claims.length > 0],
            ["Proof challenges available", `${challenges} supported gaps`, challenges > 0],
            ["Skills challenge verified", `${verified} persistent verification events`, verified > 0],
            ["Opportunity coverage", writeStorageValue(OPPORTUNITY_KEY) ? "Opportunity analyzed" : "Choose an opportunity", Boolean(writeStorageValue(OPPORTUNITY_KEY))],
        ];
        let activeAssigned = false;
        return `<section class="app-page"><div class="shell"><div class="dashboard-hero"><div><p class="eyebrow">Claim → Doubt → Challenge → Proof → Opportunity</p><h1>Welcome, ${e(firstName)}.</h1><p>Your SkillPassport shows what the evidence supports, what remains uncertain, and which proof can close the gap.</p></div><div class="hero-trust-note"><strong>Trust rule</strong><br>Only a deterministic Proof Challenge can promote a claim to Challenge Verified.</div></div>
        <div class="stats-grid"><article class="stat-card"><span class="stat-value">${artifactCount}</span><span class="stat-label">Evidence artifacts</span></article><article class="stat-card"><span class="stat-value">${claims.length}</span><span class="stat-label">Skill claims</span></article><article class="stat-card"><span class="stat-value">${evidenceBacked}</span><span class="stat-label">Evidence-backed skills</span></article><article class="stat-card"><span class="stat-value">${verified}</span><span class="stat-label">Challenge-verified skills</span></article></div>
        <div class="dashboard-grid"><section class="panel"><div class="panel-header"><div><h2>Keep the proof moving</h2><p>Every action advances the same product loop.</p></div></div><div class="action-grid"><button class="action-card" type="button" data-action="analyze-evidence"><span><strong>Analyze Evidence</strong><span>Refresh repository and academic signals</span></span><span class="action-arrow">→</span></button><a class="action-card" href="#/proofgraph"><span><strong>View ProofGraph</strong><span>Inspect every claim and source</span></span><span class="action-arrow">→</span></a><button class="action-card" type="button" data-action="enter-proof-lab"><span><strong>Enter Proof Lab</strong><span>Challenge a supported uncertainty</span></span><span class="action-arrow">→</span></button><a class="action-card" href="#/opportunities"><span><strong>Analyze Opportunity</strong><span>Map proof to Japan or India roles</span></span><span class="action-arrow">→</span></a><a class="action-card" href="#/passport"><span><strong>View SkillPassport</strong><span>Inspect issued skill stamps</span></span><span class="action-arrow">→</span></a></div></section>
        <section class="panel"><div class="panel-header"><div><h2>Trust progression</h2><p>Server-owned state, not browser checkmarks.</p></div></div><ol class="timeline">${timeline.map(([label, detail, done]) => {
            const status = done ? "completed" : !activeAssigned ? "active" : "pending";
            if (!done && !activeAssigned) activeAssigned = true;
            return `<li class="timeline-item ${status}"><span class="timeline-marker" aria-hidden="true">${done ? "✓" : status === "active" ? "•" : "○"}</span><span class="timeline-copy"><strong>${e(label)}</strong><span>${e(detail)}</span></span><span class="timeline-status">${done ? "Complete" : status === "active" ? "Next" : "Pending"}</span></li>`;
        }).join("")}</ol></section></div></div></section>`;
    }

    function writeStorageValue(key) {
        try { return localStorage.getItem(key); } catch (_error) { return null; }
    }

    function evidenceCategory(item) {
        const type = String(item?.source_type || "").toUpperCase();
        if (type === "ACADEMIC") return "Academic";
        if (type === "GITHUB_COMMIT") return "Contribution";
        if (type === "PRIOR_VERIFICATION" || type === "LIVE_PROOF") return "Live Proof";
        return "GitHub";
    }

    function evidenceForClaim(claim, evidence) {
        const ids = new Set(asArray(claim.evidence_ids).map(String));
        if (ids.size) return evidence.filter((item) => ids.has(String(item.id)));
        return evidence.filter((item) => String(item.skill || "").toLowerCase() === String(claim.skill || "").toLowerCase());
    }

    function renderEvidenceNode(item) {
        const isDemoAcademic = String(item.source_type || "").toUpperCase() === "ACADEMIC" && item.metadata?.demo;
        const sourceLabel = isDemoAcademic ? `Demo academic evidence · ${item.source_ref || "Course record"}` : (item.source_ref || titleCase(item.source_type || "Source"));
        return `<button class="evidence-node" type="button" data-action="evidence-detail" data-evidence-id="${e(item.id)}"><strong>${e(item.title || "Evidence item")}</strong><span>${e(sourceLabel)}</span></button>`;
    }

    function claimGraphMarkup(claim, evidence) {
        const items = evidenceForClaim(claim, evidence);
        const groups = { GitHub: [], Contribution: [], Academic: [], "Live Proof": [] };
        items.forEach((item) => groups[evidenceCategory(item)].push(item));

        if (claim.verification_event_id && !groups["Live Proof"].length) {
            const virtual = {
                id: `event:${claim.verification_event_id}`,
                title: "Deterministic verification event",
                source_ref: claim.verification_event_id,
                source_type: "PRIOR_VERIFICATION",
                directness: "DIRECT",
                summary: `${claim.skill} was challenge verified at ${titleCase(claim.verified_level || "the recorded")} level.`,
                metadata: { verification_event_id: claim.verification_event_id, verified_at: claim.last_verified_at },
            };
            state.evidenceById.set(virtual.id, virtual);
            groups["Live Proof"].push(virtual);
        }

        const uncertainty = asArray(claim.uncertainties)[0];
        const challengeLink = String(claim.state).toUpperCase() === "CHALLENGE_VERIFIED"
            ? `<a class="button button-secondary" href="#/passport">View skill stamp</a>`
            : claim.challenge_available
                ? `<a class="button button-amber" href="${routePath("prooflab", claim.id)}">Challenge skill <span aria-hidden="true">→</span></a>`
                : `<span class="muted tiny">No deterministic live proof is available for this skill yet.</span>`;

        return `<article class="claim-graph" id="claim-${e(claim.id)}"><div class="claim-hub"><div><div class="claim-title-row"><h2>${e(claim.skill || "Skill claim")}</h2>${renderTrustBadge(claim.state)}</div><div class="claim-meta"><span class="strength-badge">${e(titleCase(claim.evidence_strength || "Evidence"))} evidence</span>${claim.verified_level ? `<span class="strength-badge">${e(titleCase(claim.verified_level))} level</span>` : ""}</div></div><span class="tiny muted">${items.length} supporting ${items.length === 1 ? "signal" : "signals"}</span></div><div class="proof-branches">${Object.entries(groups).map(([name, branchItems]) => `<section class="proof-branch"><div class="branch-title"><span>${e(name)}</span><span class="branch-count">${branchItems.length}</span></div><div class="evidence-node-list">${branchItems.length ? branchItems.map(renderEvidenceNode).join("") : `<p class="branch-empty">No ${e(name.toLowerCase())} signal attached.</p>`}</div></section>`).join("")}</div><div class="claim-footer"><div class="uncertainty-box"><span class="uncertainty-icon" aria-hidden="true">?</span><div><strong>${uncertainty ? "Remaining uncertainty" : "Trust state"}</strong><p>${e(uncertainty || (String(claim.state).toUpperCase() === "CHALLENGE_VERIFIED" ? "Deterministic execution closed the recorded evidence gap." : "More independent evidence is needed before a live challenge is appropriate."))}</p></div></div>${challengeLink}</div></article>`;
    }

    function proofgraphView(graph) {
        if (!graph.claims.length) {
            return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow">ProofGraph</p><h1>No claims yet</h1><p>Analyze repository and academic evidence to create inspectable skill claims.</p></div></div><div class="empty-state"><div class="empty-content"><div class="empty-icon">PG</div><h2>Your evidence graph starts here.</h2><p>The engine will not invent a skill when no objective signal exists.</p><button class="button button-primary" type="button" data-action="analyze-evidence">Analyze Evidence</button></div></div></div></section>`;
        }
        return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow">ProofGraph</p><h1>Why does this claim exist?</h1><p>Open any evidence node to inspect its source, directness, summary, and provenance.</p></div><button class="button button-secondary" type="button" data-action="analyze-evidence">Refresh evidence</button></div><div class="proofgraph-intro"><div><h2>Evidence makes the claim. A challenge resolves the doubt.</h2><p>Academic evidence corroborates. Repository files and contribution signals show the work. Only deterministic live proof creates the strongest state.</p></div><div class="proofgraph-legend">${renderTrustBadge("DETECTED")}${renderTrustBadge("EVIDENCE_BACKED")}${renderTrustBadge("CHALLENGE_VERIFIED")}</div></div><div class="claim-stack">${graph.claims.map((claim) => claimGraphMarkup(claim, graph.evidence)).join("")}</div></div></section>`;
    }

    async function getChallenge(claimId, force = false) {
        if (state.challengesByClaim.has(claimId) && !force) return state.challengesByClaim.get(claimId);
        const payload = await apiRequest("/challenges", { method: "POST", body: { student_id: studentId(), claim_id: claimId } });
        const challenge = normalizeChallenge(payload);
        if (!challenge?.id) throw new ApiError("The challenge service did not return a challenge ID.");
        state.challengesByClaim.set(claimId, challenge);
        return challenge;
    }

    function challengeResultMarkup(result) {
        if (!result) return "";
        const attempt = unwrap(result, "attempt", "challenge_attempt", "result") || result;
        const event = firstDefined(result.verification_event, result.event, null);
        const verified = Boolean(attempt.passed && event && event.passed !== false);
        const passedTests = Number(attempt.tests_passed || 0);
        const totalTests = Number(attempt.tests_total || 0);
        const tests = asArray(firstDefined(attempt.test_results, result.test_results, []));
        const headline = verified ? "Challenge verified" : attempt.passed ? "Tests passed — confirming the event" : "Proof not established yet";
        const detail = verified
            ? `A persistent verification event promoted this claim at ${titleCase(event.level || "the recorded")} level.`
            : attempt.passed
                ? "The tests passed, but the interface will not claim verification until the server returns a VerificationEvent."
                : "No verified status was created. Review the failed checks, adjust the solution, and submit again.";
        return `<section class="challenge-result" id="challengeResult" aria-live="polite"><div class="result-hero ${verified ? "passed" : "failed"}"><div class="result-score">${passedTests}/${totalTests}</div><div class="result-copy"><p class="eyebrow">Deterministic result</p><h2>${e(headline)}</h2><p>${e(detail)}</p>${verified ? `<p class="tiny"><strong>Verification event:</strong> ${e(event.id || event.verification_id || "Recorded")}</p>` : ""}</div></div><div class="test-results">${tests.length ? tests.map((test) => `<div class="test-result ${test.passed ? "" : "failed"}"><span class="test-result-icon" aria-hidden="true">${test.passed ? "✓" : "×"}</span><span><strong>${e(test.name || "Deterministic check")}</strong><span>${e(test.detail || (test.passed ? "Passed" : "Did not pass"))}</span></span></div>`).join("") : `<p class="muted tiny">The server did not return individual public test details.</p>`}</div></section>`;
    }

    function proofLabView(challenge) {
        const questions = asArray(challenge.concept_questions).slice(0, 2);
        const tests = asArray(challenge.public_tests);
        const context = asArray(challenge.source_context);
        const result = state.challengeResult?.challengeId === challenge.id ? state.challengeResult.payload : null;
        return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow eyebrow-amber">Proof Lab</p><h1>Challenge the exact uncertainty.</h1><p>Concept answers add context. Only deterministic execution tests can create verified status.</p></div><a class="button button-secondary" href="#/proofgraph">Back to ProofGraph</a></div><div class="prooflab-layout"><div><article class="challenge-card"><header class="challenge-header"><div class="challenge-meta"><span class="source-badge">${e(challenge.skill || "Skill")}</span><span class="source-badge">${e(titleCase(challenge.level || "Foundation"))}</span><span class="source-badge">${e(titleCase(challenge.challenge_type || "Proof task"))}</span></div><h1>${e(challenge.title || "Proof Challenge")}</h1><p>${e(challenge.instructions || "Complete the constrained task, then run deterministic verification.")}</p></header><form id="challengeForm" data-challenge-id="${e(challenge.id)}" class="challenge-body"><section class="challenge-section"><h2>Stage 1 · Evidence-gap concept check</h2><p>Two targeted questions clarify how you reason about the gap. This stage alone cannot verify the skill.</p><div class="question-list">${questions.length ? questions.map((question, questionIndex) => `<fieldset class="concept-question"><legend>${questionIndex + 1}. ${e(question.prompt || "Concept question")}</legend><div class="option-list">${asArray(question.options).map((option, optionIndex) => `<label class="radio-option"><input type="radio" name="concept:${e(question.id)}" value="${optionIndex}" ${optionIndex === 0 ? "required" : ""}><span>${e(option)}</span></label>`).join("")}</div></fieldset>`).join("") : `<p class="form-error">This challenge is missing its server-authored concept questions. Reload the challenge before submitting.</p>`}</div></section><section class="challenge-section"><div class="editor-header"><div><h2>Stage 2 · Live proof task</h2><p class="muted tiny">Submit only the constrained solution shown here—never shell commands.</p></div>${challenge.demo_solution ? `<button class="button button-secondary button-small" type="button" data-action="load-demo-solution" data-challenge-id="${e(challenge.id)}">Load judge-demo response</button>` : ""}</div><label class="fieldset-label" for="solutionEditor">Solution</label><textarea class="code-editor" id="solutionEditor" name="solution" required spellcheck="false" aria-describedby="solutionHelp">${e(challenge.starter_code || "")}</textarea><p class="field-help" id="solutionHelp">The server runs bounded deterministic checks. It does not accept a client-provided pass state.</p></section><button class="button button-primary button-block" type="submit" ${questions.length < 2 ? "disabled" : ""}>Run deterministic verification</button></form></article>${challengeResultMarkup(result)}</div><aside class="challenge-aside"><section class="aside-card"><p class="eyebrow">Adaptive level</p><h2>${e(titleCase(challenge.level || "Foundation"))}</h2><p>${e(challenge.rationale || "Challenge level is selected from the directness, breadth, contribution, and recency of the evidence.")}</p></section><section class="aside-card"><h2>Evidence context</h2><ul class="aside-list">${context.length ? context.map((item) => `<li>• ${e(item)}</li>`).join("") : `<li>The claim's attached evidence defines this task.</li>`}</ul></section><section class="aside-card"><h2>Public checks</h2><ul class="test-list">${tests.length ? tests.map((test) => `<li class="public-test"><span class="test-icon" aria-hidden="true">✓</span><span><strong>${e(test.name || "Check")}</strong><br><span class="muted">${e(test.description || "Deterministic expected behavior")}</span></span></li>`).join("") : `<li class="muted">Public checks will appear when the challenge loads.</li>`}</ul></section><section class="aside-card"><h2>Trust boundary</h2><p>Gemini may personalize challenge wording. The proof engine owns hidden tests, pass status, level, and the verification hash.</p></section></aside></div></div></section>`;
    }

    async function fetchOpportunities(force = false) {
        if (state.opportunities.length && !force) return state.opportunities;
        const payload = await apiRequest("/opportunities");
        state.opportunities = normalizeOpportunities(payload);
        return state.opportunities;
    }

    async function fetchCoverage(opportunityId) {
        const payload = await apiRequest(`/opportunities/${encodeURIComponent(opportunityId)}?student_id=${encodeURIComponent(studentId())}`);
        const coverage = normalizeCoverage(payload);
        if (!coverage) throw new ApiError("The opportunity API did not return requirement coverage.");
        state.coverage = coverage;
        writeStorage(OPPORTUNITY_KEY, opportunityId);
        return coverage;
    }

    function opportunityCardMarkup(opportunity) {
        return `<button class="opportunity-card" type="button" data-action="select-opportunity" data-opportunity-id="${e(opportunity.id)}"><span><h3>${e(opportunity.title || "Technical opportunity")}</h3><p>${e(opportunity.company || "Company")} · ${e(opportunity.country || "Japan / India")}</p></span><span class="action-arrow" aria-hidden="true">→</span></button>`;
    }

    function coverageMarkup(coverage) {
        if (!coverage) return `<div class="coverage-empty"><div><div class="empty-icon">OL</div><h2>Choose or paste an opportunity.</h2><p>Opportunity Lens will show which requirements are challenge verified, evidence backed, detected, or missing.</p></div></div>`;
        const opportunity = coverage.opportunity || {};
        const matches = asArray(coverage.matches);
        return `<section class="coverage-card" aria-live="polite"><header class="coverage-header"><p class="eyebrow">Verified coverage</p><h2>${e(opportunity.title || "Analyzed opportunity")}</h2><p>${e(opportunity.company || "Opportunity")} · ${e(opportunity.country || "Japan / India")} · Original language: ${e(opportunity.original_language || "English")}</p></header><div class="coverage-summary"><div class="coverage-stat"><strong>${Number(coverage.required_challenge_verified || 0)}</strong><span>Required verified</span></div><div class="coverage-stat"><strong>${Number(coverage.required_evidence_backed || 0)}</strong><span>Required evidence backed</span></div><div class="coverage-stat"><strong>${Number(coverage.required_detected || 0)}</strong><span>Required detected</span></div><div class="coverage-stat"><strong>${Number(coverage.required_missing || 0)}</strong><span>Required missing</span></div></div><div class="requirement-list">${matches.map((match) => {
            const requirement = match.requirement || {};
            const action = match.action_available
                ? `<button class="button button-secondary button-small" type="button" data-action="prove-requirement" data-claim-id="${e(match.matched_claim_id || "")}" data-skill="${e(requirement.skill || "")}">Prove this skill</button>`
                : `<span class="tiny muted">${String(match.state).toUpperCase() === "CHALLENGE_VERIFIED" ? "Proven" : "No live proof"}</span>`;
            return `<article class="requirement-row"><div class="requirement-skill"><strong>${e(requirement.skill || "Capability")}</strong><span class="importance-badge ${String(requirement.importance).toUpperCase() === "PREFERRED" ? "importance-preferred" : ""}">${e(titleCase(requirement.importance || "Required"))}</span></div><div><div>${renderTrustBadge(match.state || "MISSING")}</div><p class="requirement-reason">${e(match.reason || requirement.source_text || "No matched claim was returned.")}</p></div>${action}</article>`;
        }).join("")}</div><div class="coverage-explanation"><strong>Transparent result:</strong> ${e(coverage.explanation || `${Number(coverage.required_challenge_verified || 0)} of ${Number(coverage.required_total || 0)} required capabilities are execution verified.`)}</div></section>`;
    }

    function opportunitiesView(opportunities) {
        return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow">Opportunity Lens</p><h1>What does this proof unlock?</h1><p>Paste English, Japanese, or mixed text—or browse the curated Tokyo and Bengaluru demo opportunities.</p></div></div><div class="opportunity-layout"><section class="opportunity-input-card"><h2>Paste an opportunity</h2><p>Gemini can interpret unstructured text when configured. The matching engine owns the requirement comparison.</p><form id="opportunityForm"><div class="compact-fields"><div class="field"><label for="opportunityTitle">Role title</label><input id="opportunityTitle" name="title" value="Tokyo Backend Internship" required></div><div class="field"><label for="opportunityCountry">Country</label><select id="opportunityCountry" name="country"><option>Japan</option><option>India</option><option>Japan / India</option></select></div></div><div class="field-full"><label for="opportunityCompany">Company</label><input id="opportunityCompany" name="company" value="Demo Technology Partner" required></div><div class="field-full"><label for="opportunityDescription">Description</label><textarea class="opportunity-textarea" id="opportunityDescription" name="description" minlength="20" required placeholder="Python と FastAPI を用いたバックエンド開発。SQL experience required; Docker preferred."></textarea></div><button class="button button-primary button-block" type="submit">Analyze requirements</button></form><div class="opportunity-list"><p class="fieldset-label">Curated Japan / India opportunities</p>${opportunities.length ? opportunities.map(opportunityCardMarkup).join("") : `<p class="muted tiny">No curated opportunities were returned.</p>`}</div></section><div>${coverageMarkup(state.coverage)}</div></div></div></section>`;
    }

    function skillStampMarkup(stamp) {
        const sources = asArray(stamp.evidence_sources).join(" + ") || "Inspectable evidence + live proof";
        return `<article class="skill-stamp"><header class="stamp-header"><div><h2>${e(stamp.skill || "Verified skill")}</h2><span class="stamp-level">${e(titleCase(stamp.verified_level || "Recorded"))} level</span></div>${renderTrustBadge(stamp.trust_state || "CHALLENGE_VERIFIED")}</header><dl class="stamp-details"><div class="stamp-detail"><dt>Evidence</dt><dd>${e(sources)}</dd></div><div class="stamp-detail"><dt>Verification</dt><dd>${e(stamp.verification_method || "Repo-grounded execution challenge")}</dd></div><div class="stamp-detail"><dt>Issued</dt><dd>${e(formatDate(stamp.verification_date))}</dd></div><div class="stamp-detail"><dt>Event ID</dt><dd class="hash">${e(stamp.verification_event_id || "Not recorded")}</dd></div><div class="stamp-detail"><dt>Freshness</dt><dd>${e(stamp.freshness || "Current")}</dd></div><div class="stamp-detail"><dt>Integrity hash</dt><dd class="hash" title="${e(stamp.integrity_hash || "")}">${e(shortHash(stamp.integrity_hash))}</dd></div></dl><a class="button button-secondary button-small" href="#/proofgraph">View Proof</a></article>`;
    }

    function passportMarkup(passport, isPublic = false) {
        const name = passport.candidate_display_name || displayName();
        const stamps = asArray(passport.stamps);
        const publicUrl = publicVerificationUrl(passport.id);
        const qrOrigin = PUBLIC_APP_BASE || window.location.origin;
        return `${isPublic ? `<div class="public-banner"><strong>Public read-only verification.</strong> This page shows issued skill stamps and their integrity references. It does not expose candidate submissions.</div>` : ""}<article class="passport-sheet"><header class="passport-cover"><div class="passport-person"><span class="passport-avatar" aria-hidden="true">${e(initials(name))}</span><div><p class="eyebrow">SkillPassport</p><h1>${e(name)}</h1><p>${e(passport.headline || "Inspectable evidence and challenge-verified capability")}</p></div></div><div class="passport-id-block"><span>Passport ID</span><strong>${e(passport.id)}</strong><span>Updated ${e(formatDate(passport.updated_at || passport.issued_at))}</span></div></header><div class="passport-body">${isPublic ? "" : `<div class="passport-toolbar"><p>${stamps.length} issued ${stamps.length === 1 ? "Skill Stamp" : "Skill Stamps"}, derived from persistent VerificationEvents.</p><div class="inline-actions"><button class="button button-secondary button-small" type="button" data-action="share-passport" data-passport-id="${e(passport.id)}">Share public link</button><button class="button button-primary button-small" type="button" data-action="print-passport">Download / Print</button></div></div>`}<div class="stamp-grid">${stamps.length ? stamps.map(skillStampMarkup).join("") : `<div class="empty-state"><div class="empty-content"><div class="empty-icon">SP</div><h2>No stamps issued yet.</h2><p>A Skill Stamp appears only after a deterministic challenge creates a VerificationEvent.</p>${isPublic ? "" : `<a class="button button-primary" href="#/proofgraph">Find a proof challenge</a>`}</div></div>`}</div>${isPublic ? "" : `<section class="passport-share-panel"><div><h2>Public verification</h2><p>Share an actual read-only verification route. The QR resolves to the same URL.</p><p class="hash">${e(publicUrl)}</p></div><div class="qr-wrap"><img src="${API_BASE}/public/passports/${encodeURIComponent(passport.id)}/qr.png?origin=${encodeURIComponent(qrOrigin)}" alt="QR code for the public SkillPassport verification page"><span class="qr-fallback" hidden>QR unavailable. Use Share public link.</span></div></section>`}</div></article>`;
    }

    function passportView(passport) {
        if (!passport) {
            return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow">SkillPassport</p><h1>Issue your inspectable passport.</h1><p>The passport is built from persisted VerificationEvents—not browser state.</p></div></div><div class="empty-state"><div class="empty-content"><div class="empty-icon">SP</div><h2>No passport has been issued.</h2><p>Issue it now. Only challenge-verified claims will become Skill Stamps.</p><button class="button button-primary" type="button" data-action="issue-passport">Issue SkillPassport</button></div></div></div></section>`;
        }
        return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow">Your SkillPassport</p><h1>Proof that can be inspected.</h1><p>Every Skill Stamp links a demonstrated level to its evidence and deterministic verification event.</p></div></div>${passportMarkup(passport, false)}</div></section>`;
    }

    function publicPassportView(passport) {
        return `<section class="app-page"><div class="shell"><div class="page-header"><div><p class="eyebrow">Public verification</p><h1>Inspect issued proof.</h1><p>This read-only view reports exactly what the SkillPassport verification store contains.</p></div></div>${passportMarkup(passport, true)}</div></section>`;
    }

    function notFoundView() {
        return `<section class="error-view"><div class="error-content"><div class="error-icon" aria-hidden="true">?</div><p class="eyebrow">404</p><h1>This route is not part of the proof graph.</h1><p>Return to the landing page or open your dashboard.</p><div class="inline-actions"><a class="button button-primary" href="#/">Go home</a>${state.session ? `<a class="button button-secondary" href="#/dashboard">Open dashboard</a>` : ""}</div></div></section>`;
    }

    async function renderRoute() {
        const route = parseRoute();
        if (route.name === "signup" && state.lastRouteName !== "signup") state.signupStep = 1;
        state.lastRouteName = route.name;
        const version = ++state.routeVersion;
        state.mobileNavOpen = false;
        updateChrome(route);

        if (PROTECTED_ROUTES.has(route.name) && !studentId()) {
            toast("Log in or choose View Judge Demo to open that page.", "error");
            navigate("/login");
            return;
        }

        if (route.name === "landing") main.innerHTML = landingView();
        else if (route.name === "login") main.innerHTML = loginView();
        else if (route.name === "signup") main.innerHTML = signupView();
        else if (route.name === "notfound") main.innerHTML = notFoundView();
        else {
            startRouteProgress();
            main.innerHTML = loadingView();
            try {
                if (route.name === "dashboard") {
                    const graph = await fetchCore(true);
                    if (version !== state.routeVersion) return;
                    main.innerHTML = dashboardView(graph);
                } else if (route.name === "proofgraph") {
                    const graph = await fetchProofgraph(true);
                    if (version !== state.routeVersion) return;
                    main.innerHTML = proofgraphView(graph);
                } else if (route.name === "prooflab") {
                    if (!route.parameter) throw new ApiError("Choose a skill claim from ProofGraph before opening Proof Lab.");
                    await fetchProofgraph(false);
                    const claim = state.proofgraph.claims.find((item) => String(item.id) === route.parameter);
                    if (!claim) throw new ApiError("That skill claim was not found.", 404);
                    if (!claim.challenge_available && String(claim.state).toUpperCase() !== "CHALLENGE_VERIFIED") throw new ApiError("A deterministic live proof is not available for that claim.", 409);
                    const challenge = await getChallenge(route.parameter);
                    if (version !== state.routeVersion) return;
                    main.innerHTML = proofLabView(challenge);
                } else if (route.name === "opportunities") {
                    const opportunities = await fetchOpportunities(true);
                    const lastId = writeStorageValue(OPPORTUNITY_KEY);
                    if (lastId && (!state.coverage || state.coverage.opportunity?.id !== lastId)) {
                        try { await fetchCoverage(lastId); } catch (_error) { state.coverage = null; }
                    }
                    if (version !== state.routeVersion) return;
                    main.innerHTML = opportunitiesView(opportunities);
                } else if (route.name === "passport") {
                    const passport = await fetchPassport(true, false);
                    if (version !== state.routeVersion) return;
                    main.innerHTML = passportView(passport);
                } else if (route.name === "verify") {
                    if (!route.parameter) throw new ApiError("The public verification URL is missing its passport ID.", 404);
                    const payload = await apiRequest(`/public/passports/${encodeURIComponent(route.parameter)}`);
                    const passport = normalizePassport(payload);
                    if (!passport) throw new ApiError("No public SkillPassport exists for this ID.", 404);
                    if (version !== state.routeVersion) return;
                    main.innerHTML = publicPassportView(passport);
                }
            } catch (error) {
                if (version !== state.routeVersion) return;
                const context = route.name === "verify" && error.status === 404 ? "public passport" : route.name;
                main.innerHTML = errorView(error, context);
            } finally {
                finishRouteProgress();
            }
        }

        window.scrollTo({ top: 0, behavior: "instant" });
        window.requestAnimationFrame(() => main.focus({ preventScroll: true }));
    }

    function visibleSignupStep() {
        return document.querySelector(`[data-signup-step="${state.signupStep}"]`);
    }

    function validateSignupStep() {
        const panel = visibleSignupStep();
        if (!panel) return true;
        const fields = [...panel.querySelectorAll("input, select, textarea")].filter((field) => !field.closest("[hidden]") && !field.disabled);
        for (const field of fields) {
            if (!field.checkValidity()) {
                field.reportValidity();
                field.focus();
                return false;
            }
        }
        return true;
    }

    function updateSignupUI() {
        document.querySelectorAll("[data-signup-step]").forEach((panel) => { panel.hidden = Number(panel.dataset.signupStep) !== state.signupStep; });
        document.querySelectorAll("[data-stepper]").forEach((step) => {
            const number = Number(step.dataset.stepper);
            step.className = `stepper-item ${number === state.signupStep ? "active" : number < state.signupStep ? "done" : ""}`;
        });
        const back = document.querySelector('[data-action="signup-back"]');
        const next = document.querySelector('[data-action="signup-next"], [data-action="signup-submit"]');
        if (back) back.disabled = state.signupStep === 1;
        if (next) {
            next.dataset.action = state.signupStep === 4 ? "signup-submit" : "signup-next";
            next.type = state.signupStep === 4 ? "submit" : "button";
            next.textContent = state.signupStep === 4 ? "Analyze My Evidence" : "Continue";
        }
        if (state.signupStep === 4) updateSignupReview();
        const heading = visibleSignupStep()?.querySelector("h2");
        if (heading) heading.focus?.();
    }

    function updateSignupReview() {
        const form = document.getElementById("signupForm");
        if (!form) return;
        const data = new FormData(form);
        const set = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
        set("reviewName", String(data.get("name") || "—"));
        set("reviewInstitution", `${data.get("institution") || "—"} · ${data.get("country") || "—"}`);
        set("reviewRepository", String(data.get("repository_url") || "Demo repository fallback"));
        set("reviewAcademic", data.get("academic_source") === "manual" ? `Manual: ${data.get("course_name") || "coursework"}` : "Demo academic evidence");
    }

    async function analyzeEvidence(button = null) {
        setButtonBusy(button, true, "Analyzing…");
        try {
            await apiRequest("/evidence/analyze", {
                method: "POST",
                body: {
                    student_id: studentId(),
                    repository_url: state.session?.repository_url || null,
                    github_username: state.session?.github_username || null,
                    use_demo_fallback: true,
                },
            });
            state.proofgraph = null;
            state.passport = null;
            await fetchProofgraph(true);
            toast("Evidence analyzed. ProofGraph now shows the server's claim state.");
            navigate("/proofgraph");
        } catch (error) {
            toast(error.message, "error");
        } finally {
            setButtonBusy(button, false);
        }
    }

    async function handleJudgeDemo(button) {
        setButtonBusy(button, true, "Resetting demo…");
        try {
            const payload = await apiRequest("/demo/reset", { method: "POST" });
            setSession(normalizeSession(payload));
            state.proofgraph = null;
            state.passport = null;
            state.coverage = null;
            state.challengesByClaim.clear();
            writeStorage(OPPORTUNITY_KEY, null);
            toast("Judge Demo restored to a known deterministic state.");
            navigate("/dashboard");
        } catch (error) {
            toast(error.message, "error");
            setButtonBusy(button, false);
        }
    }

    async function handleLogin(form, button) {
        const data = new FormData(form);
        const errorNode = document.getElementById("loginError");
        errorNode.hidden = true;
        setButtonBusy(button, true, "Logging in…");
        try {
            const payload = await apiRequest("/auth/login", { method: "POST", body: { email: String(data.get("email") || ""), password: String(data.get("password") || "") } });
            setSession(normalizeSession(payload));
            form.reset();
            toast("Welcome back. Your trust state was loaded from the server.");
            navigate("/dashboard");
        } catch (error) {
            errorNode.textContent = error.message;
            errorNode.hidden = false;
            setButtonBusy(button, false);
        }
    }

    function signupPayload(form) {
        const data = new FormData(form);
        const academicSource = String(data.get("academic_source") || "demo");
        const manualCoursework = academicSource === "manual" && data.get("course_name")
            ? [{
                course_name: String(data.get("course_name") || ""),
                grade: String(data.get("course_grade") || ""),
                skills: String(data.get("course_skills") || "").split(",").map((skill) => skill.trim()).filter(Boolean),
            }]
            : [];
        return {
            name: String(data.get("name") || ""),
            email: String(data.get("email") || ""),
            password: String(data.get("password") || ""),
            institution: String(data.get("institution") || ""),
            country: String(data.get("country") || ""),
            study_area: String(data.get("study_area") || ""),
            github_username: String(data.get("github_username") || "") || null,
            repository_url: String(data.get("repository_url") || "") || null,
            academic_source: academicSource,
            manual_coursework: manualCoursework,
        };
    }

    async function handleSignup(form, button) {
        if (!validateSignupStep()) return;
        const errorNode = document.getElementById("signupError");
        errorNode.hidden = true;
        const payload = signupPayload(form);
        setButtonBusy(button, true, "Creating claims…");
        try {
            const response = await apiRequest("/auth/signup", { method: "POST", body: payload });
            setSession({ ...normalizeSession(response), repository_url: payload.repository_url, github_username: payload.github_username });
            await apiRequest("/evidence/analyze", { method: "POST", body: { student_id: studentId(), repository_url: payload.repository_url, github_username: payload.github_username, use_demo_fallback: true } });
            form.reset();
            state.signupDraft = {};
            state.signupStep = 1;
            state.proofgraph = null;
            toast("Your evidence was analyzed and your first claims are ready.");
            navigate("/dashboard");
        } catch (error) {
            errorNode.textContent = error.status === 422 ? `Check the highlighted setup details. ${error.message}` : error.message;
            errorNode.hidden = false;
            setButtonBusy(button, false);
        }
    }

    async function handleChallengeSubmit(form, button) {
        if (!form.reportValidity()) return;
        const challengeId = form.dataset.challengeId;
        const data = new FormData(form);
        const conceptAnswers = {};
        for (const [key, value] of data.entries()) {
            if (key.startsWith("concept:")) conceptAnswers[key.slice(8)] = Number(value);
        }
        setButtonBusy(button, true, "Running deterministic tests…");
        try {
            const payload = await apiRequest(`/challenges/${encodeURIComponent(challengeId)}/submit`, { method: "POST", body: { student_id: studentId(), concept_answers: conceptAnswers, solution: String(data.get("solution") || "") } });
            state.challengeResult = { challengeId, payload };
            const event = firstDefined(payload?.verification_event, payload?.event, null);
            if (event) {
                state.proofgraph = null;
                state.passport = null;
                await Promise.allSettled([fetchProofgraph(true), fetchPassport(true, false)]);
                const lastId = writeStorageValue(OPPORTUNITY_KEY);
                if (lastId) await fetchCoverage(lastId).catch(() => null);
                toast("Deterministic tests passed. The VerificationEvent is now reflected across SkillPassport.");
            } else {
                const attempt = unwrap(payload, "attempt", "challenge_attempt", "result") || payload;
                toast(attempt?.passed ? "Tests passed, but no VerificationEvent was returned." : "Proof not established. No verified state was created.", attempt?.passed ? "error" : "error");
            }
            await renderRoute();
            window.setTimeout(() => document.getElementById("challengeResult")?.scrollIntoView({ behavior: "smooth", block: "center" }), 20);
        } catch (error) {
            toast(error.message, "error");
            setButtonBusy(button, false);
        }
    }

    async function handleOpportunitySubmit(form, button) {
        if (!form.reportValidity()) return;
        const data = new FormData(form);
        setButtonBusy(button, true, "Interpreting requirements…");
        try {
            const payload = await apiRequest("/opportunities/analyze", { method: "POST", body: { student_id: studentId(), title: String(data.get("title") || "Pasted opportunity"), company: String(data.get("company") || "Opportunity"), country: String(data.get("country") || "Japan / India"), description: String(data.get("description") || "") } });
            const coverage = normalizeCoverage(payload);
            if (!coverage) throw new ApiError("No structured requirements were found. Add more detail about the technical role.");
            state.coverage = coverage;
            if (coverage.opportunity?.id) writeStorage(OPPORTUNITY_KEY, coverage.opportunity.id);
            main.innerHTML = opportunitiesView(state.opportunities);
            toast("Opportunity requirements were compared with your server-owned claim states.");
        } catch (error) {
            toast(error.message, "error");
            setButtonBusy(button, false);
        }
    }

    async function handleSelectOpportunity(button) {
        setButtonBusy(button, true, "Comparing…");
        try {
            await fetchCoverage(button.dataset.opportunityId);
            main.innerHTML = opportunitiesView(state.opportunities);
            toast("Curated opportunity coverage is ready.");
        } catch (error) {
            toast(error.message, "error");
            setButtonBusy(button, false);
        }
    }

    async function handleProveRequirement(button) {
        let claimId = button.dataset.claimId;
        if (!claimId) {
            try {
                const graph = await fetchProofgraph(false);
                claimId = graph.claims.find((claim) => String(claim.skill || "").toLowerCase() === String(button.dataset.skill || "").toLowerCase() && claim.challenge_available)?.id;
            } catch (error) {
                toast(error.message, "error");
                return;
            }
        }
        if (!claimId) {
            toast("This missing capability does not yet have enough evidence for a deterministic challenge.", "error");
            navigate("/proofgraph");
            return;
        }
        navigate(`/prooflab/${encodeURIComponent(claimId)}`);
    }

    function showEvidenceDetail(id) {
        const item = state.evidenceById.get(String(id));
        if (!item) {
            toast("That evidence item is no longer attached to the current graph.", "error");
            return;
        }
        evidenceDialogTitle.textContent = item.title || "Evidence detail";
        const metadata = item.metadata && typeof item.metadata === "object" ? item.metadata : {};
        const sourceTypeLabel = String(item.source_type).toUpperCase() === "ACADEMIC" && metadata.demo ? "Demo academic evidence" : titleCase(item.source_type || "Evidence");
        evidenceDialogBody.innerHTML = `<div class="dialog-body"><p>${e(item.summary || "No summary was provided.")}</p><dl class="detail-grid"><dt>Skill</dt><dd>${e(item.skill || "Attached claim")}</dd><dt>Source type</dt><dd>${e(sourceTypeLabel)}</dd><dt>Source reference</dt><dd class="hash">${e(item.source_ref || "Not recorded")}</dd><dt>Directness</dt><dd>${e(titleCase(item.directness || "Contextual"))}</dd><dt>Recorded</dt><dd>${e(formatDate(item.created_at))}</dd></dl><section class="provenance-block"><h3>Provenance metadata</h3><pre class="provenance-code">${e(JSON.stringify(metadata, null, 2) || "{}")}</pre></section></div>`;
        if (typeof evidenceDialog.showModal === "function") evidenceDialog.showModal();
        else evidenceDialog.setAttribute("open", "");
    }

    async function copyText(text) {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return;
        }
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        textarea.remove();
        if (!copied) throw new Error("Copy was not available in this browser.");
    }

    main.addEventListener("click", async (event) => {
        const control = event.target.closest("[data-action]");
        if (!control) return;
        const action = control.dataset.action;
        if (action === "judge-demo") await handleJudgeDemo(control);
        else if (action === "logout") { clearSession(); toast("You are logged out. Local session state was cleared."); navigate("/"); }
        else if (action === "analyze-evidence") await analyzeEvidence(control);
        else if (action === "retry-route") await renderRoute();
        else if (action === "signup-next") { if (validateSignupStep()) { state.signupStep = Math.min(4, state.signupStep + 1); updateSignupUI(); } }
        else if (action === "signup-back") { state.signupStep = Math.max(1, state.signupStep - 1); updateSignupUI(); }
        else if (action === "signup-submit") { /* The form submit event owns the request. */ }
        else if (action === "enter-proof-lab") {
            const graph = await fetchProofgraph(false).catch((error) => { toast(error.message, "error"); return null; });
            if (!graph) return;
            const claim = graph.claims.find((item) => item.challenge_available);
            if (claim) navigate(`/prooflab/${encodeURIComponent(claim.id)}`);
            else { toast("Analyze or inspect evidence before opening a supported challenge.", "error"); navigate("/proofgraph"); }
        } else if (action === "evidence-detail") showEvidenceDetail(control.dataset.evidenceId);
        else if (action === "load-demo-solution") {
            const route = parseRoute();
            const challenge = state.challengesByClaim.get(route.parameter);
            const editor = document.getElementById("solutionEditor");
            if (challenge?.demo_solution && editor) { editor.value = challenge.demo_solution; editor.focus(); toast("Judge-demo response loaded. Submit it to run the real deterministic tests."); }
        } else if (action === "select-opportunity") await handleSelectOpportunity(control);
        else if (action === "prove-requirement") await handleProveRequirement(control);
        else if (action === "issue-passport") {
            setButtonBusy(control, true, "Issuing…");
            try { await fetchPassport(true, true); toast("SkillPassport issued from persistent verification events."); await renderRoute(); } catch (error) { toast(error.message, "error"); setButtonBusy(control, false); }
        } else if (action === "share-passport") {
            const url = publicVerificationUrl(control.dataset.passportId);
            try { await copyText(url); toast("Public verification link copied."); } catch (error) { toast(error.message, "error"); }
        } else if (action === "print-passport") window.print();
    });

    header.addEventListener("click", (event) => {
        const control = event.target.closest("[data-action]");
        if (!control) return;
        if (control.dataset.action === "logout") { clearSession(); toast("You are logged out. Local session state was cleared."); navigate("/"); }
        if (control.dataset.action === "toggle-menu") {
            state.mobileNavOpen = !state.mobileNavOpen;
            const nav = document.getElementById("appNav");
            nav?.classList.toggle("open", state.mobileNavOpen);
            control.setAttribute("aria-expanded", String(state.mobileNavOpen));
        }
    });

    main.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.target;
        const button = event.submitter || form.querySelector('button[type="submit"]');
        if (form.id === "loginForm") await handleLogin(form, button);
        else if (form.id === "signupForm") await handleSignup(form, button);
        else if (form.id === "challengeForm") await handleChallengeSubmit(form, button);
        else if (form.id === "opportunityForm") await handleOpportunitySubmit(form, button);
    });

    main.addEventListener("change", (event) => {
        if (event.target.name === "academic_source") {
            const manual = document.getElementById("manualCoursework");
            const isManual = event.target.value === "manual";
            manual.hidden = !isManual;
            manual.querySelectorAll("input").forEach((input) => { input.required = isManual && input.name === "course_name"; });
        }
    });

    evidenceDialog.addEventListener("click", (event) => {
        const close = event.target.closest('[data-action="close-evidence"]');
        if (close || event.target === evidenceDialog) evidenceDialog.close();
    });

    main.addEventListener("error", (event) => {
        if (event.target.matches(".qr-wrap img")) {
            event.target.hidden = true;
            const fallback = event.target.parentElement.querySelector(".qr-fallback");
            if (fallback) fallback.hidden = false;
        }
    }, true);

    window.addEventListener("hashchange", renderRoute);

    if (!window.location.hash) {
        window.location.replace(`${window.location.pathname}${window.location.search}#/`);
    } else {
        renderRoute();
    }
})();
