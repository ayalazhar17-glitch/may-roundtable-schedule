const { json, methodNotAllowed, handleError, readJsonBody, HttpError } = require("./_lib/http");
const { notifyBooking } = require("./_lib/notifications");
const { supabaseRequest } = require("./_lib/supabase");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return methodNotAllowed(res, ["POST"]);
  }

  try {
    const body = await readJsonBody(req);
    const requiredFields = ["slotId", "fullName", "email", "attendeeRole"];
    for (const field of requiredFields) {
      if (!body[field]) {
        throw new HttpError(400, `Missing field: ${field}`);
      }
    }

    const registration = await supabaseRequest("rpc/book_slot", {
      method: "POST",
      body: {
        p_slot_id: Number(body.slotId),
        p_full_name: String(body.fullName).trim(),
        p_email: String(body.email).trim(),
        p_company_role: String(body.companyRole || "").trim(),
        p_attendee_role: String(body.attendeeRole).trim(),
        p_notes: String(body.notes || "").trim()
      }
    });

    await notifyBooking(registration);
    return json(res, 201, { ok: true, registration });
  } catch (error) {
    return handleError(res, error);
  }
};
