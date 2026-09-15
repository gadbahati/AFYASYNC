import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { Readable } from "node:stream";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("./dist", import.meta.url));
const port = Number(process.env.PORT || 4173);
const apiProxyTarget = (process.env.API_PROXY_TARGET || "").replace(/\/$/, "");
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const safePath = (urlPath) => {
  const decoded = decodeURIComponent(urlPath.split("?")[0] || "/");
  const candidate = normalize(join(root, decoded === "/" ? "index.html" : decoded));
  return candidate.startsWith(root) ? candidate : null;
};

const sendFile = (res, filePath) => {
  res.writeHead(200, {
    "Content-Type": mime[extname(filePath)] || "application/octet-stream",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
  });
  createReadStream(filePath).pipe(res);
};

const readRequestBody = async (req) => {
  const chunks = [];
  for await (const chunk of req) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  return chunks.length ? Buffer.concat(chunks) : undefined;
};

const proxyApi = async (req, res) => {
  if (!apiProxyTarget) return res.writeHead(503, { "Content-Type": "application/json" }).end(JSON.stringify({ success: false, message: "API proxy is not configured" }));
  const target = new URL(req.url || "/", `${apiProxyTarget}/`);
  const headers = { ...req.headers };
  delete headers.host;
  delete headers.connection;
  const body = ["GET", "HEAD"].includes(req.method || "GET") ? undefined : await readRequestBody(req);
  const upstream = await fetch(target, { method: req.method, headers, body, redirect: "manual" });
  const responseHeaders = {};
  upstream.headers.forEach((value, key) => { responseHeaders[key] = value; });
  delete responseHeaders["content-length"];
  res.writeHead(upstream.status, responseHeaders);
  if (!upstream.body) return res.end();
  return Readable.fromWeb(upstream.body).pipe(res);
};

const server = createServer(async (req, res) => {
  try {
    if ((req.url || "/").startsWith("/api/")) return await proxyApi(req, res);

    const requested = safePath(req.url || "/");
    if (!requested) return res.writeHead(400).end("Bad request");

    try {
      const info = await stat(requested);
      if (info.isFile()) return sendFile(res, requested);
    } catch {}

    return sendFile(res, join(root, "index.html"));
  } catch (error) {
    console.error("Frontend request failed:", error);
    return res.writeHead(502, { "Content-Type": "application/json" }).end(JSON.stringify({ success: false, message: "API proxy request failed" }));
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`AfyaSync frontend listening on 0.0.0.0:${port}`);
  console.log(`AfyaSync API proxy: ${apiProxyTarget || "not configured"}`);
});
