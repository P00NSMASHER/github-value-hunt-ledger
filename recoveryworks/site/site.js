(() => {
  "use strict";

  const form = document.querySelector("#recoveryInquiry");
  const panel = document.querySelector("#draftPanel");
  const draftText = document.querySelector("#draftText");
  const emailDraft = document.querySelector("#emailDraft");
  const copyDraft = document.querySelector("#copyDraft");
  const status = document.querySelector("#formStatus");
  const year = document.querySelector("#year");

  if (year) year.textContent = String(new Date().getFullYear());
  if (!form || !panel || !draftText || !emailDraft || !copyDraft || !status) return;

  const clean = (value) => value.trim().replace(/\s+/g, " ");

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!form.reportValidity()) return;

    const name = clean(document.querySelector("#name").value);
    const email = clean(document.querySelector("#email").value);
    const company = clean(document.querySelector("#company").value);
    const area = clean(document.querySelector("#area").value);
    const notes = document.querySelector("#notes").value.trim();
    const subject = `RecoveryOS fit conversation — ${company}`;
    const body = [
      "Hello RecoveryOS,",
      "",
      "I’d like to discuss a possible recovery review.",
      "",
      `Name: ${name}`,
      `Work email: ${email}`,
      `Company: ${company}`,
      `Area: ${area}`,
      `Note: ${notes || "No additional note."}`,
      "",
      "I have not attached or included confidential business records.",
    ].join("\n");

    const contact = document.querySelector(".signal-bar a").textContent.trim();
    emailDraft.href = `mailto:${contact}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    draftText.textContent = `Subject: ${subject}\n\n${body}`;
    panel.hidden = false;
    status.textContent = "Draft prepared locally. Nothing was uploaded.";
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });

  copyDraft.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(draftText.textContent);
      copyDraft.textContent = "Copied";
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(draftText);
      selection.removeAllRanges();
      selection.addRange(range);
      copyDraft.textContent = "Select and copy";
    }
  });
})();
