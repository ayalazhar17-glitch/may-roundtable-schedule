const { json, methodNotAllowed, handleError, readJsonBody, HttpError } = require("../../_lib/http");
const { requireAdmin } = require("../../_lib/admin");
const { SLOT_SELECT, supabaseRequest, formatSlot, slotPayloadFromInput } = require("../../_lib/supabase");

module.exports = async function handler(req, res) {
  if (!requireAdmin(req, res)) {
    return;
  }

  try {
    if (req.method === "GET") {
      const rows = await supabaseRequest(
        `slots?select=${encodeURIComponent(SLOT_SELECT)}&order=event_date.asc,sort_order.asc,id.asc`
      );
      return json(res, 200, { slots: (rows || []).map(formatSlot) });
    }

    if (req.method === "POST") {
      const body = await readJsonBody(req);
      for (const field of ["eventDate", "eventTime", "venue", "needs"]) {
        if (!body[field]) {
          throw new HttpError(400, `Missing field: ${field}`);
        }
      }

      const rows = await supabaseRequest(`slots?select=${encodeURIComponent(SLOT_SELECT)}`, {
        method: "POST",
        headers: {
          Prefer: "return=representation"
        },
        body: slotPayloadFromInput(body)
      });

      return json(res, 201, { slot: formatSlot(rows[0]) });
    }

    return methodNotAllowed(res, ["GET", "POST"]);
  } catch (error) {
    return handleError(res, error);
  }
};
