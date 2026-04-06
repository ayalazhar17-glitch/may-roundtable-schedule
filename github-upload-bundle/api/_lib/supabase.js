const { HttpError } = require("./http");

const SLOT_SELECT = "id,slug,event_date,event_time,venue,area,needs,status,sort_order";

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new HttpError(500, `Missing required environment variable: ${name}`);
  }
  return value;
}

function supabaseBase() {
  return requiredEnv("SUPABASE_URL").replace(/\/$/, "");
}

function supabaseHeaders(extra = {}) {
  const key = requiredEnv("SUPABASE_SERVICE_ROLE_KEY");
  return {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    ...extra
  };
}

async function supabaseRequest(path, options = {}) {
  const response = await fetch(`${supabaseBase()}/rest/v1/${path}`, {
    method: options.method || "GET",
    headers: supabaseHeaders(options.headers || {}),
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  if (!response.ok) {
    let errorPayload = null;
    try {
      errorPayload = await response.json();
    } catch {
      errorPayload = null;
    }

    throw new HttpError(
      response.status,
      errorPayload?.message || errorPayload?.error || "Supabase request failed.",
      errorPayload
    );
  }

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function formatSlot(row) {
  return {
    id: row.id,
    slug: row.slug,
    date: row.event_date,
    time: row.event_time,
    venue: row.venue,
    area: row.area || "",
    needs: row.needs,
    status: row.status,
    sortOrder: row.sort_order || 0
  };
}

function formatRegistration(row) {
  const slot = row.slot || {};
  return {
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    companyRole: row.company_role || "",
    attendeeRole: row.attendee_role,
    notes: row.notes || "",
    createdAt: row.created_at,
    slot: {
      id: slot.id,
      slug: slot.slug,
      date: slot.event_date,
      time: slot.event_time,
      venue: slot.venue,
      area: slot.area || "",
      needs: slot.needs
    }
  };
}

function slugify(value) {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function slotPayloadFromInput(input) {
  const payload = {
    event_date: input.eventDate,
    event_time: input.eventTime,
    venue: input.venue,
    area: input.area || "",
    needs: input.needs,
    status: input.status,
    sort_order: input.sortOrder === undefined ? undefined : Number(input.sortOrder)
  };

  if (input.slug) {
    payload.slug = input.slug;
  } else if (input.venue && input.eventDate) {
    payload.slug = `${slugify(input.venue)}-${String(input.eventDate).replace(/-/g, "")}`;
  }

  return payload;
}

module.exports = {
  SLOT_SELECT,
  supabaseRequest,
  formatSlot,
  formatRegistration,
  slotPayloadFromInput
};
