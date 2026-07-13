#!/usr/bin/env node
// Guard: jsdom must stay pinned to EXACTLY 27.0.0.
//
// Any newer jsdom (even a patch bump) pulls ESM-only transitive deps that
// Jest cannot require() on Node < 24.9 — see docs/js-testing.md (jsdom
// version constraint section) before changing this. Dependabot has
// reintroduced the bump twice (#416 and its follow-up).
//
// This lives in a file instead of the Makefile's original
// `node -e ' \ ...'` inline script because that form is a make-version trap:
// macOS's bundled GNU make 3.81 collapses backslash-newlines in recipes into
// one line (valid JS), while make 4.x on CI preserves them per POSIX — inside
// single quotes they reach node as literal backslashes, and the "script"
// dies with `SyntaxError: Expected unicode escape`. Same Makefile: green
// locally, red on CI. Pinned by tests/test_check_jsdom_pin.py.

import { readFileSync } from "node:fs";

const pkg = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);
const pinned = pkg.dependencies.jsdom;

if (pinned !== "27.0.0") {
  console.error(
    `jsdom is ${JSON.stringify(pinned)}, expected exactly "27.0.0".`,
  );
  console.error(
    "Any newer jsdom (even a patch bump) pulls ESM-only transitive deps",
  );
  console.error(
    "that Jest cannot require() on Node < 24.9 - see docs/js-testing.md",
  );
  console.error("(jsdom version constraint section) before changing this.");
  process.exit(1);
}
