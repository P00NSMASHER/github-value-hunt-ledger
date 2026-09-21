"use strict";

(() => {
  const byId = (id) => document.getElementById(id);
  const contact = document.querySelector('meta[name="freight-contact-email"]').content;
  const message = byId("formMessage");
  let subject = "Freight Recovery — fit discussion";
  let draft = "";

  byId("prepareDraft").addEventListener("click", () => {
    for (const field of document.querySelectorAll("#inquiryFields input")) {
      if (!field.reportValidity()) return;
    }

    const company = byId("company").value.trim();
    const email = byId("email").value.trim();
    const volume = byId("volume").value;

    subject = "Freight Recovery — " + company;
    draft = [
      "I would like to discuss fit for a freight invoice review.",
      "",
      "Company: " + company,
      "Work email: " + email,
      "Approximate carrier invoices per month: " + volume,
      "",
      "Please confirm which current offer fits, the proposed scope and fee, and the controlled intake process before any freight documents are shared."
    ].join("\n");

    byId("draftText").value = draft;
    byId("draftPanel").hidden = false;

    if (contact) {
      byId("emailDraft").href =
        "mailto:" + contact +
        "?subject=" + encodeURIComponent(subject) +
        "&body=" + encodeURIComponent(draft);
      byId("emailDraft").hidden = false;
      byId("deliveryNote").textContent =
        "Open the draft to " + contact +
        ", review it, and send it from your own email application. Do not attach freight documents to the initial inquiry.";
    }

    message.textContent = "Inquiry prepared locally. Nothing has been sent.";
    byId("draftText").focus();
  });

  byId("copyDraft").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(draft);
      message.textContent = "Inquiry copied. Nothing has been sent.";
    } catch (_) {
      byId("draftText").focus();
      byId("draftText").select();
      message.textContent = "The inquiry is selected. Use your device’s Copy command.";
    }
  });

  byId("downloadDraft").addEventListener("click", () => {
    const content = "Subject: " + subject + "\n\n" + draft + "\n";
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "freight-recovery-inquiry.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message.textContent = "Text file prepared. Nothing has been sent.";
  });

  byId("emailDraft").addEventListener("click", () => {
    message.textContent =
      "Email draft opened. Review and send it yourself; this page cannot confirm sending or delivery.";
  });
})();
