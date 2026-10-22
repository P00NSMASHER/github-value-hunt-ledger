"use strict";
// Native details remains usable without JavaScript. Escape closes the directory.
const businessMenu = document.querySelector(".business-menu");
if (businessMenu) {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && businessMenu.open) {
      businessMenu.open = false;
      businessMenu.querySelector("summary").focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!businessMenu.contains(event.target)) businessMenu.open = false;
  });
}
// Preserve previously distributed freight homepage anchors after consolidation.
if (window.location.pathname === "/") {
  const freightAnchors = new Set(["#start-audit", "#pricing", "#audit-output", "#how"]);
  if (freightAnchors.has(window.location.hash)) {
    window.location.replace("/recovery/" + window.location.search + window.location.hash);
  }
}

// Shared enquiries use a private receipt endpoint. Email remains an explicit fallback.
const enquiryForm = document.getElementById("group-enquiry");
if (enquiryForm) {
  const field = id => document.getElementById(id);
  const business = field("enquiry-business");
  const fullName = field("enquiry-name");
  const workEmail = field("enquiry-email");
  const companyName = field("enquiry-company");
  const message = field("enquiry-message");
  const consent = field("enquiry-consent");
  const website = field("enquiry-website");
  const fields = field("enquiry-fields");
  const send = field("send-enquiry");
  const draft = field("enquiry-draft");
  const status = field("enquiry-status");
  const copyStatus = field("enquiry-copy-status");
  const copyText = field("enquiry-copy-text");
  const recipient = draft.href.split("?")[0];
  const requested = new URLSearchParams(window.location.search).get("business");
  const requestedOption = [...business.options].find(option => option.value === requested || option.textContent === requested);
  if (requestedOption) business.value = requestedOption.value;
  let online = false;
  let token = "";
  let widget;
  let busy = false;
  let received = false;
  let attempted = false;
  let requestKey = "";
  let requestSignature = "";

  function selectedName() {
    return [...business.options].find(option => option.value === business.value).textContent;
  }
  function compose() {
    const subject = "RETALLY enquiry — " + selectedName();
    const body = "Business: " + selectedName() + "\nName: " + fullName.value.trim()
      + "\nEmail: " + workEmail.value.trim() + "\nCompany: " + companyName.value.trim()
      + "\n\n" + message.value.trim();
    draft.href = recipient + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    return {subject, body};
  }
  function ready() {
    send.disabled = !online || !token || busy || received;
  }
  function securityUnavailable() {
    online = false;
    token = "";
    ready();
    status.textContent = "Secure intake is unavailable. Your details have not been sent. You can use the email draft or copy your enquiry below.";
  }
  async function timedFetch(url, options = {}, timeoutMs = 10000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, {...options, credentials: "same-origin", cache: "no-store", signal: controller.signal});
    } finally {
      clearTimeout(timeout);
    }
  }
  async function initialize() {
    try {
      const response = await timedFetch("/api/group-inquiry", {headers: {Accept: "application/json"}});
      const config = await response.json();
      if (!response.ok || config.online !== true || typeof config.siteKey !== "string" || !config.siteKey
          || !window.crypto || typeof window.crypto.randomUUID !== "function") {
        securityUnavailable();
        return;
      }
      const render = () => {
        try {
          widget = window.turnstile.render("#enquiry-turnstile", {
            sitekey: config.siteKey,
            action: "retally_group",
            theme: "light",
            // Flexible has a 300px minimum; compact also fits the phone card.
            size: "compact",
            callback: value => {
              token = value;
              online = true;
              ready();
              if (!received && !busy) status.textContent = attempted
                ? "Ready to retry. Sending the same details reuses the original request reference if it was saved."
                : "Ready to send securely. Nothing has been sent yet.";
            },
            "expired-callback": () => {
              token = "";
              ready();
              if (!received && !busy) status.textContent = "Security verification expired. Complete it again before sending.";
            },
            "error-callback": () => {
              token = "";
              ready();
              if (!received && !busy) status.textContent = "Security verification is unavailable. Please retry it, or use the email draft below.";
            }
          });
          if (!token && !received && !busy) {
            status.textContent = "Complete the security verification to enable secure sending. Nothing has been sent.";
          }
        } catch { securityUnavailable(); }
      };
      if (window.turnstile) render();
      else {
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.async = true;
        script.defer = true;
        script.onload = render;
        script.onerror = securityUnavailable;
        document.head.appendChild(script);
      }
    } catch { securityUnavailable(); }
  }

  enquiryForm.hidden = false;
  enquiryForm.addEventListener("input", compose);
  enquiryForm.addEventListener("change", compose);
  enquiryForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy || received || !online || !token || !enquiryForm.reportValidity()) return;
    const payload = {
      business: business.value,
      fullName: fullName.value.trim(),
      workEmail: workEmail.value.trim(),
      companyName: companyName.value.trim(),
      message: message.value.trim(),
      consent: consent.checked,
      website: website.value
    };
    // A retry of the same details keeps its key, including after an uncertain response.
    const signature = JSON.stringify(payload);
    if (signature !== requestSignature) {
      requestKey = window.crypto.randomUUID();
      requestSignature = signature;
    }
    payload.idempotencyKey = requestKey;
    payload.turnstileToken = token;
    busy = true;
    attempted = true;
    fields.disabled = true;
    ready();
    compose();
    status.textContent = "Saving your enquiry securely…";
    try {
      const response = await timedFetch("/api/group-inquiry", {
        method: "POST",
        headers: {"Content-Type": "application/json", Accept: "application/json"},
        body: JSON.stringify(payload)
      }, 25000);
      const receipt = await response.json();
      if (response.status !== 202 || receipt.ok !== true || receipt.received !== true
          || typeof receipt.reference !== "string" || !/^RA-\d{8}-[A-Za-z0-9-]{4,40}$/.test(receipt.reference)) {
        throw new Error("No valid saved receipt");
      }
      received = true;
      status.textContent = "Your enquiry was saved. Reference: " + receipt.reference + ". "
        + (receipt.notificationPending === true
          ? "The email notification is pending; your saved enquiry remains available to RETALLY."
          : "RETALLY can use your contact details to respond.");
      send.textContent = "Enquiry saved";
    } catch {
      status.textContent = "We could not confirm that your enquiry was saved. Your details remain on this page. Complete security verification and retry the same details safely, or use the email draft. If a previous attempt reached RETALLY, retrying will reuse its reference.";
    } finally {
      busy = false;
      fields.disabled = received;
      token = "";
      ready();
      if (!received && widget !== undefined && window.turnstile) window.turnstile.reset(widget);
    }
  });
  field("copy-enquiry").addEventListener("click", async () => {
    const {subject, body} = compose();
    const text = subject + "\n\n" + body;
    try {
      await navigator.clipboard.writeText(text);
      copyStatus.textContent = "Enquiry copied. Review it in your email app and send when ready. Copying does not send another enquiry.";
      copyText.hidden = true;
    } catch {
      copyText.value = text;
      copyText.hidden = false;
      copyText.focus();
      copyText.select();
      copyStatus.textContent = "Copy the selected enquiry text below into your email app. Nothing is sent by copying.";
    }
  });
  compose();
  initialize();
}
