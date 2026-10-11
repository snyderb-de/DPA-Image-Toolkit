'use strict';

// node --test testing/web_backend/test_recent_controls.js
// Set PLAYWRIGHT_MODULE to a Playwright module path to include real-browser QA.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');

const root = resolve(__dirname, '../..');
const script = readFileSync(resolve(root, 'web/static/app.js'), 'utf8');
const css = readFileSync(resolve(root, 'web/static/app.css'), 'utf8');
const paths = [
  String.raw`X:\Apps\scans`,
  String.raw`C:\temp\new\reports`,
  String.raw`\\server\share\scans`,
  String.raw`X:\O'Brien\scans`,
  String.raw`X:\scans\<img src=x onerror="alert(1)">&'quoted'`,
];

// A deliberately small DOM double: parsing HTML is forbidden for recent paths.
class Element {
  constructor() {
    this.children = [];
    this.listeners = {};
    this.hidden = false;
  }
  set innerHTML(value) { assert.fail(`Recent folders must not parse HTML: ${value}`); }
  replaceChildren(...children) { this.children = children; }
  appendChild(child) { child.parent = this; this.children.push(child); }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  async click(event = { stopPropagation() { this.stopped = true; } }) {
    await this.listeners.click?.(event);
    if (!event.stopped && this.parent) await this.parent.click(event);
  }
}

function harness() {
  const row = new Element();
  const undo = new Element();
  const retry = new Element();
  undo.hidden = retry.hidden = true;
  const elements = {
    'recent-auto_crop': row,
    'btn-undo-ocr_pdf': undo,
    'btn-retry-flagged-ocr_pdf': retry,
  };
  const requests = [];
  const context = vm.createContext({
    URLSearchParams,
    window: { location: { hash: '' } },
    document: {
      addEventListener() {},
      getElementById: id => elements[id] || null,
      createElement: () => new Element(),
    },
    fetch: async (url, options) => {
      if (options) requests.push({ url, body: JSON.parse(options.body) });
      return { json: async () => ({ ok: true, file_count: 1, folders: paths }) };
    },
    console,
    confirm: () => true,
  });
  vm.runInContext(script, context);
  return { row, undo, retry, requests, context };
}

test('recent-folder selection and forget preserve paths without parsing HTML', async () => {
  const { row, requests, context } = harness();
  context.renderRecent('auto_crop', paths);
  assert.equal(row.hidden, false);
  assert.equal(row.children[0].textContent, 'Recent');
  assert.equal(row.children.length, paths.length + 1);
  for (const [index, path] of paths.entries()) {
    const chip = row.children[index + 1];
    assert.equal(chip.title, path);
    assert.equal(chip.children[0].textContent, path.split(/[\\/]/).filter(Boolean).pop());
    assert.equal(chip.children.length, 2);
    await chip.click();
    assert.deepEqual(requests.pop(), { url: '/api/auto_crop/prepare', body: { folder: path } });
    await chip.children[1].click();
    assert.deepEqual(requests.pop(), { url: '/api/auto_crop/recent/forget', body: { folder: path } });
    assert.equal(requests.length, 0, 'forget must not bubble into selection');
  }
});

test('recent-folder rerender clears stale chips and hides an empty row', () => {
  const { row, context } = harness();
  context.renderRecent('auto_crop', paths);
  context.renderRecent('auto_crop', [paths[0]]);
  assert.equal(row.children.length, 2);
  context.renderRecent('auto_crop', []);
  assert.equal(row.hidden, true);
  assert.equal(row.children.length, 0);
  context.renderRecent('auto_crop', [paths[1]]);
  assert.equal(row.hidden, false);
  assert.equal(row.children[1].title, paths[1]);
  context.renderRecent('missing-tool', paths);
});

test('hidden attribute has an important display override for component rules', () => {
  assert.ok(/\[hidden\]\s*\{\s*display:\s*none\s*!important\s*;?\s*\}/.test(css),
    '[hidden] needs display: none !important to win over component display rules');
});

test('completion, undo, reset, and empty results update control hidden states', async () => {
  const { context, undo, retry } = harness();
  assert.equal(undo.hidden, true);
  assert.equal(retry.hidden, true);
  const results = { outputs: ['out.pdf'], flagged_documents: [{ document: 'scan', pages: [1] }] };
  context.onJobDone('ocr_pdf', results);
  assert.equal(undo.hidden, false);
  assert.equal(retry.hidden, false);
  await context.undoJob('ocr_pdf');
  assert.equal(undo.hidden, true);
  context.onJobDone('ocr_pdf', results);
  await context.resetTool('ocr_pdf');
  assert.equal(undo.hidden, true);
  assert.equal(retry.hidden, true);
  context.onJobDone('ocr_pdf', { outputs: [], flagged_documents: [] });
  assert.equal(undo.hidden, true);
  assert.equal(retry.hidden, true);
});

