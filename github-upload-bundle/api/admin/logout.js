const { json, methodNotAllowed } = require("../_lib/http");
const { clearAdminCookie } = require("../_lib/admin");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return methodNotAllowed(res, ["POST"]);
  }

  clearAdminCookie(res);
  return json(res, 200, { ok: true });
};
