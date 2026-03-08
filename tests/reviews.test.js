const assert = require("assert");

// ============================================================================
// PURE FUNCTIONS TO TDD
// ============================================================================

function groupAndSortDecks(byDeckData, showTime) {
  const groups = {};

  // Group by top-level deck name
  for (const [deckName, entries] of Object.entries(byDeckData)) {
    if (deckName === "Unknown") continue;

    const total = entries.reduce(
      (sum, e) =>
        sum +
        (showTime
          ? e.time || 0
          : (e.count || 0) + (e.mature || 0) + (e.young || 0)),
      0,
    );
    if (total === 0) continue;

    const topLevelName = deckName.split("::")[0];
    if (!groups[topLevelName]) {
      groups[topLevelName] = {
        total: 0,
        subDecks: [],
      };
    }

    groups[topLevelName].total += total;
    groups[topLevelName].subDecks.push({
      deckName,
      total,
    });
  }

  // Sort groups by descending total
  const sortedGroups = Object.keys(groups).sort(
    (a, b) => groups[b].total - groups[a].total,
  );

  const result = [];
  let groupIndex = 0;

  for (const topLevel of sortedGroups) {
    const group = groups[topLevel];
    // Sort sub-decks within group by descending total
    group.subDecks.sort((a, b) => b.total - a.total);

    let subIndex = 0;
    for (const subDeck of group.subDecks) {
      result.push({
        deckName: subDeck.deckName,
        groupIndex,
        subIndex,
        totalInGroup: group.subDecks.length,
      });
      subIndex++;
    }
    groupIndex++;
  }

  return result;
}

// Hardcoded base colors mimicking DECK_COLORS
const BASE_COLORS = [
  "hsla(320, 80%, 60%, 0.85)", // index 0
  "hsla(200, 80%, 50%, 0.85)", // index 1
  "hsla(40, 90%, 55%, 0.85)", // index 2
];

function getGroupedDeckColor(groupIndex, subIndex, totalInGroup) {
  const baseColor = BASE_COLORS[groupIndex % BASE_COLORS.length];

  if (totalInGroup <= 1 || subIndex === 0) return baseColor;

  // Expected format: "hsla(H, S%, L%, A)"
  const match = baseColor.match(
    /hsla\((\d+),\s*(\d+)%,\s*([\d.]+)%,\s*([\d.]+)\)/,
  );
  if (!match) return baseColor;

  let h = parseInt(match[1], 10);
  const s = parseInt(match[2], 10);
  let l = parseFloat(match[3]);
  const a = match[4];

  const hueOffsets = [0, 9, -9, 16, -16]; // Length 5
  const lightOffsets = [0, 18, -18, 10, -10, 26, -26]; // Length 7
  const satOffsets = [0, -25, -12]; // Length 3

  h = (h + hueOffsets[subIndex % hueOffsets.length] + 360) % 360;
  l = Math.max(
    25,
    Math.min(85, l + lightOffsets[subIndex % lightOffsets.length]),
  );

  const newS = Math.max(
    40,
    Math.min(100, s + satOffsets[subIndex % satOffsets.length]),
  );

  return `hsla(${Math.round(h)}, ${Math.round(newS)}%, ${Math.round(l)}%, ${a})`;
}

// ============================================================================
// TESTS
// ============================================================================

let passed = 0;
let failed = 0;

console.log("🧪 Reviews Deck Grouping and Coloring Tests\n");
console.log("=".repeat(60));