test('browser: exact recent paths and hidden controls throughout job lifecycle', {
  skip: !process.env.PLAYWRIGHT_MODULE && 'Set PLAYWRIGHT_MODULE to run Chromium QA',
}, async () => {
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
  const browser = await chromium.launch({
    headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (['error', 'warning'].includes(message.type())) errors.push(message.text());
    });
    await page.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.hostname !== 'dpa.test') return route.fulfill({ body: '' });
      if (url.pathname === '/') return route.fulfill({
        contentType: 'text/html', body: readFileSync(resolve(root, 'web/templates/index.html'), 'utf8'),
      });
      if (url.pathname.startsWith('/static/')) return route.fulfill({
        contentType: url.pathname.endsWith('.css') ? 'text/css' : 'text/javascript',
        body: readFileSync(resolve(root, 'web', url.pathname.slice(1)), 'utf8'),
      });
      if (request.method() === 'POST') requests.push({ url: url.pathname, body: request.postDataJSON() });
      return route.fulfill({ json: {
        ok: true, folders: [], file_count: 1, removed_count: 1,
        keys: [], labels: [], settings: {},
      } });
    });
    await page.goto('http://dpa.test/');
    assert.equal(await page.title(), 'DPA Image Toolkit');
    assert.equal(await page.locator('.tool-panel.active').count(), 1);

    async function hidden(selector, expected = true) {
      const result = await page.locator(selector).evaluate(element => ({
        hidden: element.hidden, display: getComputedStyle(element).display,
        rects: element.getClientRects().length,
      }));
      assert.equal(result.hidden, expected, selector);
      if (expected) {
        assert.equal(result.display, 'none', selector);
        assert.equal(result.rects, 0, `${selector} must occupy no space`);
        await page.locator(selector).evaluate(element => element.focus());
        assert.equal(await page.locator(selector).evaluate(element => document.activeElement === element), false);
      } else {
        assert.notEqual(result.display, 'none', selector);
        assert.ok(result.rects > 0, selector);
      }
    }

    await hidden('#btn-undo-auto_crop');
    await hidden('#btn-retry-flagged-ocr_pdf');
    await hidden('#recent-auto_crop');
    for (const path of paths) {
      await page.evaluate(path => renderRecent('auto_crop', [path]), path);
      await hidden('#recent-auto_crop', false);
      const chip = page.locator('#recent-auto_crop .recent-chip');
      assert.equal(await chip.getAttribute('title'), path);
      assert.equal(await chip.locator('.chip-path').textContent(), path.split(/[\\/]/).filter(Boolean).pop());
      assert.equal(await chip.locator('img, script, [onclick]').count(), 0);
      await chip.locator('.chip-path').click();
      await page.waitForFunction(path => state.auto_crop.path === path, path);
      await page.waitForFunction(() => document.getElementById('recent-auto_crop').hidden);
      assert.deepEqual(requests.pop(), { url: '/api/auto_crop/prepare', body: { folder: path } });
      await page.evaluate(path => renderRecent('auto_crop', [path]), path);
      await chip.locator('.chip-forget').click();
      await page.waitForFunction(() => document.getElementById('recent-auto_crop').hidden);
      assert.deepEqual(requests.pop(), { url: '/api/auto_crop/recent/forget', body: { folder: path } });
      assert.equal(requests.length, 0);
    }

    await page.evaluate(() => onJobDone('auto_crop', { outputs: ['out.tif'], success: 1 }));
    await hidden('#btn-undo-auto_crop', false);
    page.on('dialog', dialog => dialog.accept());
    await page.locator('#btn-undo-auto_crop').click();
    await page.waitForFunction(() => document.getElementById('btn-undo-auto_crop').hidden);
    await hidden('#btn-undo-auto_crop');
    await page.locator('.nav-item[data-tool="ocr_pdf"]').click();
    await page.evaluate(() => onJobDone('ocr_pdf', {
      outputs: ['out.pdf'], flagged_documents: [{ document: 'scan', pages: [1] }],
    }));
    await hidden('#btn-undo-ocr_pdf', false);
    await hidden('#btn-retry-flagged-ocr_pdf', false);
    await page.locator('#btn-reset-ocr_pdf').click();
    await page.waitForFunction(() => state.ocr_pdf.jobState === 'idle');
    await hidden('#btn-undo-ocr_pdf');
    await hidden('#btn-retry-flagged-ocr_pdf');
    await page.evaluate(() => onJobDone('ocr_pdf', { outputs: [], flagged_documents: [] }));
    await hidden('#btn-undo-ocr_pdf');
    await hidden('#btn-retry-flagged-ocr_pdf');
    if (process.env.DPA_QA_SCREENSHOT) await page.screenshot({ path: process.env.DPA_QA_SCREENSHOT });
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
});
