// Compare original vs hardened pages: page errors, number of http(s) links, and
// whether a planted javascript: URL in the data is neutralised.
// Usage: node check_links.js ORIG_DIR OUT_DIR name1 name2 ...
const {chromium} = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const [origDir, outDir, ...names] = process.argv.slice(2);
  const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  let failed = 0;
  async function load(file, html) {
    const tmp = path.join(path.dirname(file), '.t-' + path.basename(file));
    fs.writeFileSync(tmp, html);
    const p = await b.newPage({viewport: {width: 375, height: 800}});
    const errs = []; p.on('pageerror', e => errs.push(e.message));
    try {
      await p.goto('file://' + path.resolve(tmp)); await p.waitForTimeout(1200);
      await p.evaluate(() => document.querySelectorAll('[aria-expanded="false"]').forEach(x => { try { x.click() } catch (e) {} }));
      await p.waitForTimeout(300);
      const r = await p.evaluate(() => {
        const a = [...document.querySelectorAll('a[href]')].map(x => x.getAttribute('href'));
        return {http: a.filter(h => /^https?:/i.test(h)).length, bad: a.filter(h => /^\s*(javascript|data|vbscript):/i.test(h)).length};
      });
      return {...r, errs};
    } finally { await p.close(); fs.unlinkSync(tmp); }
  }
  for (const n of names) {
    const o = fs.readFileSync(path.join(origDir, n), 'utf8'), h = fs.readFileSync(path.join(outDir, n), 'utf8');
    const ro = await load(path.join(origDir, n), o), rh = await load(path.join(outDir, n), h);
    const plant = s => s.replace(/(["'])(url|src)\1\s*:\s*\1https?:\/\/[^"']+\1/, (m, q, k) => `${q}${k}${q}:${q}javascript:alert(1)${q}`);
    const eo = await load(path.join(origDir, n), plant(o)), eh = await load(path.join(outDir, n), plant(h));
    const ok = rh.errs.length === 0 && rh.http === ro.http && eh.bad === 0 && plant(h) !== h;
    if (!ok) failed++;
    console.log(`${ok ? 'PASS' : 'FAIL'} ${n}: links before ${ro.http} after ${rh.http}; errors ${rh.errs.length}; planted javascript: link rendered — before fix ${eo.bad}, after fix ${eh.bad}`, rh.errs.slice(0, 2));
  }
  await b.close(); process.exit(failed ? 1 : 0);
})();
