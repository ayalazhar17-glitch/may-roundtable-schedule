const { json, methodNotAllowed, handleError } = require("./_lib/http");
const { SLOT_SELECT, supabaseRequest, formatSlot } = require("./_lib/supabase");

module.exports = async function handler(req, res) {
  if (req.method !== "GET") {
    return methodNotAllowed(res, ["GET"]);
  }

  try {
    const rows = await supabaseRequest(
      `slots?select=${encodeURIComponent(SLOT_SELECT)}&order=event_date.asc,sort_order.asc,id.asc`
    );
    return json(res, 200, { slots: (rows || []).map(formatSlot) });
  } catch (error) {
    return handleError(res, error);
  }
};
