---
render_with_liquid: false
---

# Design spec: year/quarter calendar time filters for the stats terminal

|                                         |                                                                                                                                                             |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Status**                              | Phase 1 (single tokens, §1–§9): **implemented 2026-07-11**, all gates green. Phase 2 (spans, Part II §13–§19): **implemented 2026-07-11**, all gates green. |
| **Issue**                               | [ryusoh/anki#403 — feat: year based time filter](https://github.com/ryusoh/anki/issues/403)                                                                 |
| **Date**                                | 2026-07-11                                                                                                                                                  |
| **Scope**                               | `js/utils/timeRange.js`, `js/commands/{reviews,due,retention,handler}.js`, root `tests/`                                                                    |
| **Audience**                            | The implementing agent. Follow this doc literally; every decision is already made.                                                                          |
| **Reference implementation researched** | `~/dev/fund/js/` (the fund repo's terminal — same author, same UX conventions)                                                                              |

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as in RFC 2119.

> Both phases are implemented. Part I (§1–§9) and Part II (§13–§19) are
> shipped; see §18 for the Phase 2 acceptance status.

---

# Part I — Phase 1: single calendar tokens (IMPLEMENTED)

---

## 1. Summary

The stats terminal (`js/terminal.js` + `js/commands/`) currently accepts only
_relative_ time ranges — "the last N days" (`1m`, `2y`, `1y4m`, `all`). This
feature adds _calendar_ range tokens, ported from the fund repo's terminal:

| Token    | Meaning                            | Example resolved range      |
| -------- | ---------------------------------- | --------------------------- |
| `2025`   | full calendar year                 | `2025-01-01` … `2025-12-31` |
| `2023q2` | one quarter (case-insensitive `q`) | `2023-04-01` … `2023-06-30` |

They work **everywhere an existing `[range]` is accepted**, including the bare
"range shortcut" form that re-renders the current chart:

```
plot reviews 2025        reviews deck 2023q2      retention 2024
plot due 2027            due 2027                 2025          ← bare shortcut
```

Past-facing charts (`reviews`, `retention`) filter their date-keyed entries to
the calendar window. The future-facing chart (`due`) maps the window onto
day-offsets from today; a fully-past window renders as empty data.

**No command-routing changes are needed.** The router (`js/commands/handler.js`)
gates every range through `isValidRange()` and generic `(.+)` regexes, so
teaching `isValidRange`/the data-access functions about calendar tokens is
sufficient (verified claim, §3.2).

---

## 2. Research findings — the fund implementation

Everything below was read from the fund repo source on 2026-07-11. Cited as
`file:line` relative to `~/dev/fund/`.

### 2.1 Token parsing

- `parseQuarterToken(token, fallbackYear)` (`js/utils/date.js:276-295`) accepts
  two forms: explicit `^\s*(\d{4})q([1-4])\s*$/i` and bare `^\s*q([1-4])\s*$/i`
  (bare form resolves against a remembered "context year").
- Plain years are parsed with `parseInt` and bounds-checked
  `year >= 1900 && year <= currentYear + 5` (`js/transactions/terminal/dateUtils.js:92-98`).
- `resolveQuarterRange(year, quarter, mode)` (`js/utils/date.js:303-321`)
  computes quarter boundaries with `Date.UTC` arithmetic (first day of quarter;
  first day of next quarter minus 24 h).

### 2.2 Range grammar

`parseDateRange` / `parseSimplifiedDateRange`
(`js/transactions/terminal/dateUtils.js:74-187,258-337`) support single tokens
(`2023`, `2023q1`), `from <tok>` / `f:<tok>`, `<tok> to <tok>` / `<tok>:<tok>`,
and a module-level `lastContextYear` so a later bare `q2` means "Q2 of the year
you last mentioned" (`dateUtils.js:8,53-65`).

### 2.3 Consumption

The parsed `{from, to}` (ISO `YYYY-MM-DD` strings or `null`) is stored as
`transactionState.chartDateRange` and every chart/summary filters by comparing
entry dates against it (`js/transactions/terminal/handlers/plot.js:123-151`,
`js/transactions/terminal/snapshots.js:168-170` and ~10 similar sites).
`formatDateRange` reverse-maps a range back to a human label — `"Q2 2023"`,
`"2023"`, or `"<from> to <to>"` (`dateUtils.js:189-256`).

### 2.4 Pitfall documented in the fund repo (we inherit the fix)

`normalizeDateOnly` (`js/utils/date.js:327-340`) warns that
`new Date('YYYY-MM-DD')` parses as **UTC midnight**, which shifts to the
previous day in UTC-negative timezones. Bare date strings must be constructed
at _local_ midnight via `new Date(y, m-1, d)`. This spec adopts that rule
(§5.1) and otherwise avoids `Date` entirely by comparing ISO strings
lexicographically.

### 2.5 What we deliberately do NOT port (non-goals, v1)

| Fund feature                                               | Why cut from Phase 1                                                                             |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Bare `q2` with `lastContextYear` (`dateUtils.js:8`)        | Cross-module mutable state; not in the issue's examples. Deferred (§10).                         |
| Colon syntax `f:<tok>` / `to:<tok>` / `<tok>:<tok>`        | Single-token, so it DOES fit our grammar — **ported in Phase 2 (Part II, §13)**, not deferred.   |
| Multi-word `from <tok>` / `<tok> to <tok>`                 | Multi-token grammar collides with this terminal's `[range]`-is-one-token design. Deferred (§10). |
| `mode: 'start'/'end'` half-open ranges (`date.js:314-319`) | Subsumed by Phase 2's nullable `from`/`to` bounds (§14.2) — no separate mode parameter needed.   |

---

## 3. Current system in this repo (verified facts)

### 3.1 Range pipeline

- `js/utils/timeRange.js` — `parseRange(key)` → **number of days**, `null` for
  `"all"`, `undefined` if invalid. Grammar `^(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)d)?$`
  (`timeRange.js:17`). `isValidRange = parseRange(k) !== undefined`
  (`timeRange.js:58-60`). `formatRange` → `"N days"` / `"all time"` /
  `"unknown"` (`timeRange.js:67-72`).
  - A bare 4-digit token like `2025` does **not** match this grammar today
    (no `y/m/d` suffix), so there is **no grammar collision** with the new
    tokens. Verified by reading the regex; pinned by a new test (§7.1).
- `js/commands/reviews.js:20-153` `getReviewStatsData(rangeKey, byDeck)` slices
  `window.reviewStatsData.reviews` by **index count**:
  `allData.slice(allData.length - days)`, and accumulates a `preSliceSum` of
  everything before the slice (needed by cumulative charts). The by-deck branch
  slices the global array the same way, then pads each deck's entries onto the
  global slice's date axis (`targetDates`), computing `preSliceSumsByDeck` from
  entries dated before `firstTargetDate` (`reviews.js:42-63`).
- `js/commands/due.js:21-57` `getFutureDueData(rangeKey, byDeck)` keeps entries
  with `e.day < days` (`day` = offset from today, `0` = today).
  `renderFutureDueChart` (`due.js:59-280`) places counts at array index
  `i = e.day` and labels indexes `Today / Tomorrow / +Nd` (`due.js:129-133`).
- `js/commands/retention.js:172-191` `showRetention` reuses
  `getReviewStatsData(rangeKey)` — it inherits whatever reviews filtering does.
- `js/commands/handler.js` routes ranges via `isValidRange` at 16 call sites
  and via `(.+)` capture groups in `dynamicPatterns` (`handler.js:695-699`).
  A token that is a valid range by itself is a "shortcut" that re-renders the
  current chart with the new range (`handler.js:693,727-729`,
  `handleTimeRangeShortcut` at `handler.js:113-148`).

### 3.2 Why the router needs zero changes (claim, verified by trace)

- Bare `2025`: `handleCommand` computes `isShortcut = isValidRange("2025")`
  (`handler.js:693`). Once `isValidRange` accepts calendar tokens, this
  bypasses the trie-rejection branch (`handler.js:708`) and enters
  `handleTimeRangeShortcut` (`handler.js:727-729`). No trie insertions needed.
- `plot reviews 2025`: matches `dynamicPatterns[0]`'s `(.+)` (`handler.js:696`),
  then `handlePlotCommand`'s regex captures `rangeStr = "2025"`
  (`handler.js:307-316`) and gates it with `isValidRange`.
- `reviews deck 2023q2`, `due 2027`, `retention 2024`, `show due 2025`: same
  story through `handleRegexCommands` (`handler.js:454-680`) — every range
  position is a `(.+)` or `parts[2]` gated by `isValidRange`.

### 3.3 Data reality (measured against the live JSON on 2026-07-11)

- `data/anki/review_stats_data.json` → `reviews`: 2 316 entries,
  `2020-02-13` … `2026-07-10`, sorted ascending, **17 gaps** (days with no
  reviews are absent). ⇒ **Calendar filtering MUST compare `entry.date`
  strings, never do index arithmetic** (the existing `length - days` slice is
  a knowingly-approximate legacy behavior we leave untouched for duration
  keys).
- Every `reviewsByDeck` entry's `date` also appears in the global `reviews`
  array (0 violations measured). ⇒ the by-deck padding logic keyed off the
  global slice's dates remains correct when only the global-slice selection
  changes (§5.3).
- `data/anki/custom_stats_data.json` → `futureDue`: contiguous `day` offsets
  `0…7089` today, but `renderFutureDueChart` already treats it as sparse
  (`daySparseMap`, `due.js:155-163`) — new code MUST also tolerate sparseness
  (use filtering, not slicing).
- Entry dates are written by the Python exporter in **local** time; the whole
  feature stays in local-date space (§5.1).

---

## 4. UX specification

### 4.1 Grammar (normative)

```
range          = duration | calendar
duration       = existing grammar, UNCHANGED   ; 1m..12m, Ny, Nd, combos, "all"
calendar       = year | quarter
year           = 4DIGIT 4DIGIT 4DIGIT 4DIGIT           ; 1970 <= year <= 2099
quarter        = year ("q" / "Q") ("1"/"2"/"3"/"4")
```

- Tokens are trimmed and matched case-insensitively (input is already
  lowercased by `handleCommand`, but `timeRange.js` MUST lowercase/trim
  defensively itself, as `parseRange` does today).
- Year bounds are **fixed constants** `1970`/`2099` (unlike the fund's
  `currentYear + 5`) so parsing is deterministic and clock-independent.
  Rationale: a 4-digit day-count like `3650` (10 years in days) must not be
  swallowed as a year; the upper bound keeps huge counts unambiguous, and no
  Anki collection predates 1970.

### 4.2 Behavior matrix

With today = `2026-07-11` (examples; behavior is defined relative to "today"):

| Input                                    | Chart     | Result                                                                                         |
| ---------------------------------------- | --------- | ---------------------------------------------------------------------------------------------- |
| `plot reviews 2025`                      | reviews   | entries with `2025-01-01 ≤ date ≤ 2025-12-31`; message `Rendered review history chart (2025).` |
| `plot reviews 2023q2`                    | reviews   | entries in `2023-04-01…2023-06-30`; message `… (2023 Q2).`                                     |
| `retention 2024`                         | retention | retention line over 2024 entries                                                               |
| `plot due 2026`                          | due       | day-offsets `0…173` (window clamped to start today — past days have no due data)               |
| `plot due 2027`                          | due       | day-offsets `174…538`, x-axis labeled with real dates (§5.4)                                   |
| `plot due 2025`                          | due       | empty ⇒ existing "No future reviews in this range." path                                       |
| `reviews 2027` (future year, past chart) | reviews   | empty slice ⇒ existing "No review data available." path                                        |
| bare `2023q2` after `pr`                 | reviews   | re-renders current chart with the quarter (shortcut path)                                      |
| bare `2025` with no chart yet            | due       | defaults to due chart (existing shortcut behavior, `handler.js:145-147`)                       |
| `plot reviews 2101`                      | —         | invalid range ⇒ existing `Unknown range: 2101` message                                         |
| `plot reviews 2023q5`                    | —         | invalid range (same path)                                                                      |

Cumulative review charts over a calendar window MUST seed their running totals
with the pre-window sums (`preSliceSum` semantics preserved), i.e.
`plot reviews cumulative 2025` starts the y-axis at the all-history total as of
`2024-12-31` — same convention the duration ranges use today.

The active range persists exactly like duration ranges do: after
`plot reviews 2025`, typing `retention` renders retention for 2025
(`activeTimeRange` mechanism, `handler.js:20,84`, untouched).

### 4.3 Messages and help (normative strings)

- Range display label: `2025` → `"2025"`; `2023q2` → `"2023 Q2"` (matches the
  fund's `formatDateRange` output style, `dateUtils.js:238,243`).
- The 12 duplicated error hints `"Valid ranges: 1m-12m, 1y-Ny, all"` in
  `handler.js` MUST be replaced by one exported constant:

  ```js
  export const RANGE_HELP =
    "Valid ranges: 1m-12m, 1y-Ny, Nd, combos (1y4m), YYYY (e.g. 2025), YYYYqN (e.g. 2023q2), all";
  ```

- `showHelp` and `listCharts` (`handler.js:746-825`) and `getReviewsHelp`
  (`reviews.js:779-816`) each gain one line in their "Time ranges/Ranges"
  block (indented like its neighbors): `2025, 2023q2 (calendar year / quarter)`.

---

## 5. Detailed design

Implementation surface is four files plus tests. **Do the steps in §8 order.**

### 5.1 Date-handling rules (apply everywhere)

1. All range boundaries are ISO `YYYY-MM-DD` strings; compare entry dates with
   plain string operators (`from <= e.date && e.date <= to`). Zero-padded ISO
   strings order lexicographically — no `Date` objects needed for filtering.
2. When a real `Date` is unavoidable (due-chart offsets only):
   **never** call `new Date("YYYY-MM-DD")` or `Date.parse` (UTC-midnight trap,
   §2.4). Build local dates: `new Date(y, m - 1, d)`.
3. Day differences: `Math.round((b - a) / 86400000)` between two local-midnight
   dates (`Math.round` absorbs DST's ±1 h).
4. Quarter boundaries come from a constant table — quarter end-days never vary
   (leap years only affect February, which is never a quarter boundary):
   Q1 `01-01…03-31`, Q2 `04-01…06-30`, Q3 `07-01…09-30`, Q4 `10-01…12-31`.

### 5.2 `js/utils/timeRange.js` — the only place that understands tokens

Add a tagged-union **RangeSpec** and keep every existing export
backward-compatible. `parseRange`'s duration behavior MUST NOT change (pinned
by `tests/timeRange.test.cjs`).

Reference implementation (add below the existing code; JSDoc included — the
repo lints with ESLint, 2-space indent, double quotes, trailing semicolons):

```js
/**
 * @typedef {% raw %}{{ kind: "duration", days: number }{% endraw %}
 *         | { kind: "all" }
 *         | { kind: "calendar", from: string, to: string, label: string }} RangeSpec
 */

const CALENDAR_RE = /^(\d{4})(?:q([1-4]))?$/;
const QUARTER_BOUNDS = {
  1: ["01-01", "03-31"],
  2: ["04-01", "06-30"],
  3: ["07-01", "09-30"],
  4: ["10-01", "12-31"],
};
const MIN_YEAR = 1970;
const MAX_YEAR = 2099;

/**
 * Parse a calendar token ("2025", "2023q2") into a calendar RangeSpec.
 * @param {string} rangeKey
 * @returns {RangeSpec|undefined} calendar spec, or undefined if not calendar
 */
export function parseCalendarRange(rangeKey) {
  if (!rangeKey || typeof rangeKey !== "string") return undefined;
  const match = rangeKey.trim().toLowerCase().match(CALENDAR_RE);
  if (!match) return undefined;
  const year = parseInt(match[1], 10);
  if (year < MIN_YEAR || year > MAX_YEAR) return undefined;
  if (match[2]) {
    const quarter = parseInt(match[2], 10);
    const [start, end] = QUARTER_BOUNDS[quarter];
    return {
      kind: "calendar",
      from: `${year}-${start}`,
      to: `${year}-${end}`,
      label: `${year} Q${quarter}`,
    };
  }
  return {
    kind: "calendar",
    from: `${year}-01-01`,
    to: `${year}-12-31`,
    label: `${year}`,
  };
}

/**
 * Parse any range token into a RangeSpec.
 * @param {string} rangeKey
 * @returns {RangeSpec|undefined} undefined if invalid
 */
export function parseRangeSpec(rangeKey) {
  const calendar = parseCalendarRange(rangeKey);
  if (calendar) return calendar;
  const days = parseRange(rangeKey);
  if (days === null) return { kind: "all" };
  if (days === undefined) return undefined;
  return { kind: "duration", days };
}

/**
 * Map a calendar spec onto due-chart day offsets relative to `now`.
 * @param {RangeSpec} spec - must be kind "calendar"
 * @param {Date} [now] - injectable for tests
 * @returns {% raw %}{{start: number, end: number}{% endraw %}|null} inclusive offsets, clamped to
 *   start >= 0; null when the whole window is in the past (end < 0)
 */
export function calendarRangeToDayOffsets(spec, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const toLocal = (iso) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  };
  const diff = (target) => Math.round((target - today) / 86400000);
  const end = diff(toLocal(spec.to));
  if (end < 0) return null;
  return { start: Math.max(0, diff(toLocal(spec.from))), end };
}
```

Then modify the two existing helpers (surgical edits):

```js
// isValidRange (timeRange.js:58-60) — one-line body change:
export function isValidRange(rangeKey) {
  return parseRangeSpec(rangeKey) !== undefined;
}

// formatRange (timeRange.js:67-72) — handle calendar first:
export function formatRange(rangeKey) {
  const spec = parseRangeSpec(rangeKey);
  if (spec === undefined) return "unknown";
  if (spec.kind === "all") return "all time";
  if (spec.kind === "calendar") return spec.label;
  return `${spec.days} days`;
}
```

Ordering note: `parseCalendarRange` and `parseRange` accept disjoint token
sets (§3.1), so `parseRangeSpec`'s try-calendar-first order is safe.

### 5.3 `js/commands/reviews.js` — calendar filtering for past data

`getReviewStatsData(rangeKey, byDeck)` (`reviews.js:20-153`). Import
`parseRangeSpec` alongside the existing imports. At the top, compute
`const spec = parseRangeSpec(rangeKey);`.

**Shared helper** (module-private, add above `getReviewStatsData`):

```js
/**
 * Index window [start, end) of entries with from <= date <= to.
 * Entries are sorted ascending by date; linear scan is fine (~2.3k entries).
 */
function calendarSliceBounds(entries, spec) {
  let start = 0;
  while (start < entries.length && entries[start].date < spec.from) start++;
  let end = start;
  while (end < entries.length && entries[end].date <= spec.to) end++;
  return { start, end };
}
```

**Non-deck branch** (`reviews.js:109-152`): the current code derives
`sliceIndex` from `days` and slices `[sliceIndex, length)`. Rework the branch
so all three range kinds produce `{ start, end }` and share the existing
`preSliceSum` loop:

- `spec.kind === "all"` (or `spec === undefined`, preserving today's fallback):
  `start = 0, end = allData.length` — keep returning the full copy with a
  zeroed `preSliceSum` exactly as now (`reviews.js:110-124`).
- `spec.kind === "duration"`: `start = Math.max(0, allData.length - spec.days),
end = allData.length` — identical to today.
- `spec.kind === "calendar"`: `({ start, end } = calendarSliceBounds(allData, spec))`.

Then `const slice = allData.slice(start, end);` and run the existing
`preSliceSum` accumulation loop over `[0, start)` (it already loops
`i < sliceIndex`; rename the bound to `start`). The returned array keeps its
`preSliceSum` expando property — **do not change the return shape**.

**By-deck branch** (`reviews.js:25-107`): only the global-slice selection
changes. Replace the `days !== null && days !== undefined` block
(`reviews.js:31-34`) with the same three-way `{ start, end }` computation and
`globalSlice = globalData.slice(start, end);`. Everything downstream
(`targetDates`, `firstTargetDate`, per-deck padding, `preSliceSumsByDeck`)
stays byte-identical — it is already date-keyed off the global slice, and every
deck date is guaranteed to appear in the global array (§3.3), so no deck entry
inside the window can be dropped.

**Message** — `showReviews` (`reviews.js:764-777`): replace the two lines
computing `days`/`rangeText` with `const rangeText = formatRange(rangeLabel);`
(import `formatRange`). For durations this produces the identical string
(`"90 days"`), so existing message assertions keep passing; calendar ranges
produce `(2025)` / `(2023 Q2)`.

### 5.4 `js/commands/due.js` — calendar window on day offsets

**Data** — `getFutureDueData(rangeKey, byDeck)` (`due.js:21-57`): compute
`const spec = parseRangeSpec(rangeKey);` and branch:

- `undefined` or `kind === "all"`: return `allData` unchanged (today's
  behavior for `null`/`undefined` days).
- `kind === "duration"`: keep the existing code paths verbatim
  (`e.day < days` early-exit loop for by-deck, `slice(0, days)` for global).
- `kind === "calendar"`:

  ```js
  const offsets = calendarRangeToDayOffsets(spec);
  // Whole window already in the past -> nothing is due there.
  if (!offsets) return byDeck ? {} : [];
  const inWindow = (e) => e.day >= offsets.start && e.day <= offsets.end;
  ```

  Global: `return allData.filter(inWindow);`. By-deck: build `limitedData`
  with `entries.filter(inWindow)` per deck (keep the `Array.isArray(entries)`
  guard). Use `filter`, not index slicing — treat `day` as sparse (§3.3).

**Labels** — `renderFutureDueChart(data, byDeck, rangeDays)`
(`due.js:59-280`): a calendar window that starts in the future produces
entries whose smallest `day` is > 0; today's renderer would prepend hundreds
of zero bars labeled `+1d…` before the window. Fix by rebasing on the minimum
day and labeling calendar mode with real dates:

1. Change the signature to
   `renderFutureDueChart(data, byDeck = false, rangeDays = null, rangeSpec = null)`.
2. Where `maxDay` is computed (`due.js:107-121`), also compute `minDay` the
   same way (initialize to `Infinity`, take `Math.min`; if no entries,
   `minDay = 0`). For all existing inputs data starts at day 0, so
   `minDay === 0` and nothing changes — this is the backward-compat guarantee.
3. `numDays = maxDay - minDay + 1`. Every place that writes
   `counts[i] = map[i] || 0` becomes `counts[i] = map[minDay + i] || 0`
   (three sites: `due.js:163,225-226`).
4. Label loop (`due.js:129-133`):

   ```js
   const isCalendar = rangeSpec && rangeSpec.kind === "calendar";
   const base = new Date();
   const todayLocal = new Date(
     base.getFullYear(),
     base.getMonth(),
     base.getDate(),
   );
   for (let i = 0; i < numDays; i++) {
     const day = minDay + i;
     if (isCalendar) {
       const d = new Date(
         todayLocal.getFullYear(),
         todayLocal.getMonth(),
         todayLocal.getDate() + day,
       );
       const mm = String(d.getMonth() + 1).padStart(2, "0");
       const dd = String(d.getDate()).padStart(2, "0");
       labels[i] = `${d.getFullYear()}-${mm}-${dd}`;
     } else if (day === 0) labels[i] = "Today";
     else if (day === 1) labels[i] = "Tomorrow";
     else labels[i] = `+${day}d`;
   }
   ```

   (`new Date(y, m, d + day)` overflows correctly across month/year ends.)

**Wiring** — `showDue` (`due.js` around lines 365-380): pass the spec through
and reuse `formatRange` for the message, mirroring §5.3:

```js
const spec = parseRangeSpec(rangeLabel);
const rangeText = formatRange(rangeLabel);
const result = renderFutureDueChart(data, byDeck, days, spec);
```

(`days` from `parseRange` is still passed as `rangeDays`; it is `undefined`
for calendar tokens, which downstream already treats like `null` — check the
one place `rangeDays` is used before relying on it, and do not remove it.)

### 5.5 `js/commands/retention.js`

No filtering changes — it reuses `getReviewStatsData` (§3.1). Only the message:
in `showRetention` (`retention.js:181-190`) replace the `days`/`rangeText`
computation with `formatRange(rangeLabel)` as in §5.3.

### 5.6 `js/commands/handler.js`

1. Add `RANGE_HELP` (§4.3) to the `timeRange.js` imports (define the constant
   in `timeRange.js` so `reviews.js` help can also use it, and re-export it
   from `handler.js` like `DEFAULT_RANGE` is at `handler.js:17`).
2. Replace all 12 literal `"Valid ranges: 1m-12m, 1y-Ny, all"` occurrences
   (`handler.js:318,463,476,491,510,529,545,565,585,603,629,649`) with
   `appendLine(RANGE_HELP, "muted")`.
3. Add the calendar examples line to `showHelp` and `listCharts` (§4.3).
4. **Nothing else.** No trie changes (`js/utils/trie.js` untouched — §3.2),
   no new routing branches, no changes to `handleTimeRangeShortcut`.

---

## 6. Explicit DO-NOTs (each has bitten someone before)

1. **Do not** change `parseRange`'s duration grammar or return values —
   `tests/timeRange.test.cjs` pins it.
2. **Do not** filter reviews by index arithmetic for calendar ranges — the
   array has gaps (§3.3); compare `entry.date` strings.
3. **Do not** use `new Date("YYYY-MM-DD")` / `Date.parse` anywhere (§5.1).
4. **Do not** change return shapes: `getReviewStatsData` returns an array with
   a `preSliceSum` expando (or the by-deck object), `getFutureDueData` returns
   an array/object — callers and tests destructure these.
5. **Do not** insert year tokens into the command trie — the shortcut path
   bypasses it (§3.2) and enumerating years would bloat autocomplete.
6. **Do not** run the Python suites for this change; the JS gate is
   `make check-node` (root `tests/` only — a `*.test.js` anywhere else
   silently never runs; see `docs/js-testing.md`).
7. Run everything **from the repo root**; use `python3` if Python is ever
   needed (CLAUDE.md).

---

## 7. Test plan

Tests live in root `tests/`, discovered by `tools/node_test_runner.mjs`
(`*.test.js|cjs|mjs`). Follow the existing pattern: CommonJS file, mock
`global.document`/`global.window` where DOM is touched (copy the mock block
from `tests/handler_coverage.test.cjs:1-55`), dynamically `await import()` the
ESM source so c8 sees coverage (`tests/timeRange.test.cjs:22`).

### 7.1 `tests/timeRange_calendar.test.cjs` (pure logic, no DOM)

| Case                                                                                | Expectation                                                           |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `parseRangeSpec("2025")`                                                            | `{kind:"calendar", from:"2025-01-01", to:"2025-12-31", label:"2025"}` |
| `parseRangeSpec("2023q2")`, `"2023Q2"`, `" 2023q2 "`                                | `{…, from:"2023-04-01", to:"2023-06-30", label:"2023 Q2"}`            |
| all four quarters of one year                                                       | boundary table from §5.1(4)                                           |
| `"2024q1"` (leap year)                                                              | `to === "2024-03-31"` (leap day irrelevant — documents why)           |
| `"2023q5"`, `"2023q0"`, `"202"`, `"20255"`, `"1969"`, `"2100"`, `"q2"`, `"2023 q2"` | `undefined` (calendar-wise) — and `isValidRange` false for each       |
| `parseRangeSpec("3m")`                                                              | `{kind:"duration", days:90}`                                          |
| `parseRangeSpec("all")`                                                             | `{kind:"all"}`                                                        |
| `parseRange("2025")`                                                                | still `undefined` (no grammar collision)                              |
| `isValidRange("2025")`, `isValidRange("2023q2")`                                    | `true`                                                                |
| `formatRange("2025")`, `formatRange("2023q2")`                                      | `"2025"`, `"2023 Q2"`                                                 |
| `formatRange("3m")`, `formatRange("all")`                                           | unchanged `"90 days"`, `"all time"`                                   |
| `calendarRangeToDayOffsets(spec2026, now=2026-07-11)`                               | `{start:0, end:173}` (clamped)                                        |
| `calendarRangeToDayOffsets(spec2027, now=2026-07-11)`                               | `{start:174, end:538}`                                                |
| `calendarRangeToDayOffsets(spec2025, now=2026-07-11)`                               | `null`                                                                |
| quarter spanning today (`2026q3`, now=2026-07-11)                                   | `{start:0, end:81}`                                                   |

Construct `now` as `new Date(2026, 6, 11)` (local), never from a string.

### 7.2 `tests/reviews_calendar.test.cjs`

Mock `window.reviewStatsData` with hand-built entries **including a date gap**
and multiple years, e.g. dates `2024-12-30, 2024-12-31, 2025-01-01, 2025-01-03,
2025-06-30, 2026-01-01` (note missing `2025-01-02`).

- `getReviewStatsData("2025")` returns exactly the three 2025 entries;
  `preSliceSum` equals the sum of the two 2024 entries' fields.
- `getReviewStatsData("2025q1")` returns the two Q1 entries.
- `getReviewStatsData("2027")` returns `[]` with a fully-populated zero/summed
  `preSliceSum` (sum of _all_ entries — everything is before the window).
- By-deck: `getReviewStatsData("2025", true)` — `dates` are the three 2025
  dates; a deck with an entry only on `2024-12-31` gets its count in
  `preSliceSumsByDeck` and zero-padded rows in the window.
- Regression: `getReviewStatsData("1m")` and `("all")` byte-match their
  pre-change outputs on the same mock (compute expected by hand).

### 7.3 `tests/due_calendar.test.cjs`

Mock `window.customStatsData.futureDue = [{day:0,…}, {day:1,…}, …, {day:600,…}]`
(include a deliberate hole to prove sparseness-tolerance). Freeze "today" by
injecting `now` where the API allows; for `renderFutureDueChart` label checks,
compute expected labels from the real current date at test runtime (the test
must not assume a fixed today).

- `getFutureDueData("<current year>")` keeps only offsets `0…(days to Dec 31)`.
- `getFutureDueData("<next year>")` keeps only next-year offsets (start > 0).
- `getFutureDueData("<last year>")` → `[]`; by-deck → `{}`.
- Render with a mock `Chart` class capturing `config` (pattern in
  `handler_coverage.test.cjs:38-46`): for a next-year spec, first label is
  next year's Jan 1 as `YYYY-MM-DD` and dataset arrays have no leading-zero
  run; for duration specs labels still start `Today, Tomorrow, +2d`.

### 7.4 `tests/handler_calendar.test.cjs` (routing, end-to-end through `handleCommand`)

Reuse the DOM/window mock block. Assert on the returned
`{handled, command, range}` and captured `appendLine` lines:

- `handleCommand("plot reviews 2025", log)` → `handled:true`,
  `command:"plot-reviews"`, `range:"2025"`, no `Unknown range` line.
- `handleCommand("plot due 2027", log)` → `plot-due` with `range:"2027"`.
- `handleCommand("retention 2024q4", log)` → retention path.
- Bare `handleCommand("2023q2", log)` after a reviews command → shortcut path
  re-renders reviews (`command` starts with `"reviews"`), `range:"2023q2"`.
- `handleCommand("plot reviews 2101", log)` → error result, message includes
  `Unknown range: 2101` and the new `RANGE_HELP` text.

### 7.5 Gate

```sh
make check-node     # node runner + jest(review_heatmap) + c8 coverage
make lint           # eslint/stylelint/markdownlint (this doc must pass markdownlint)
make precommit      # full gate before merging
```

All pre-existing tests MUST pass unmodified **except** message-text assertions
that hardcode `"Valid ranges: 1m-12m, 1y-Ny, all"`, which may be updated to
`RANGE_HELP` (search `tests/` for that literal first and list the hits in the
PR description).

**Known pre-existing failures — NOT yours to fix.** See "Known pre-existing
failures" in `docs/js-testing.md` (the `review_heatmap` jest/Node-version
mismatch and the cosmetic `handler_coverage.test.cjs` print) — both predate
this feature and are unrelated to it; do not chase them. The bar for this
feature is: all root `tests/` suites green in the node-runner portion of
`make check-node`, plus `fmt-check`/`lint`/`quality-py` clean.

---

## 8. Implementation order (one commit per step is fine)

1. `js/utils/timeRange.js`: add `parseCalendarRange`, `parseRangeSpec`,
   `calendarRangeToDayOffsets`, `RANGE_HELP`; update `isValidRange`,
   `formatRange`. Write §7.1 tests. Run `make check-node` — all pre-existing
   tests must still be green. Known intermediate state: consumers still call
   `parseRange`, which returns `undefined` for calendar tokens, and both data
   functions treat that as "all" — so calendar tokens now route successfully
   but render the full history. This is acceptable mid-branch; steps 2–3 fix
   it. Do not stop after step 1.
2. `js/commands/reviews.js` (§5.3) + §7.2 tests.
3. `js/commands/due.js` (§5.4) + §7.3 tests.
4. `js/commands/retention.js` (§5.5) — covered by existing retention tests plus
   one message assertion added to §7.4.
5. `js/commands/handler.js` (§5.6) + §7.4 tests; update help text and any
   stale literal in existing tests.
6. `make precommit`; fix lint/format fallout only (no design changes).

---

## 9. Acceptance criteria — Phase 1 status (verified 2026-07-11)

- [ ] Every row of the §4.2 behavior matrix holds when run manually in the
      terminal UI against the live JSON. _(Not yet manually exercised — only
      pinned by the automated suites below.)_
- [x] All §7 tests pass via the node-runner portion of `make check-node`
      (68/68 suites, 100% line coverage on every touched file); `fmt-check`,
      `lint`, `quality-py`, `check-py` all green. (`make precommit` cannot
      fully pass in this environment — see §7.5 known failure 1.)
- [x] `git grep "Valid ranges: 1m-12m, 1y-Ny, all"` returns nothing in source
      (only this doc mentions the old literal, descriptively).
- [x] No changes under `js/utils/trie.js`, `js/terminal.js`, or the Python
      exporters.
- [x] Duration ranges (`1m`, `2y6m15d`, `all`) behave byte-identically
      (regression cases in §7.2/§7.3).

Phase 1 tests shipped: `tests/timeRange_calendar.test.cjs` (19),
`tests/reviews_calendar.test.cjs` (5), `tests/due_calendar.test.cjs` (6),
`tests/retention_calendar.test.cjs` (3), `tests/handler_calendar.test.cjs` (7).

## 10. Deferred (out of scope for BOTH phases, do not implement)

- Bare `qN` with a remembered context year (fund `dateUtils.js:8-65`).
- Multi-word span syntax: `from 2023`, `2023 to 2024` (fund
  `dateUtils.js:74-187`) — multi-token, collides with the one-token `[range]`
  grammar. The colon forms (`2020:2023`, `f:2026`, `to:2028`) are NOT
  deferred — they are Phase 2 (Part II).
- Month tokens (`2025-03`) — natural extension of the token grammar.
- Autocomplete/trie entries for calendar tokens.

## 11. Open questions / unverified

- Issue #403's body is an empty template (fetched via GitHub API 2026-07-11);
  scope was taken from its title ("feat: year based time filter") and the
  examples supplied with the request (`2026, 2025, 2027, 2023q2`). If span
  syntax was silently expected, it is §10 work.
- `rangeDays` (3rd param of `renderFutureDueChart`) is `undefined` in calendar
  mode; §5.4 asserts downstream tolerates it — the implementer MUST grep its
  uses inside the function and confirm before relying on this.

## 12. Source index

| Claim area                                 | Primary source                                                                                                          |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Fund token parsing / quarter resolution    | `~/dev/fund/js/utils/date.js:256-321`                                                                                   |
| Fund range grammar & context year          | `~/dev/fund/js/transactions/terminal/dateUtils.js`                                                                      |
| Fund consumption & UX                      | `~/dev/fund/js/transactions/terminal/handlers/plot.js:118-151`                                                          |
| UTC-midnight pitfall                       | `~/dev/fund/js/utils/date.js:327-340`                                                                                   |
| This repo's range pipeline                 | `js/utils/timeRange.js`, `js/commands/handler.js:682-744`                                                               |
| Reviews/due/retention data access          | `js/commands/reviews.js:20-153`, `js/commands/due.js:21-57`, `js/commands/retention.js:172-191`                         |
| Data-shape measurements (gaps, invariants) | `data/anki/review_stats_data.json`, `data/anki/custom_stats_data.json`, measured 2026-07-11                             |
| Test conventions                           | `tests/timeRange.test.cjs`, `tests/handler_coverage.test.cjs`, `tools/node_test_runner.mjs:11-23`, `docs/js-testing.md` |

---

# Part II — Phase 2: span and open-ended range tokens (TO IMPLEMENT)

Everything in Part II assumes Phase 1 is already merged (it is — see the
status table). Line numbers below cite the **post-Phase-1** source as of
2026-07-11. Re-verify each cited line before editing; if it has drifted,
locate the construct by name, not by number.

## 13. Summary and grammar

Phase 2 ports the fund's **colon syntax** (`parseSimplifiedDateRange`,
`~/dev/fund/js/transactions/terminal/dateUtils.js:258-337`) — the remaining
feature-parity gap named in the follow-up request: `2027:2028`, `f:2026`,
`to:2028`. These are all **single tokens** (no spaces), so they fit the
one-token `[range]` grammar and — exactly as in Phase 1 §3.2 — **the router
needs zero changes**. Verified 2026-07-11: all four example tokens currently
return `isValidRange(...) === false` / `parseRangeSpec(...) === undefined`,
so there is no grammar collision to migrate around.

### 13.1 Grammar (normative)

```
range      = duration | calendar            ; duration UNCHANGED (Part I)
calendar   = unit | span | open-from | open-to
unit       = year | quarter                  ; Phase 1 tokens, UNCHANGED
span       = unit ":" unit                   ; e.g. 2020:2023, 2023q1:2024q2, 2023:2024q2
open-from  = ("f" / "from") ":" unit         ; e.g. f:2026, from:2026, f:2023q2
open-to    = "to" ":" unit                   ; e.g. to:2028, to:2023q2
```

- One colon exactly; a token containing a colon MUST split into exactly two
  non-empty parts (`"2023::2024"` and `":2023"` and `"2023:"` are invalid).
- Whitespace inside the token is invalid (`"2020 : 2023"` — the router only
  ever hands us whitespace-free tokens anyway, but the parser MUST NOT strip
  interior spaces).
- Each `unit` obeys the Phase 1 rules verbatim: 1970–2099 bounds,
  case-insensitive `q`, quarter table from §5.1(4). The right side of `f:` /
  `to:` MUST be a calendar unit — `f:3m`, `to:all`, `f:2101` are invalid.
- **Span resolution:** `A:B` → `{from: A.from, to: B.to}`. Validity rule:
  `A.from <= B.to` as a plain ISO-string comparison. This makes
  `2023:2020` and `2023q2:2023q1` invalid, while `2023:2023` (≡ `2023`) and
  `2023:2023q1` (Jan 1 – Mar 31) are valid. NOTE this is deliberately more
  general than the fund, which only allows year:year or quarter:quarter
  (`dateUtils.js:301-333`) — we also accept mixed `2023:2024q2`; it falls out
  of the same code path for free.
- **Labels** (used by `formatRange` and chart messages): span →
  `"<A.label> to <B.label>"` (e.g. `"2027 to 2028"`, `"2023 Q1 to 2024 Q2"`);
  open-from → `"from <unit.label>"`; open-to → `"to <unit.label>"`. Do not
  special-case `A === B` — `"2023 to 2023"` is acceptable output.

### 13.2 Nullable bounds — the one semantic change

The calendar `RangeSpec` arms become **nullable**:

```
{ kind: "calendar", from: string|null, to: string|null, label: string }
```

`from === null` means "unbounded past" (window starts at the data's first
entry / day 0). `to === null` means "unbounded future" (window extends to the
data's last entry / last offset). Phase 1 tokens continue to produce both
bounds non-null, so every existing Phase 1 test keeps passing byte-identically.

Exactly **two functions** in the entire codebase dereference `spec.from` /
`spec.to` (verified by grep on 2026-07-11) and therefore need null guards:

1. `calendarRangeToDayOffsets` — `js/utils/timeRange.js:151,153`
2. `calendarSliceBounds` — `js/commands/reviews.js:30,32`

Everything else consumes only `spec.kind`, `spec.label`, or the derived
`offsets.start/end` — meaning **`js/commands/due.js`, `retention.js`, and
`handler.js` need ZERO source changes in Phase 2** (they get the feature
through the two functions above). Tests for them are still required (§16).

## 14. Detailed design

### 14.1 `js/utils/timeRange.js` — restructure `parseCalendarRange`

Extract the current single-token body (`timeRange.js:99-121`) into a private
`parseCalendarUnit(token)` that returns `{from, to, label}` **without** the
`kind` field, then rebuild the exported `parseCalendarRange` on top of it.
Reference implementation (replaces `timeRange.js:94-121`; keep `CALENDAR_RE`,
`QUARTER_BOUNDS`, `MIN_YEAR`, `MAX_YEAR` as they are):

```js
/**
 * Parse one calendar unit ("2025", "2023q2") -> {from, to, label},
 * or undefined. Both bounds are always non-null for a unit.
 */
function parseCalendarUnit(token) {
  const match = token.match(CALENDAR_RE);
  if (!match) return undefined;
  const year = parseInt(match[1], 10);
  if (year < MIN_YEAR || year > MAX_YEAR) return undefined;
  if (match[2]) {
    const quarter = parseInt(match[2], 10);
    const [start, end] = QUARTER_BOUNDS[quarter];
    return {
      from: `${year}-${start}`,
      to: `${year}-${end}`,
      label: `${year} Q${quarter}`,
    };
  }
  return {
    from: `${year}-01-01`,
    to: `${year}-12-31`,
    label: `${year}`,
  };
}

/**
 * Parse a calendar token into a calendar RangeSpec.
 * Single units: "2025", "2023q2".
 * Spans:        "2020:2023", "2023q1:2024q2", "2023:2024q2".
 * Open-ended:   "f:2026" / "from:2026" (from unit start, no upper bound),
 *               "to:2028" (up to unit end, no lower bound).
 * @param {string} rangeKey
 * @returns {RangeSpec|undefined} calendar spec, or undefined if not calendar
 */
export function parseCalendarRange(rangeKey) {
  if (!rangeKey || typeof rangeKey !== "string") return undefined;
  const key = rangeKey.trim().toLowerCase();
  if (key.includes(":")) {
    const parts = key.split(":");
    if (parts.length !== 2 || !parts[0] || !parts[1]) return undefined;
    const [head, tail] = parts;
    if (head === "f" || head === "from") {
      const unit = parseCalendarUnit(tail);
      if (!unit) return undefined;
      return {
        kind: "calendar",
        from: unit.from,
        to: null,
        label: `from ${unit.label}`,
      };
    }
    if (head === "to") {
      const unit = parseCalendarUnit(tail);
      if (!unit) return undefined;
      return {
        kind: "calendar",
        from: null,
        to: unit.to,
        label: `to ${unit.label}`,
      };
    }
    const left = parseCalendarUnit(head);
    const right = parseCalendarUnit(tail);
    if (!left || !right) return undefined;
    // ISO strings compare lexicographically; reject inverted spans.
    if (left.from > right.to) return undefined;
    return {
      kind: "calendar",
      from: left.from,
      to: right.to,
      label: `${left.label} to ${right.label}`,
    };
  }
  const unit = parseCalendarUnit(key);
  if (!unit) return undefined;
  return { kind: "calendar", from: unit.from, to: unit.to, label: unit.label };
}
```

Backward-compat trap: existing tests `deepStrictEqual` the output of
`parseCalendarRange("2025")` against exactly
`{kind, from, to, label}` — the wrapper above preserves that shape and key
set. Do not add fields.

Update the `@typedef` at `timeRange.js:79-82` to the nullable form (§13.2).

**`calendarRangeToDayOffsets`** (`timeRange.js:144-154`) — add null guards.
`end` may now legitimately be `Infinity` (callers filter with
`e.day <= offsets.end`, which is `Infinity`-safe):

```js
export function calendarRangeToDayOffsets(spec, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const toLocal = (iso) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  };
  const diff = (target) => Math.round((target - today) / 86400000);
  const end = spec.to === null ? Infinity : diff(toLocal(spec.to));
  if (end < 0) return null;
  const start = spec.from === null ? 0 : Math.max(0, diff(toLocal(spec.from)));
  return { start, end };
}
```

**`RANGE_HELP`** (`timeRange.js:15-16`) — new normative string. It MUST keep
the substrings `YYYY` and `YYYYqN` (pinned by
`tests/handler_calendar.test.cjs`, the "mentions calendar tokens" case):

```js
export const RANGE_HELP =
  "Valid ranges: 1m-12m, 1y-Ny, Nd, combos (1y4m), YYYY, YYYYqN (2023q2), spans (2020:2023, f:2026, to:2028), all";
```

The two hardcoded copies of the old string in
`tests/handler_calendar.test.cjs` assert via the imported constant, so they
survive; but `grep -rn "Valid ranges:" tests/` first and update any literal
that duplicates the exact Phase 1 wording.

### 14.2 `js/commands/reviews.js` — null-safe `calendarSliceBounds`

Replace the body (`reviews.js:29-35`):

```js
function calendarSliceBounds(entries, spec) {
  let start = 0;
  if (spec.from !== null) {
    while (start < entries.length && entries[start].date < spec.from) start++;
  }
  let end = start;
  if (spec.to === null) {
    end = entries.length;
  } else {
    while (end < entries.length && entries[end].date <= spec.to) end++;
  }
  return { start, end };
}
```

Semantics falling out for free (no further edits in this file):

- `f:2025` → `start` at first entry ≥ `2025-01-01`, `end = length`;
  `preSliceSum` covers everything before 2025 (cumulative charts stay
  correct).
- `to:2024` → `start = 0` (so `preSliceSum` is all zeros — nothing precedes
  an unbounded-past window), `end` after the last entry ≤ `2024-12-31`.
- `2024:2025` → both loops run, same as a Phase 1 token spanning two years.

### 14.3 `js/commands/due.js`, `retention.js`, `handler.js` — NO source changes

- `due.js` consumes only `calendarRangeToDayOffsets` output and
  `rangeSpec.kind`. With `to: null`, `offsets.end === Infinity` and the
  existing `e.day <= offsets.end` filter keeps every future entry; `minDay`/
  `maxDay`/label logic already derives from the filtered data. With
  `from: null`, `offsets.start === 0`. A `to:<past year>` window yields
  `null` offsets → the existing empty path. **Do not edit this file.**
- `retention.js` message comes from `formatRange` → `spec.label`. Done.
- `handler.js` routing is gated by `isValidRange` (§3.2) — colon tokens flow
  through identically (verified: they are plain tokens after the lowercase
  trim; nothing else in `handleCommand` interprets `:`). Only the help text
  changes: add one line to `showHelp` and `listCharts` next to the Phase 1
  calendar line: `2027:2028, f:2026, to:2028 (calendar spans)` — match the
  neighboring lines' `appendLine("...", "muted")` style. That is the ONLY
  `handler.js` edit.

## 15. Behavior matrix (Phase 2)

With today = `2026-07-11`, data as in §3.3:

| Input                        | Chart     | Result                                                                                      |
| ---------------------------- | --------- | ------------------------------------------------------------------------------------------- |
| `plot reviews 2024:2025`     | reviews   | entries `2024-01-01 … 2025-12-31`; message `… (2024 to 2025).`                              |
| `plot reviews 2023q4:2024q1` | reviews   | entries `2023-10-01 … 2024-03-31`; message `… (2023 Q4 to 2024 Q1).`                        |
| `retention f:2025`           | retention | entries from `2025-01-01` through the last entry; message `… (from 2025).`                  |
| `reviews to:2024`            | reviews   | entries up to `2024-12-31`; cumulative variant starts at zero (nothing precedes the window) |
| `plot due f:2027`            | due       | offsets `174 … end-of-data`, date-labeled x-axis (calendar mode)                            |
| `plot due to:2026`           | due       | offsets `0 … 173`                                                                           |
| `plot due to:2025`           | due       | empty (window entirely past) — same path as `plot due 2025`                                 |
| bare `f:2026` after `pr`     | reviews   | shortcut path re-renders reviews from 2026-01-01 on                                         |
| `plot reviews 2023:2020`     | —         | `Unknown range: 2023:2020` + `RANGE_HELP`                                                   |
| `plot reviews f:3m`          | —         | invalid (unit after `f:` must be calendar)                                                  |
| `plot reviews 2023::2024`    | —         | invalid (exactly one colon)                                                                 |

`activeTimeRange` persistence, cumulative `preSliceSum` seeding, and the
empty-window messages all behave exactly as specified for Phase 1 (§4.2) —
spans reuse those paths, they do not add new ones.

## 16. Test plan (Phase 2)

Same conventions as §7 (CommonJS + `node:test`, dynamic `await import()`, no
`Date.parse`, construct `now` as `new Date(2026, 6, 11)`).

### 16.1 `tests/timeRange_span.test.cjs` (new file, pure logic)

| Case                                                                                                                                                                                | Expectation                                                                   |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `parseRangeSpec("2027:2028")`                                                                                                                                                       | `{kind:"calendar", from:"2027-01-01", to:"2028-12-31", label:"2027 to 2028"}` |
| `parseRangeSpec("2023q1:2024q2")`                                                                                                                                                   | `from:"2023-01-01", to:"2024-06-30", label:"2023 Q1 to 2024 Q2"`              |
| mixed `"2023:2024q2"` and `"2023q4:2024"`                                                                                                                                           | `2023-01-01…2024-06-30` and `2023-10-01…2024-12-31`                           |
| `"2023:2023"`                                                                                                                                                                       | valid; `from/to` equal the `2023` unit; label `"2023 to 2023"`                |
| `"2023:2023q1"`                                                                                                                                                                     | valid; `2023-01-01…2023-03-31`                                                |
| `parseRangeSpec("f:2026")`, `"from:2026"`                                                                                                                                           | `{from:"2026-01-01", to:null, label:"from 2026"}` (both aliases)              |
| `parseRangeSpec("f:2023q2")`                                                                                                                                                        | `{from:"2023-04-01", to:null, label:"from 2023 Q2"}`                          |
| `parseRangeSpec("to:2028")`                                                                                                                                                         | `{from:null, to:"2028-12-31", label:"to 2028"}`                               |
| `parseRangeSpec("to:2023q2")`                                                                                                                                                       | `{from:null, to:"2023-06-30", label:"to 2023 Q2"}`                            |
| `" F:2026 "`, `"TO:2028"` (trim + case)                                                                                                                                             | valid, same as lowercase                                                      |
| invalid: `"2023:2020"`, `"2023q2:2023q1"`, `"2023::2024"`, `":2023"`, `"2023:"`, `"f:"`, `"to:"`, `"f:3m"`, `"to:all"`, `"f:2101"`, `"t:2026"`, `"2020 : 2023"`, `"2020:2023:2025"` | `parseRangeSpec` → `undefined`; `isValidRange` → `false` for each             |
| `formatRange("2027:2028")`, `("f:2026")`, `("to:2028")`                                                                                                                             | `"2027 to 2028"`, `"from 2026"`, `"to 2028"`                                  |
| Phase 1 regression: `parseCalendarRange("2025")` deep-equals its Phase 1 shape; `parseRange("f:2026")` → `undefined`                                                                | unchanged                                                                     |
| `calendarRangeToDayOffsets(parse("f:2027"), now)`                                                                                                                                   | `{start:174, end:Infinity}`                                                   |
| `calendarRangeToDayOffsets(parse("f:2025"), now)` (from in past)                                                                                                                    | `{start:0, end:Infinity}` (clamped, NOT null — future is unbounded)           |
| `calendarRangeToDayOffsets(parse("to:2027"), now)`                                                                                                                                  | `{start:0, end:538}`                                                          |
| `calendarRangeToDayOffsets(parse("to:2025"), now)`                                                                                                                                  | `null` (entirely past)                                                        |

### 16.2 Extend `tests/reviews_calendar.test.cjs` (same 6-entry gap mock)

- `getReviewStatsData("f:2025")` → the four entries dated ≥ `2025-01-01`
  (including `2026-01-01`); `preSliceSum` = sum of the two 2024 entries.
- `getReviewStatsData("to:2024")` → the two 2024 entries; `preSliceSum` all
  zeros.
- `getReviewStatsData("2024:2025")` → the first five entries; `preSliceSum`
  all zeros.
- By-deck: `getReviewStatsData("f:2025", true)` → `dates` are the four ≥
  2025 dates; DeckA's pre-window count lands in `preSliceSumsByDeck`.

### 16.3 Extend `tests/due_calendar.test.cjs` (same runtime-relative mock)

- `getFutureDueData("f:<next year>")` → every entry with
  `day >= nextYearStartOffset`, through the end of the mock data (no upper
  truncation).
- `getFutureDueData("to:<current year>")` → offsets `0…currentYearEndOffset`.
- `getFutureDueData("to:<last year>")` → `[]`; by-deck → `{}`.
- Render `f:<next year>`: first label is next Jan 1 (`YYYY-MM-DD`), label
  count = number of days from next Jan 1 through the last mock entry.

### 16.4 Extend `tests/handler_calendar.test.cjs`

- `handleCommand("plot reviews 2024:2025", log)` → `command:"plot-reviews"`,
  `range:"2024:2025"`, no `Unknown range` line.
- Bare `handleCommand("f:2026", log)` after a reviews command → shortcut path,
  `range:"f:2026"`.
- `handleCommand("plot due to:2028", log)` → `plot-due`, `range:"to:2028"`.
- `handleCommand("plot reviews 2023:2020", log)` → error result with
  `Unknown range: 2023:2020` and `RANGE_HELP`.

## 17. Implementation order (Phase 2)

Red before green at every step; run the named test file after each.

1. Write `tests/timeRange_span.test.cjs` (§16.1) → confirm red →
   restructure `timeRange.js` (§14.1: `parseCalendarUnit`, colon handling,
   nullable typedef, `calendarRangeToDayOffsets` guards, `RANGE_HELP`) →
   green. Then run `tests/timeRange_calendar.test.cjs` AND
   `tests/timeRange.test.cjs` — both MUST pass unmodified.
2. Extend `tests/reviews_calendar.test.cjs` (§16.2) → red →
   `calendarSliceBounds` null guards (§14.2) → green.
3. Extend `tests/due_calendar.test.cjs` (§16.3) → these SHOULD pass with no
   `due.js` edits (that is the point of §14.3). If any fails, the bug is in
   step 1, not in `due.js` — do not edit `due.js`.
4. Extend `tests/handler_calendar.test.cjs` (§16.4) → routing cases should
   already pass; add the two help-text lines to `showHelp`/`listCharts`
   (§14.3) — the only `handler.js` edit.
5. Gate per §7.5, including its **known pre-existing failures** note. Also
   run `npx prettier --write docs/terminal-calendar-ranges.md` if you touch
   this doc, and tick the §18 boxes.

## 18. Acceptance criteria (Phase 2) — status (verified 2026-07-11)

- [x] Every §15 row holds via automated tests (§16); not yet manually
      spot-checked in the live terminal UI.
- [x] All Phase 1 test files (`timeRange_calendar`, `reviews_calendar`,
      `due_calendar`, `handler_calendar`, `retention_calendar`) pass with
      their Phase 1 assertions intact — Phase 2 only _added_ cases to
      `reviews_calendar`, `due_calendar`, and `handler_calendar`; no existing
      assertion was edited or removed.
- [x] `git diff --stat` shows source changes ONLY in `js/utils/timeRange.js`
      (74 lines: `parseCalendarUnit` extraction, colon handling, nullable
      typedef, `calendarRangeToDayOffsets` guards, `RANGE_HELP`),
      `js/commands/reviews.js` (10 lines: null guards in
      `calendarSliceBounds`), and 2 added lines in `js/commands/handler.js`
      (`showHelp`/`listCharts`). `js/commands/due.js` and
      `js/commands/retention.js` have **zero diff** — confirmed by
      `git diff --stat js/commands/due.js` returning empty, and by the §16.3
      due tests (10/10 green) requiring no source edit.
- [x] `RANGE_HELP` contains `YYYY`, `YYYYqN`, and now also `f:2026`/`to:2028`
      (pinned in `tests/timeRange_span.test.cjs` and
      `tests/handler_calendar.test.cjs`).
- [x] Node-runner portion of `make check-node`: 69/69 root suites green
      (100% line coverage on `timeRange.js`; `due.js`/`retention.js`
      coverage unchanged from Phase 1 since untouched). `fmt-check`, `lint`,
      `quality-py` all clean. (Same pre-existing `review_heatmap` jest/Node
      version failure as Phase 1 — see §7.5 known failure 1; not
      Phase-2-related.)

Phase 2 tests shipped: `tests/timeRange_span.test.cjs` (16 new),
`tests/reviews_calendar.test.cjs` (+5, 9 total),
`tests/due_calendar.test.cjs` (+4, 10 total),
`tests/handler_calendar.test.cjs` (+5, 12 total).

## 19. Phase 2 DO-NOTs

1. **Do not** edit `js/commands/due.js` or `js/commands/retention.js` — if a
   span test fails there, fix `timeRange.js` (§17 step 3).
2. **Do not** accept duration or `all` tokens after `f:`/`to:` — calendar
   units only.
3. **Do not** implement multi-word forms (`from 2023`, `2023 to 2024`) or a
   `t:` alias — `f:`, `from:`, `to:` exactly, matching the fund
   (`dateUtils.js:276,288`).
4. **Do not** special-case `A === B` spans or collapse labels.
5. **Do not** return `Infinity`/`null` mixtures beyond the spec: open-from →
   `to: null`; open-to → `from: null`; never both null (there is no token
   for it — `all` already covers that).
6. All Part I DO-NOTs (§6) still apply, especially: no `new Date("YYYY-MM-DD")`,
   no index arithmetic on review dates, no trie changes, run from repo root.

---

# Amendments (post-Phase-2)

## A1 (2026-07-11): due-chart tooltip shows relative offsets in calendar mode

User feedback after shipping: hovering a calendar-filtered due chart showed
the date (the axis label) in the tooltip title; it should show the same
relative-offset form (`Today` / `Tomorrow` / `+Nd`) that duration filters
show. Implemented TDD in `js/commands/due.js`: `renderFutureDueChart` builds
a `tooltipTitles` array parallel to the date labels in calendar mode and the
tooltip title callback prefers it (falling back to the axis label in
duration mode, which is unchanged). Axis labels remain real dates — only the
hover tooltip switches. Pinned by four cases in `tests/due_calendar.test.cjs`
("tooltip title: …"). This supersedes the §5.4 note that labels alone carry
the calendar context.