// Test 1: groupAndSortDecks
console.log("\n📋 Test 1: groupAndSortDecks correctly groups and sorts");
try {
  const byDeckData = {
    // Group "Language" - Total time: 100
    "Language::Japanese": [{ time: 60, count: 5 }],
    "Language::English": [{ time: 40, count: 5 }],
    // Group "Math" - Total time: 150
    "Math::Calculus": [{ time: 150, count: 5 }],
    // Group "History" (No subdecks) - Total time: 50
    History: [{ time: 50, count: 5 }],
  };

  const showTime = true;
  const result = groupAndSortDecks(byDeckData, showTime);

  // Expected order:
  // Math (150) -> Math::Calculus
  // Language (100) -> Language::Japanese (60), Language::English (40)
  // History (50) -> History

  assert.strictEqual(result.length, 4, "Should have 4 decks grouped");

  assert.strictEqual(result[0].deckName, "Math::Calculus");
  assert.strictEqual(result[0].groupIndex, 0);
  assert.strictEqual(result[0].subIndex, 0);

  assert.strictEqual(result[1].deckName, "Language::Japanese");
  assert.strictEqual(result[1].groupIndex, 1);
  assert.strictEqual(result[1].subIndex, 0);

  assert.strictEqual(result[2].deckName, "Language::English");
  assert.strictEqual(result[2].groupIndex, 1);
  assert.strictEqual(result[2].subIndex, 1);

  assert.strictEqual(result[3].deckName, "History");
  assert.strictEqual(result[3].groupIndex, 2);
  assert.strictEqual(result[3].subIndex, 0);

  console.log("   ✓ Decks grouped and sorted correctly");
  passed++;
} catch (e) {
  console.log(`   ✗ groupAndSortDecks: ${e.message}`);
  failed++;
}

// Test 2: groupAndSortDecks ignores Unknown deck
console.log("\n📋 Test 2: groupAndSortDecks ignores 'Unknown' deck");
try {
  const byDeckData = {
    Science: [{ time: 100, count: 5 }],
    Unknown: [{ time: 500, count: 5 }],
  };

  const result = groupAndSortDecks(byDeckData, true);
  assert.strictEqual(result.length, 1, "Should filter out Unknown deck");
  assert.strictEqual(result[0].deckName, "Science");

  console.log("   ✓ Unknown deck ignored");
  passed++;
} catch (e) {
  console.log(`   ✗ groupAndSortDecks (Unknown): ${e.message}`);
  failed++;
}

// Test 3: getGroupedDeckColor
console.log("\n📋 Test 3: getGroupedDeckColor creates distinct shades");
try {
  // Mock DECK_COLORS
  // Assume index 0 is hsla(320, 80%, 60%, 0.85)
  // We want to make sure subIndex 0 matches base, and subIndex 1/2 vary but share hue

  const color0_0 = getGroupedDeckColor(0, 0, 3);
  const color0_1 = getGroupedDeckColor(0, 1, 3);
  const color0_2 = getGroupedDeckColor(0, 2, 3);

  assert.notStrictEqual(
    color0_0,
    color0_1,
    "Colors in same group should differ",
  );
  assert.notStrictEqual(
    color0_1,
    color0_2,
    "Colors in same group should differ",
  );

  // They should all start with 'hsla('
  assert.ok(color0_0.startsWith("hsla("));
  assert.ok(color0_1.startsWith("hsla("));

  console.log("   ✓ Grouped colors generated correctly");
  passed++;
} catch (e) {
  console.log(`   ✗ getGroupedDeckColor: ${e.message}`);
  failed++;
}

// Test 4: groupAndSortDecks with mature/young structure
console.log(
  "\n📋 Test 4: groupAndSortDecks with futureDue structure (mature/young)",
);
try {
  const dueDeckData = {
    // Group "Science" - Total mature: 20, young: 10 => 30
    "Science::Physics": [{ mature: 20, young: 10 }],
    // Group "Art" - Total mature: 0, young: 5 => 5
    "Art::Drawing": [{ mature: 0, young: 5 }],
  };

  const showTime = false;
  const result = groupAndSortDecks(dueDeckData, showTime);

  assert.strictEqual(result.length, 2, "Should have 2 decks grouped");
  assert.strictEqual(
    result[0].deckName,
    "Science::Physics",
    "Science should be first due to larger sum (30)",
  );
  assert.strictEqual(
    result[1].deckName,
    "Art::Drawing",
    "Art should be second (5)",
  );

  console.log(
    "   ✓ Decks grouped and sorted correctly using mature/young counts",
  );
  passed++;
} catch (e) {
  console.log(`   ✗ groupAndSortDecks with mature/young: ${e.message}`);
  failed++;
}

console.log("\n" + "=".repeat(60));
console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);

if (failed > 0) {
  console.log("❌ TESTS FAILED");
  process.exit(1);
} else {
  console.log("✅ ALL TESTS PASSED");
  process.exit(0);
}
