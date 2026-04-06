const { json, methodNotAllowed, handleError } = require("../_lib/http");
const { requireAdmin } = require("../_lib/admin");
const { supabaseRequest, formatRegistration } = require("../_lib/supabase");

const REGISTRATION_SELECT = [
  "id",
  "full_name",
  "email",
  "company_role",
  "attendee_role",
  "notes",
  "created_at",
  "slot:slots(id,slug,event_date,event_time,venue,area,needs)"
].join(",");

module.exports = async function handler(req, res) {
  if (req.method !== "GET") {
    return methodNotAllowed(res, ["GET"]);
  }

  if (!requireAdmin(req, res)) {
    return;
  }

  try {
    const rows = await supabaseRequest(
      `registrations?select=${encodeURIComponent(REGISTRATION_SELECT)}&order=created_at.desc`
    );
    return json(res, 200, { registrations: (rows || []).map(formatRegistration) });
  } catch (error) {
    return handleError(res, error);
  }
};
