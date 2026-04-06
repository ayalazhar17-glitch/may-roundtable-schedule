const { json, methodNotAllowed } = require("../_lib/http");
const { isAdmin } = require("../_lib/admin");

module.exports = async function handler(req, res) {
  if (req.method !== "GET") {
    return methodNotAllowed(res, ["GET"]);
  }

  return json(res, 200, { authenticated: isAdmin(req) });
};
