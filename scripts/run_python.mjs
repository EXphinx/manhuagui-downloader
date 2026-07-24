import { spawnSync } from "node:child_process";
import process from "node:process";

import { findPython } from "./python_command.mjs";

const python = findPython();
const result = spawnSync(
  python.command,
  [...python.args, ...process.argv.slice(2)],
  {
    cwd: process.cwd(),
    env: process.env,
    stdio: "inherit",
    windowsHide: true,
  },
);

if (result.error) {
  throw result.error;
}
process.exitCode = result.status ?? 1;
