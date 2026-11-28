// Browser check for the Neath Port Talbot What's On pages. Fails (exit 1) if any page, at 375px and 1200px:
//  - throws a JavaScript error, - scrolls sideways, - has no h1, - renders no event cards (unless --allow-empty),
//  - renders a link that is not http(s), #, mailto: or tel:, - holds Ammanford / Rhydaman / Welsh-switch text.
// Usage: node test_pages.js [--allow-empty] [--shots DIR] page1.html page2.html ...
const {chromium} = require('playwright'); const fs = require('fs'); const path = require('path');
const args = process.argv.slice(2); let allowEmpty = false, shots = null; const files = [];
for (let i = 0; i < args.length; i++) { if (args[i] === '--allow-empty') allowEmpty = true; else if (args[i] === '--shots') shots = args[++i]; else files.push(args[i]); }
// Leftover Ammanford copy or Welsh-switch code. Not Welsh words: real NPT events use them ("Dysgu Cymraeg", "Menter Iaith").
// Checked in the page's own code only, with the DATA listings taken out: real fixtures name Ammanford sides
// ("Trebanos v Ammanford", 6 Nov 2026), and that is data, not leftover template text.
const FORBIDDEN = /Ammanford|Rhydaman|CY_SUM|cy-switch/i;
function withoutData(src) {
  const m = /const\s+DATA\s*=\s*/.exec(src);
  if (!m) return src;
  let i = m.index + m[0].length, depth = 0, str = null;
  for (; i < src.length; i++) {
    const c = src[i];
    if (str) { if (c === '\\') i++; else if (c === str) str = null; continue; }
    if (c === '"' || c === "'") str = c;
    else if (c === '{' || c === '[') depth++;
    else if ((c === '}' || c === ']') && --depth === 0) { i++; break; }
  }
  return src.slice(0, m.index) + src.slice(i);
}
(async () => {
  const b = await chromium.launch({executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium'});
  let failed = 0;
  for (const f of files) {
    const tmp = f + '.t.html';
    const problems = [];
    try {
      const src = fs.readFileSync(f, 'utf8');
      const code = withoutData(src);
      if (FORBIDDEN.test(code)) problems.push('forbidden text in source: ' + code.match(FORBIDDEN)[0]);
      if (/data-lang=/.test(src)) problems.push('language switch markup present');
      fs.writeFileSync(tmp, '<!doctype html><meta charset="utf-8">' + src);
      for (const W of [375, 1200]) {
        const p = await b.newPage({viewport: {width: W, height: 800}});
        const errs = []; p.on('pageerror', e => errs.push(e.message));
        await p.goto('file://' + path.resolve(tmp)); await p.waitForTimeout(800);
        const r = await p.evaluate(() => ({
          sw: document.documentElement.scrollWidth, h1: document.querySelector('h1')?.innerText || '',
          cards: document.querySelectorAll('.ev, .mi, article.card').length,
          bad: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => !/^(https?:|#|mailto:|tel:)/i.test(h.trim())).slice(0, 5),
          text: document.body.innerText,
          wide: (() => { const w = innerWidth, o = []; document.querySelectorAll('body *').forEach(e => { const x = e.getBoundingClientRect(); if (x.right > w + 1 && x.width > 0) o.push(e.tagName + '.' + e.className + ' ' + Math.round(x.right)) }); return o.slice(0, 4) })()}));
        if (shots) await p.screenshot({path: path.join(shots, path.basename(f, '.html') + '-' + W + '.png'), fullPage: false});
        await p.close();
        const t = `@${W}px `;
        if (errs.length) problems.push(t + 'JS errors: ' + errs.slice(0, 3).join(' | '));
        if (r.sw > W) problems.push(t + `scrolls sideways (${r.sw}px); wide: ` + r.wide.join(', '));
        if (!r.h1) problems.push(t + 'no h1');
        if (!allowEmpty && !r.cards) problems.push(t + 'no event cards');
        if (r.bad.length) problems.push(t + 'non-http links: ' + r.bad.join(', '));
        if (W === 375 && !problems.length) console.log(`  ${path.basename(f)}: ${r.cards} event cards, h1 "${r.h1.replace(/\n/g, ' ')}"`);
      }
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
