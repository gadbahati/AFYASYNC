import { createServer } from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("./dist", import.meta.url));
const port = Number(process.env.PORT || 4173);
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

const server = createServer(async (req, res) => {
  try {
    const requested = safePath(req.url || "/");
    if (!requested) return res.writeHead(400).end("Bad request");

    try {
      const info = await stat(requested);
      if (info.isFile()) return sendFile(res, requested);
    } catch {}

    return sendFile(res, join(root, "index.html"));
  } catch {
    return res.writeHead(500).end("Internal server error");
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`AfyaSync frontend listening on 0.0.0.0:${port}`);
});
