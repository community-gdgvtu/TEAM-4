import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const scriptsDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = dirname(scriptsDirectory);
const buildScript = join(scriptsDirectory, "build-netlify.mjs");
const outputDirectory = join(frontendDirectory, "dist");
const publicEnvironmentKeys = [
    "SKILLPASSPORT_API_BASE_URL",
    "VITE_API_BASE_URL",
    "PUBLIC_APP_BASE_URL",
    "URL",
    "DEPLOY_PRIME_URL",
];

function runBuild(overrides = {}) {
    const environment = { ...process.env };
    for (const key of publicEnvironmentKeys) delete environment[key];
    Object.assign(environment, overrides);
    return spawnSync(process.execPath, [buildScript], {
        cwd: frontendDirectory,
        encoding: "utf8",
        env: environment,
    });
}

test("Netlify build emits safe runtime configuration", async (context) => {
    await context.test("uses same-origin defaults without shipping the social placeholder", async () => {
        const result = runBuild();
        assert.equal(result.status, 0, result.stderr);
        const runtime = await readFile(join(outputDirectory, "runtime-config.js"), "utf8");
        const index = await readFile(join(outputDirectory, "index.html"), "utf8");
        assert.match(runtime, /"apiBase": ""/);
        assert.match(runtime, /"publicAppBase": ""/);
        assert.doesNotMatch(index, /__OG_IMAGE__/);
        assert.match(index, /content="\/og\.png"/);
    });

    await context.test("uses only explicitly public deployment URLs", async () => {
        const secretSentinel = "must-not-enter-the-static-bundle";
        const result = runBuild({
            SKILLPASSPORT_API_BASE_URL: "https://api.skillpassport.example/api/",
            PUBLIC_APP_BASE_URL: "https://skillpassport.example/",
            GEMINI_API_KEY: secretSentinel,
            MONGODB_URI: `mongodb://${secretSentinel}`,
        });
        assert.equal(result.status, 0, result.stderr);
        const runtime = await readFile(join(outputDirectory, "runtime-config.js"), "utf8");
        const index = await readFile(join(outputDirectory, "index.html"), "utf8");
        assert.match(runtime, /https:\/\/api\.skillpassport\.example\/api/);
        assert.match(runtime, /https:\/\/skillpassport\.example/);
        assert.match(index, /https:\/\/skillpassport\.example\/og\.png/);
        assert.doesNotMatch(runtime, new RegExp(secretSentinel));
        assert.doesNotMatch(index, new RegExp(secretSentinel));
    });

    await context.test("rejects non-HTTP API configuration", () => {
        const result = runBuild({ SKILLPASSPORT_API_BASE_URL: "file:///tmp/not-an-api" });
        assert.notEqual(result.status, 0);
        assert.match(result.stderr, /must use HTTP or HTTPS/);
    });

    await context.test("rejects credentials and token-like URL components", () => {
        const credentialResult = runBuild({
            SKILLPASSPORT_API_BASE_URL: "https://deploy-token@example.com/api",
        });
        assert.notEqual(credentialResult.status, 0);
        assert.match(credentialResult.stderr, /must not include URL credentials/);

        const queryResult = runBuild({
            SKILLPASSPORT_API_BASE_URL: "https://api.example.com/api?token=public-nope",
        });
        assert.notEqual(queryResult.status, 0);
        assert.match(queryResult.stderr, /must not include a query string or fragment/);

        const fragmentResult = runBuild({
            PUBLIC_APP_BASE_URL: "https://skillpassport.example/#token",
        });
        assert.notEqual(fragmentResult.status, 0);
        assert.match(fragmentResult.stderr, /must not include a query string or fragment/);
    });
});
