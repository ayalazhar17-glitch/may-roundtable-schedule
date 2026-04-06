const { json, methodNotAllowed, handleError, readJsonBody } = require("../_lib/http");
const { issueAdminCookie } = require("../_lib/admin");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return methodNotAllowed(res, ["POST"]);
  }

  try {
    const body = await readJsonBody(req);
    if (!process.env.ADMIN_PIN || body.pin !== process.env.ADMIN_PIN) {
      return json(res, 401, { error: "Incorrect admin PIN." });
    }

    issueAdminCookie(res);
    return json(res, 200, { ok: true });
  } catch (error) {
    return handleError(res, error);
  }
};
