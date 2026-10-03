#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const apiDir = path.join(__dirname, "../src/api");
const chunkDir = path.join(apiDir, ".client-chunks");
const target = path.join(apiDir, "client.ts");

if (!fs.existsSync(chunkDir)) {
  if (fs.existsSync(target)) {
    console.log("assemble-client: chunk directory absent; keeping checked-in client.ts");
    process.exit(0);
  }
  console.error("assemble-client: neither chunk directory nor client.ts exists");
  process.exit(1);
}

const files = fs.readdirSync(chunkDir).filter((f) => f.endsWith(".txt")).sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
const body = files.map((f) => fs.readFileSync(path.join(chunkDir, f), "utf8")).join("");
if (body.length < 10000 || !body.includes("contextScopeSummary") || !body.includes("citizenApiMethods")) {
  console.error("assemble-client: incomplete assembly", body.length);
  process.exit(1);
}
fs.writeFileSync(target, body);
console.log("assemble-client: restored client.ts", body.length, "bytes from", files.length, "chunks");
