#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const packageRoot = path.resolve(__dirname, "..");
const cliArgs = process.argv.slice(2);
const storeHome =
  process.env.CODEX_MEM_HOME ||
  (process.platform === "win32"
    ? path.join(os.homedir(), "Documents", "codex-mem", "state")
    : path.join(os.homedir(), ".codex-mem", "state"));

function buildPythonArgs() {
  if (cliArgs.length === 0) {
    return ["-m", "codex_mem", "--help"];
  }
  return ["-m", "codex_mem", cliArgs[0], "--home", storeHome, ...cliArgs.slice(1)];
}

function candidateInterpreters() {
  const candidates = [];
  if (process.env.CODEX_MEM_PYTHON) {
    candidates.push({ command: process.env.CODEX_MEM_PYTHON, prefix: [] });
  }
  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA || "";
    const explicit = [
      path.join(localAppData, "Programs", "Python", "Python312", "python.exe"),
      path.join(localAppData, "Programs", "Python", "Python311", "python.exe"),
      path.join(localAppData, "Programs", "Python", "Python310", "python.exe"),
      "C:\\Python314\\python.exe",
      "C:\\Python313\\python.exe",
      "C:\\Python312\\python.exe",
      "C:\\Python311\\python.exe",
      "C:\\Python310\\python.exe"
    ];
    for (const command of explicit) {
      if (command && fs.existsSync(command)) {
        candidates.push({ command, prefix: [] });
      }
    }
    candidates.push({ command: "python", prefix: [] });
    candidates.push({ command: "py", prefix: ["-3"] });
    return candidates;
  }

  candidates.push({ command: "python3", prefix: [] });
  candidates.push({ command: "python", prefix: [] });
  return candidates;
}

function tryRun(candidate, args) {
  const result = spawnSync(candidate.command, [...candidate.prefix, ...args], {
    cwd: packageRoot,
    env: {
      ...process.env,
      PYTHONUTF8: "1"
    },
    stdio: "inherit"
  });
  if (result.error) {
    return false;
  }
  if (typeof result.status === "number") {
    process.exit(result.status);
  }
  console.error(`codex-mem wrapper terminated unexpectedly via signal: ${result.signal || "unknown"}`);
  process.exit(1);
}

const args = buildPythonArgs();
for (const candidate of candidateInterpreters()) {
  if (tryRun(candidate, args)) {
    break;
  }
}

console.error("No usable Python interpreter found. Set CODEX_MEM_PYTHON to python.exe or install Python 3.11+.");
process.exit(1);
