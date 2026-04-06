const { json, methodNotAllowed, handleError, readJsonBody, HttpError } = require("../../_lib/http");
const { requireAdmin } = require("../../_lib/admin");
const { SLOT_SELECT, supabaseRequest, formatSlot, slotPayloadFromInput } = require("../../_lib/supabase");

module.exports = async function handler(req, res) {
  if (!requireAdmin(req, res)) {
    return;
  }

  const { id } = req.query;

  try {
    if (!id) {
      throw new HttpError(400, "Slot id is required.");
    }

    if (req.method === "PUT") {
      const body = await readJsonBody(req);
      const payload = slotPayloadFromInput(body);
      Object.keys(payload).forEach((key) => {
        if (payload[key] === undefined || payload[key] === null || payload[key] === "") {
          if (key !== "area") {
            delete payload[key];
          }
        }
      });

      const rows = await supabaseRequest(
        `slots?id=eq.${encodeURIComponent(id)}&select=${encodeURIComponent(SLOT_SELECT)}`,
        {
          method: "PATCH",
          headers: {
            Prefer: "return=representation"
          },
          body: payload
        }
      );

      if (!rows || !rows.length) {
        throw new HttpError(404, "Slot not found.");
      }

      return json(res, 200, { slot: formatSlot(rows[0]) });
    }

    if (req.method === "DELETE") {
      await supabaseRequest(`slots?id=eq.${encodeURIComponent(id)}`, {
        method: "DELETE"
      });
      return json(res, 200, { ok: true });
    }

    return methodNotAllowed(res, ["PUT", "DELETE"]);
  } catch (error) {
    return handleError(res, error);
  }
};
