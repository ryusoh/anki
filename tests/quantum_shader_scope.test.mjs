import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(
  path.join(__dirname, "..", "js", "ambient", "quantum_shader.js"),
  "utf8",
);

/**
 * Extract the body of a top-level `function name(...)` from the source.
 * Returns the full text between the opening and closing braces (inclusive).
 */
function extractFunctionBody(source, name) {
  const re = new RegExp(`^function\\s+${name}\\s*\\(`, "m");
  const match = re.exec(source);
  if (!match) return null;
  let depth = 0;
  let start = -1;
  for (let i = match.index; i < source.length; i++) {
    if (source[i] === "{") {
      if (depth === 0) start = i;
      depth++;
    } else if (source[i] === "}") {
      depth--;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Regression: cachedRect must not be referenced as a bare identifier inside
// init(). It is declared in initControls() — accessing it from init() is a
// cross-scope ReferenceError that crashes the ResizeObserver.
// ---------------------------------------------------------------------------

test("cachedRect is not referenced as a bare variable in init()", () => {
  const initBody = extractFunctionBody(src, "init");
  assert.ok(initBody, "could not extract init() body");

  // Match bare `cachedRect` usage (not as a property like `.cachedRect` or
  // inside a string/comment referencing the name through a method).
  // We look for assignments (`cachedRect =`) and reads (`cachedRect`).
  const bareRefs = [...initBody.matchAll(/(?<!\w|\.)cachedRect(?!\w)/g)];
  assert.strictEqual(
    bareRefs.length,
    0,
    `init() must not reference cachedRect directly — found ${bareRefs.length} bare reference(s). ` +
      "Use controls.invalidateRect() instead.",
  );
});

// ---------------------------------------------------------------------------
// initControls must return an object with invalidateRect so that callers
// (e.g. the resize handler in init) can invalidate the cached bounding rect.
// ---------------------------------------------------------------------------

test("initControls returns an object with invalidateRect", () => {
  const body = extractFunctionBody(src, "initControls");
  assert.ok(body, "could not extract initControls() body");

  assert.ok(
    /return\s*\{[^}]*invalidateRect\b/.test(body),
    "initControls() must return an object containing invalidateRect",
  );
});

// ---------------------------------------------------------------------------
// The resize handler inside init() must call controls.invalidateRect()
// ---------------------------------------------------------------------------

test("resize handler in init() calls controls.invalidateRect()", () => {
  const initBody = extractFunctionBody(src, "init");
  assert.ok(initBody, "could not extract init() body");

  assert.ok(
    /controls\.invalidateRect\s*\(\s*\)/.test(initBody),
    "resize handler must call controls.invalidateRect()",
  );
});

// ---------------------------------------------------------------------------
// General guard: local variables declared in initControls must not appear as
// bare identifiers in init(). Catches future cross-scope leaks.
// ---------------------------------------------------------------------------

test("no initControls local variables leak into init()", () => {
  const controlsBody = extractFunctionBody(src, "initControls");
  const initBody = extractFunctionBody(src, "init");
  assert.ok(controlsBody, "could not extract initControls() body");
  assert.ok(initBody, "could not extract init() body");

  // Collect let/const/var declarations at the top level of initControls
  const declPattern = /\b(?:let|const|var)\s+(\w+)\b/g;
  const locals = new Set();
  let m;
  while ((m = declPattern.exec(controlsBody)) !== null) {
    locals.add(m[1]);
  }

  // These are common names that may legitimately appear in both scopes
  const allowlist = new Set([
    "event",
    "target",
    "tag",
    "rect",
    "width",
    "height",
    "aspect",
    "i",
    "j",
    "k",
    "e",
    "err",
    "error",
  ]);

  const leaked = [];
  for (const name of locals) {
    if (allowlist.has(name)) continue;
    const re = new RegExp(`(?<!\\w|\\.)${name}(?!\\w)`, "g");
    // Check that it's not just in a string like "controls.X" — we want bare refs
    const refs = [...initBody.matchAll(re)];
    if (refs.length > 0) {
      leaked.push(name);
    }
  }

  assert.strictEqual(
    leaked.length,
    0,
    `initControls() locals referenced bare in init(): [${leaked.join(", ")}]. ` +
      "These will throw ReferenceError at runtime.",
  );
});
