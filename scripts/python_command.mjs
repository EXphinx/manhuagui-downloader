import { spawnSync } from "node:child_process";
import process from "node:process";

export function findPython() {
  const candidates =
    process.platform === "win32"
      ? process.env.VIRTUAL_ENV
        ? [
            ["python", []],
            ["py", ["-3"]],
            ["python3", []],
          ]
        : [
            ["py", ["-3"]],
            ["python", []],
            ["python3", []],
          ]
      : [
          ["python3", []],
          ["python", []],
        ];

  for (const [command, args] of candidates) {
    const result = spawnSync(command, [...args, "--version"], {
      stdio: "ignore",
      timeout: 5000,
      windowsHide: true,
    });
    if (!result.error && result.status === 0) {
      return { command, args };
    }
  }

  throw new Error(
    "Python 3 was not found. Install Python 3.10 or newer and add it to PATH.",
  );
}
