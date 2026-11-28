// Evaluate a page's top-level const declarations in order, in a sandbox with no DOM, and return the
// wanted ones if they survive a JSON round trip. Input on stdin: {"decls": [[name, text], ...], "want": [...]}.
// Declarations that need the DOM or a function call that fails are skipped; only wanted ones must succeed.
const vm = require("vm");

const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const ctx = vm.createContext({});
const failed = {};
for (const [name, text] of input.decls) {
  try {
    vm.runInContext(`var ${name} = (${text});`, ctx, { timeout: 2000 });
  } catch (e) {
    failed[name] = String(e.message || e).slice(0, 120);
  }
}
const values = {}, bad = {};
for (const name of input.want) {
  if (name in failed) { bad[name] = "did not evaluate: " + failed[name]; continue; }
  if (!(name in ctx)) { bad[name] = "not declared"; continue; }
  const v = ctx[name];
  // Anything JSON would silently drop or change is refused: RegExp/Set/Map -> {}, Date -> string,
  // undefined -> gone, NaN -> null. `this[k]` is the value before Date.toJSON has run.
  let marked;
  try {
    marked = JSON.stringify(v, function (k, x) {
      const o = this[k], kind = o && o.constructor && o.constructor.name;
      return o === undefined || typeof o === "function" || ["RegExp", "Set", "Map", "Date"].includes(kind) ||
        (typeof o === "number" && !Number.isFinite(o)) ? "__NOT_JSON__" : x;
    });
  } catch (e) { bad[name] = "not serialisable"; continue; }
  if (marked === undefined || marked.includes("__NOT_JSON__")) { bad[name] = "holds a RegExp, Set, Map, Date, function, undefined or NaN"; continue; }
  values[name] = JSON.parse(marked);
}
process.stdout.write(JSON.stringify({ values, bad }));
