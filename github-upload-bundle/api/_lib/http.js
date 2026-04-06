class HttpError extends Error {
  constructor(status, message, details) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.details = details || null;
  }
}

function json(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function methodNotAllowed(res, allowed) {
  res.setHeader("Allow", allowed.join(", "));
  return json(res, 405, { error: "Method not allowed." });
}

async function readJsonBody(req) {
  if (req.body && typeof req.body === "object") {
    return req.body;
  }

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.from(chunk));
  }

  if (!chunks.length) {
    return {};
  }

  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "Invalid JSON body.");
  }
}

function handleError(res, error) {
  if (error instanceof HttpError) {
    return json(res, error.status, {
      error: error.message,
      details: error.details || undefined
    });
  }

  console.error(error);
  return json(res, 500, { error: "Something went wrong." });
}

module.exports = {
  HttpError,
  json,
  methodNotAllowed,
  readJsonBody,
  handleError
};
