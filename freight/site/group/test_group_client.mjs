import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

// No browser network or provider calls: exercise the delivered script against a
// minimal DOM and mocked transport, including uncertain responses and retries.
const source = readFileSync(new URL('./group.js', import.meta.url), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor(value = '') { this.value = value; this.textContent = ''; this.listeners = {}; this.hidden = false; this.disabled = false; this.checked = false; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  async fire(type) { return this.listeners[type]?.({preventDefault() {}}); }
  focus() { this.focused = true; }
  select() { this.selected = true; }
}
async function page({online = true, query = '', post, clipboard = true, scriptError = false} = {}) {
  const ids = ['group-enquiry', 'enquiry-business', 'enquiry-name', 'enquiry-email', 'enquiry-company', 'enquiry-message', 'enquiry-consent', 'enquiry-website', 'enquiry-fields', 'send-enquiry', 'enquiry-draft', 'enquiry-status', 'enquiry-copy-status', 'enquiry-copy-text', 'copy-enquiry'];
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const el = id => elements[id];
  el('enquiry-business').options = [{value: 'general', textContent: 'Help me find the right business'}, {value: 'capturebrief', textContent: 'CaptureBrief'}, {value: 'permitplate', textContent: 'PermitPlate NYC'}];
  el('enquiry-business').value = 'general';
  el('send-enquiry').disabled = true;
  el('enquiry-draft').href = 'mailto:jay@retallyrecovery.com?subject=RETALLY';
  el('group-enquiry').reportValidity = () => !!(el('enquiry-name').value && el('enquiry-email').value && el('enquiry-message').value && el('enquiry-consent').checked);
  const calls = [];
  const verification = {};
  let sequence = 0;
  const window = {location: {pathname: '/contact/', search: query, hash: ''}, crypto: {randomUUID: () => `12345678-1234-4000-8000-${String(++sequence).padStart(12, '0')}`}};
  if (!scriptError) window.turnstile = {render(selector, options) { verification.options = options; return 0; }, reset() { verification.resets = (verification.resets || 0) + 1; }};
  const document = {getElementById: el, querySelector: () => null, createElement: () => new Element(), head: {appendChild(script) { if (scriptError) script.onerror(); }}};
  const context = {window, document, URLSearchParams, AbortController, setTimeout, clearTimeout,
    navigator: {clipboard: {async writeText(text) { if (!clipboard) throw Error('denied'); verification.copied = text; }}},
    fetch: async (url, options) => {
      calls.push({url, options});
      assert.equal(url, '/api/group-inquiry');
      if (options.method === 'POST') return post ? await post(options) : {status: 202, json: async () => ({ok: true, received: true, reference: 'RA-20261022-1234ABCD', notificationPending: false})};
      return {ok: online, json: async () => ({online, siteKey: online ? 'public-test-key' : undefined})};
    }};
  runInNewContext(source, context);
  await tick();
  return {el, calls, verification,
    verify(token = 'test-token') { verification.options.callback(token); },
    fill() { el('enquiry-name').value = 'Example Person'; el('enquiry-email').value = 'person@example.test'; el('enquiry-company').value = ''; el('enquiry-message').value = 'Please explain the available public-source review.'; el('enquiry-consent').checked = true; },
    submit: () => el('group-enquiry').fire('submit')};
}

test('initialization is read-only and accepts old display-name and slug links', async () => {
  for (const query of ['?business=CaptureBrief', '?business=capturebrief']) {
    const p = await page({query});
    assert.equal(p.calls.length, 1);
    assert.equal(p.calls[0].options.method, undefined);
    assert.equal(p.el('enquiry-business').value, 'capturebrief');
    assert.equal(p.el('send-enquiry').disabled, true);
    assert.equal(p.verification.options.action, 'retally_group');
    p.verify();
    assert.match(p.el('enquiry-status').textContent, /Nothing has been sent yet/);
  }
});

test('offline intake and blocked security script keep email/copy fallback without posting', async () => {
  for (const config of [{online: false}, {scriptError: true}]) {
    const p = await page(config);
    assert.equal(p.el('group-enquiry').hidden, false);
    assert.equal(p.el('send-enquiry').disabled, true);
    assert.match(p.el('enquiry-status').textContent, /unavailable/);
    p.fill();
    await p.submit();
    assert.equal(p.calls.length, 1);
    assert.match(p.el('enquiry-draft').href, /^mailto:jay@retallyrecovery.com/);
  }
});

test('verified submission sends exact contact contract and displays durable receipt', async () => {
  const p = await page({query: '?business=permitplate'});
  p.fill(); p.verify(); await p.submit();
  const payload = JSON.parse(p.calls[1].options.body);
  assert.deepEqual(Object.keys(payload).sort(), ['business','companyName','consent','fullName','idempotencyKey','message','turnstileToken','website','workEmail'].sort());
  assert.equal(payload.business, 'permitplate');
  assert.equal(payload.companyName, '');
  assert.equal(payload.consent, true);
  assert.equal(payload.website, '');
  assert.equal(p.calls[1].options.credentials, 'same-origin');
  assert.match(p.el('enquiry-status').textContent, /saved.*RA-20261022-1234ABCD/);
  assert.equal(p.el('enquiry-fields').disabled, true);
  assert.equal(p.el('send-enquiry').disabled, true);
  await p.submit();
  assert.equal(p.calls.length, 2);
});

test('provider-pending receipt stays a successful save without claiming email delivery', async () => {
  const p = await page({post: async () => ({status: 202, json: async () => ({ok: true, received: true, reference: 'RA-20261022-1234ABCD', notificationPending: true})})});
  p.fill(); p.verify(); await p.submit();
  assert.match(p.el('enquiry-status').textContent, /saved.*notification is pending/);
  assert.doesNotMatch(p.el('enquiry-status').textContent, /email (?:sent|delivered)/i);
});

test('lost response retries identical details with the same idempotency key', async () => {
  let attempts = 0;
  const p = await page({post: async () => { if (++attempts === 1) throw Error('lost response'); return {status: 202, json: async () => ({ok: true, received: true, reference: 'RA-20261022-1234ABCD', duplicate: true})}; }});
  p.fill(); p.verify(); await p.submit();
  assert.match(p.el('enquiry-status').textContent, /could not confirm/);
  assert.equal(p.el('enquiry-fields').disabled, false);
  p.verify('new-security-token');
  assert.doesNotMatch(p.el('enquiry-status').textContent, /Nothing has been sent/);
  await p.submit();
  const [first, retry] = p.calls.filter(c => c.options.method === 'POST').map(c => JSON.parse(c.options.body));
  assert.equal(first.idempotencyKey, retry.idempotencyKey);
  assert.notEqual(first.turnstileToken, retry.turnstileToken);
  assert.match(p.el('enquiry-status').textContent, /saved/);
});

test('changed details get a new key after an uncertain request', async () => {
  const p = await page({post: async () => { throw Error('unavailable'); }});
  p.fill(); p.verify(); await p.submit();
  p.el('enquiry-message').value = 'A revised non-sensitive question.';
  p.verify('new-security-token'); await p.submit();
  const requests = p.calls.filter(c => c.options.method === 'POST').map(c => JSON.parse(c.options.body));
  assert.notEqual(requests[0].idempotencyKey, requests[1].idempotencyKey);
});

test('malformed or non-202 response never creates a success message', async () => {
  for (const response of [{status: 200, json: async () => ({ok: true, received: true, reference: 'RA-20261022-1234ABCD'})}, {status: 202, json: async () => ({ok: true, received: true, reference: '<unsafe>'})}]) {
    const p = await page({post: async () => response});
    p.fill(); p.verify(); await p.submit();
    assert.match(p.el('enquiry-status').textContent, /could not confirm/);
    assert.equal(p.el('enquiry-fields').disabled, false);
  }
});

test('unchecked consent and duplicate submit events cannot dispatch extra requests', async () => {
  let resolve;
  const p = await page({post: () => new Promise(done => { resolve = done; })});
  p.fill(); p.verify(); p.el('enquiry-consent').checked = false;
  await p.submit(); assert.equal(p.calls.length, 1);
  p.el('enquiry-consent').checked = true;
  const pending = p.submit();
  await p.submit(); assert.equal(p.calls.length, 2);
  resolve({status: 202, json: async () => ({ok: true, received: true, reference: 'RA-20261022-1234ABCD'})});
  await pending;
});

test('clipboard denial exposes the complete manual draft without posting', async () => {
  const p = await page({clipboard: false, online: false});
  p.fill(); await p.el('copy-enquiry').fire('click');
  const draft = p.el('enquiry-copy-text');
  assert.equal(draft.hidden, false); assert.equal(draft.selected, true);
  for (const detail of ['Business:', 'Example Person', 'person@example.test', 'public-source review']) assert.ok(draft.value.includes(detail));
  assert.equal(p.calls.length, 1);
});
