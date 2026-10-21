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

// A local composer, deliberately separate from the freight enquiry API.
// No fields are stored, submitted, tracked or sent until the user uses email.
const enquiryForm = document.getElementById("group-enquiry");
if (enquiryForm) {
  const business = document.getElementById("enquiry-business");
  const message = document.getElementById("enquiry-message");
  const draft = document.getElementById("enquiry-draft");
  const status = document.getElementById("enquiry-status");
  const recipient = draft.href.split("?")[0];
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("business");
  if ([...business.options].some(option => option.value === requested)) business.value = requested;
  function compose() {
    const subject = "RETALLY enquiry — " + business.value;
    const body = "Business: " + business.value + "\n\n" + message.value.trim();
    draft.href = recipient + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    draft.textContent = "Open draft for " + business.value + " ↗";
    return {subject, body};
  }
  enquiryForm.hidden = false;
  enquiryForm.addEventListener("input", compose);
  enquiryForm.addEventListener("change", compose);
  enquiryForm.addEventListener("submit", event => {
    event.preventDefault();
    compose();
    status.textContent = "Your email app will open if one is configured. Review and send the draft there, or copy your message below. Nothing has been sent from this page.";
    window.location.href = draft.href;
  });
  document.getElementById("copy-enquiry").addEventListener("click", async () => {
    const {subject, body} = compose();
    try {
      await navigator.clipboard.writeText(subject + "\n\n" + body);
      status.textContent = "Message copied. Paste it into an email to RETALLY, review it and send when ready.";
    } catch {
      message.focus();
      message.select();
      status.textContent = "Select and copy your message, then use the email address on this page. Nothing has been sent.";
    }
  });
  compose();
}
