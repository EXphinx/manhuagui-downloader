import { spawnSync } from "node:child_process";
import process from "node:process";

const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const env = { ...process.env };

// Finder automation can block local and hosted DMG builds. In CI mode Tauri
// creates the same installable DMG without relying on Finder window styling.
if (process.platform === "darwin" && !env.CI) {
  env.CI = "true";
}

const result = spawnSync(pnpm, ["exec", "tauri", "build"], {
  cwd: process.cwd(),
  env,
  stdio: "inherit",
  windowsHide: true,
});

if (result.error) {
  throw result.error;
}
process.exitCode = result.status ?? 1;
