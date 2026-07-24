import { spawn } from "node:child_process";
import process from "node:process";

import { findPython } from "./python_command.mjs";

const API_URL = "http://127.0.0.1:48135/api/health";
const children = new Set();
let exiting = false;

async function readHealth() {
  try {
    const response = await fetch(API_URL, { cache: "no-store" });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

async function waitForBackend() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const health = await readHealth();
    if (health?.app === "manhuagui-downloader") return;
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error("本地下载服务启动超时");
}

function start(command, args) {
  const child = spawn(command, args, {
    cwd: process.cwd(),
    env: process.env,
    stdio: "inherit",
  });
  children.add(child);
  child.once("exit", () => children.delete(child));
  return child;
}

function stop(exitCode = 0) {
  if (exiting) return;
  exiting = true;
  for (const child of children) {
    if (!child.killed) child.kill("SIGTERM");
  }
  setTimeout(() => process.exit(exitCode), 80).unref();
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => stop(0));
}

const currentHealth = await readHealth();
if (currentHealth && currentHealth.app !== "manhuagui-downloader") {
  throw new Error("端口 48135 已被其他程序占用");
}

if (!currentHealth) {
  const python = findPython();
  const backend = start(python.command, [
    ...python.args,
    "-u",
    "-m",
    "manhuagui_downloader.server",
    "--port",
    "48135",
    "--parent-pid",
    String(process.pid),
  ]);
  backend.once("exit", (code) => {
    if (!exiting) stop(code ?? 1);
  });
  await waitForBackend();
}

const pnpm = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const vite = start(pnpm, ["exec", "vite", "--host", "127.0.0.1"]);
vite.once("exit", (code) => stop(code ?? 0));
