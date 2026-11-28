// Browser check for the Ammanford dashboard pages. Fails (exit 1) if any page:
//  - throws a JavaScript error, - scrolls sideways at 375px (English or Welsh),
//  - has no h1, or the Welsh switch does not change the h1,
//  - renders a link that is not http(s), #, mailto: or tel:.
// Usage: node test_pages.js page1.html page2.html ...
const {chromium} = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  let failed = 0;
  for (const f of process.argv.slice(2)) {
    const tmp = f + '.t.html';
    const problems = [];
    try {
      fs.writeFileSync(tmp, '<!doctype html><meta charset="utf-8">' + fs.readFileSync(f, 'utf8'));
      const p = await b.newPage({viewport: {width: 375, height: 800}});
      const errs = []; p.on('pageerror', e => errs.push(e.message));
      await p.goto('file://' + path.resolve(tmp)); await p.waitForTimeout(1000);
      const W = 375;
      const ov1 = await p.evaluate(() => document.documentElement.scrollWidth);
      const h1en = await p.evaluate(() => document.querySelector('h1')?.innerText || '');
      const c = await p.$('#l-cy, [data-lang="cy"]');
      if (c) { await c.click(); await p.waitForTimeout(800); }
      const h1cy = await p.evaluate(() => document.querySelector('h1')?.innerText || '');
      const ov2 = await p.evaluate(() => document.documentElement.scrollWidth);
      const badLinks = await p.evaluate(() => [...document.querySelectorAll('a[href]')]
        .map(a => a.getAttribute('href')).filter(h => !/^(https?:|#|mailto:|tel:)/i.test(h.trim())).slice(0, 5));
      const wide = await p.evaluate(() => { const W = innerWidth, r = []; document.querySelectorAll('body *').forEach(e => { const b = e.getBoundingClientRect(); if (b.right > W + 1 && b.width > 0) r.push(e.tagName + '.' + e.className + ' ' + Math.round(b.right)) }); return r.slice(0, 4) });
      await p.close();
      if (errs.length) problems.push('JS errors: ' + errs.slice(0, 3).join(' | '));
      if (ov1 > W) problems.push(`scrolls sideways in English (${ov1}px)`);
      if (ov2 > W) problems.push(`scrolls sideways in Welsh (${ov2}px)`);
      if (ov1 > W || ov2 > W) problems.push('wide: ' + wide.join(', '));
      if (!h1en) problems.push('no h1');
      if (!c) problems.push('no Welsh switch found');
      else if (h1cy === h1en) problems.push('Welsh switch did not change the h1');
      if (badLinks.length) problems.push('non-http links: ' + badLinks.join(', '));
    } catch (e) {
      problems.push('could not test: ' + e.message);
    } finally {
      try { fs.unlinkSync(tmp); } catch (e) {}
    }
    if (problems.length) failed++;
    console.log(`${problems.length ? 'FAIL' : 'PASS'} ${path.basename(f)}${problems.length ? '\n  - ' + problems.join('\n  - ') : ''}`);
  }
  await b.close();
  process.exit(failed ? 1 : 0);
})();
