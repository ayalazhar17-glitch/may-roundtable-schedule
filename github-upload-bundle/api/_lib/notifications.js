async function sendResendEmail({ to, subject, text }) {
  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.FROM_EMAIL;
  if (!apiKey || !to || !from) {
    return;
  }

  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from,
      to: [to],
      subject,
      text
    })
  });
}

function twilioAuthHeader() {
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const authToken = process.env.TWILIO_AUTH_TOKEN;
  if (!accountSid || !authToken) {
    return null;
  }
  return Buffer.from(`${accountSid}:${authToken}`).toString("base64");
}

async function sendTwilioSms(body) {
  const accountSid = process.env.TWILIO_ACCOUNT_SID;
  const to = process.env.TWILIO_TO_NUMBER;
  const from = process.env.TWILIO_FROM_NUMBER;
  const auth = twilioAuthHeader();

  if (!accountSid || !to || !from || !auth) {
    return;
  }

  const payload = new URLSearchParams({ To: to, From: from, Body: body });
  await fetch(`https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: payload
  });
}

function bookingText(registration) {
  const slot = registration.slot;
  return [
    "New booking received",
    "",
    `Name: ${registration.fullName}`,
    `Email: ${registration.email}`,
    `Company / Role: ${registration.companyRole || "Not provided"}`,
    `Attending as: ${registration.attendeeRole}`,
    `Date: ${slot.date}`,
    `Time: ${slot.time}`,
    `Venue: ${slot.venue}`,
    `Area: ${slot.area || "Not listed"}`,
    `Needs: ${slot.needs}`,
    `Notes: ${registration.notes || "None"}`
  ].join("\n");
}

async function notifyBooking(registration) {
  const organizer = process.env.ORGANIZER_EMAIL;
  const text = bookingText(registration);
  const subject = `New roundtable booking: ${registration.slot.venue} on ${registration.slot.date}`;

  try {
    if (organizer) {
      await sendResendEmail({ to: organizer, subject, text });
    }
  } catch (error) {
    console.error("Organizer email failed", error);
  }

  try {
    await sendTwilioSms(
      `New booking: ${registration.fullName} | ${registration.slot.venue} | ${registration.slot.date} ${registration.slot.time} | ${registration.attendeeRole}`
    );
  } catch (error) {
    console.error("Twilio SMS failed", error);
  }

  if (process.env.SEND_USER_CONFIRMATION === "true") {
    try {
      await sendResendEmail({
        to: registration.email,
        subject: `Confirmed: ${registration.slot.venue} on ${registration.slot.date}`,
        text
      });
    } catch (error) {
      console.error("User confirmation failed", error);
    }
  }
}

module.exports = { notifyBooking };
