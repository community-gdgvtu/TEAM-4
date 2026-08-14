import { copyFile, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = dirname(scriptsDirectory);
const outputDirectory = join(frontendDirectory, "dist");

function publicUrl(name, value) {
    const candidate = String(value || "").trim().replace(/\/+$/, "");
    if (!candidate) return "";
    let parsed;
    try {
        parsed = new URL(candidate);
    } catch (_error) {
        throw new Error(`${name} must be an absolute HTTP(S) URL.`);
    }
    if (!new Set(["http:", "https:"]).has(parsed.protocol)) {
        throw new Error(`${name} must use HTTP or HTTPS.`);
    }
    if (parsed.username || parsed.password) {
        throw new Error(`${name} must not include URL credentials.`);
    }
    if (parsed.search || parsed.hash) {
        throw new Error(`${name} must not include a query string or fragment.`);
    }
    return parsed.href.replace(/\/+$/, "");
}

const apiBase = publicUrl(
    "SKILLPASSPORT_API_BASE_URL",
    process.env.SKILLPASSPORT_API_BASE_URL || process.env.VITE_API_BASE_URL || "",
);
const publicAppBase = publicUrl(
    "PUBLIC_APP_BASE_URL",
    process.env.PUBLIC_APP_BASE_URL || process.env.URL || process.env.DEPLOY_PRIME_URL || "",
);

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });

for (const asset of ["app.js", "styles.css", "og.png"]) {
    await copyFile(join(frontendDirectory, asset), join(outputDirectory, asset));
}

const sourceIndex = await readFile(join(frontendDirectory, "index.html"), "utf8");
const socialCardUrl = publicAppBase ? `${publicAppBase}/og.png` : "/og.png";
await writeFile(
    join(outputDirectory, "index.html"),
    sourceIndex.replaceAll("__OG_IMAGE__", socialCardUrl),
    "utf8",
);

const runtimeSource = `// Generated at deploy time. Contains public URLs only.\nwindow.SKILLPASSPORT_CONFIG = Object.freeze(${JSON.stringify({ apiBase, publicAppBase }, null, 4)});\n`;
await writeFile(join(outputDirectory, "runtime-config.js"), runtimeSource, "utf8");

console.log(`Netlify bundle ready: ${outputDirectory}`);
console.log(`API base: ${apiBase || "same-origin /api"}`);
console.log(`Public app base: ${publicAppBase || "current origin"}`);
