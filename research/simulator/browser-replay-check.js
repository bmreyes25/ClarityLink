/* Actual local Chromium check. Prints assertions only; never exports capture pixels. */
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

async function main() {
  if (!process.env.CLARITY_PLAYWRIGHT_MODULE || !process.env.CLARITY_BROWSER_EXECUTABLE)
    throw Error('Set CLARITY_PLAYWRIGHT_MODULE and CLARITY_BROWSER_EXECUTABLE; see README');
  const {chromium} = require(process.env.CLARITY_PLAYWRIGHT_MODULE);
  const browser = await chromium.launch({headless: true, executablePath: process.env.CLARITY_BROWSER_EXECUTABLE});
  try {
    const page = await browser.newPage(); const errors = []; const requests = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route(/^https?:/, route => { requests.push(route.request().url()); return route.abort(); });
    await page.goto(pathToFileURL(path.join(__dirname, 'index.html')).href);
    for (const [button, evidence, checkTime, check] of [
      ['live-casting-sample', 'Observed mirror', 32, async () => {
        assert.match(await page.locator('#center-app').textContent(), /music/);
        assert.match(await page.locator('#cluster-capture-label').textContent(), /cast-music/);
        assert.equal(await page.locator('#map-plane').evaluate(e => e.classList.contains('active')), false);
      }],
      ['waze-headunit-sample', 'Observed Honda guidance', 22, async () => {
        assert.match(await page.locator('#center-app').textContent(), /home/);
        assert.match(await page.locator('#cluster-capture-label').textContent(), /waze-route/);
      }],
      ['dual-sample', 'Synthetic proposed second stream', 8, async () => {
        assert.match(await page.locator('#center-app').textContent(), /music/);
        assert.equal(await page.locator('#map-plane').evaluate(e => e.classList.contains('active')), true);
        assert.match(await page.locator('#cluster-stream').textContent(), /map-002/);
      }]]) {
      await page.locator('#' + button).click();
      assert.match(await page.locator('#replay-evidence').textContent(), new RegExp(evidence));
      const count = await page.evaluate(() => events.length); let checked = false;
      for (let i = 0; i < count; i++) {
        await page.locator('#next').click();
        assert.equal(await page.locator('#error').textContent(), '');
        if (await page.evaluate(() => state.updatedMs) === checkTime) { await check(); checked = true; }
        await page.waitForFunction(() => [...document.querySelectorAll('#center-capture,#cluster-capture')]
          .every(img => !img.hasAttribute('src') || (img.complete && img.naturalWidth === 800 && img.naturalHeight === 480)));
      }
      assert.equal(checked, true);
      if (button === 'waze-headunit-sample')
        assert.match(await page.locator('#cluster-capture-label').textContent(), /waze-ended/);
      // Observed samples end with Music/compass, not an observed unplug.
      // Inject a separately modeled disconnect for browser cleanup checks.
      await page.evaluate(() => { state = model.apply({tMs: state.updatedMs + 1, type: 'disconnected'}); render(); });
      assert.equal(await page.locator('#map-plane').evaluate(e => e.classList.contains('active')), false);
      assert.equal(await page.locator('#center-capture').getAttribute('src'), null);
      assert.equal(await page.locator('#cluster-capture').getAttribute('src'), null);
      await page.locator('#reset').click();
      assert.equal(await page.evaluate(() => model.receiver.usb.attached), false);
      console.log('PASS local browser replay: ' + evidence);
    }
    assert.deepEqual(errors, []); assert.deepEqual(requests, []);
    console.log('PASS no page errors or remote HTTP requests; capture images stayed local');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
