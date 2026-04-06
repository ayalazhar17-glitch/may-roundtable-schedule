const crypto = require("crypto");
const { json } = require("./http");

const COOKIE_NAME = "roundtable_admin";

function parseCookies(header = "") {
  return header
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .reduce((acc, part) => {
      const eqIndex = part.indexOf("=");
      if (eqIndex === -1) {
        return acc;
      }
      const key = part.slice(0, eqIndex);
      const value = decodeURIComponent(part.slice(eqIndex + 1));
      acc[key] = value;
      return acc;
    }, {});
}

function sessionSecret() {
  return process.env.ADMIN_SESSION_SECRET || process.env.ADMIN_PIN || "changeme";
}

function sign(value) {
  return crypto.createHmac("sha256", sessionSecret()).update(value).digest("hex");
}

function buildCookie(value, maxAge = 60 * 60 * 24 * 7) {
  const secure = process.env.NODE_ENV === "production" || !!process.env.VERCEL;
  return [
    `${COOKIE_NAME}=${encodeURIComponent(value)}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${maxAge}`,
    secure ? "Secure" : ""
  ]
    .filter(Boolean)
    .join("; ");
}

function issueAdminCookie(res) {
  const value = "admin";
  res.setHeader("Set-Cookie", buildCookie(`${value}.${sign(value)}`));
}

function clearAdminCookie(res) {
  res.setHeader("Set-Cookie", buildCookie("", 0));
}

function isAdmin(req) {
  const cookies = parseCookies(req.headers.cookie || "");
  const raw = cookies[COOKIE_NAME];
  if (!raw) {
    return false;
  }

  const [value, signature] = raw.split(".");
  if (!value || !signature) {
    return false;
  }

  const expected = sign(value);
  if (signature.length !== expected.length) {
    return false;
  }

  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected)) && value === "admin";
}

function requireAdmin(req, res) {
  if (isAdmin(req)) {
    return true;
  }

  json(res, 401, { error: "Admin authentication required." });
  return false;
}

module.exports = {
  issueAdminCookie,
  clearAdminCookie,
  isAdmin,
  requireAdmin
};
