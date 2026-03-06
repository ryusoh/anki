/**
 * Trie (Prefix Tree) for Command Autocomplete
 * Provides fast prefix-based autocomplete and command validation
 */

export class TrieNode {
  constructor() {
    this.children = {};
    this.isEndOfCommand = false;
    this.command = null; // Full command stored at end node
  }
}

export class CommandTrie {
  constructor() {
    this.root = new TrieNode();
    this.commands = new Set(); // Track all registered commands
  }

  /**
   * Insert a command into the trie (character-by-character for autocomplete)
   * @param {string} command - Command to insert (e.g., "plot due", "reviews")
   */
  insert(command) {
    const normalized = command.toLowerCase().trim();
    if (!normalized) return;

    let node = this.root;

    // Insert character by character for proper prefix matching
    for (const char of normalized) {
      if (!node.children[char]) {
        node.children[char] = new TrieNode();
      }
      node = node.children[char];
    }

    node.isEndOfCommand = true;
    node.command = normalized;
    this.commands.add(normalized);
  }

  /**
   * Insert multiple commands at once
   * @param {string[]} commands - Array of commands
   */
  insertAll(commands) {
    commands.forEach((cmd) => this.insert(cmd));
  }

  /**
   * Search for an exact command match
   * @param {string} command - Command to search
   * @returns {boolean} - True if command exists
   */
  search(command) {
    const normalized = command.toLowerCase().trim();
    return this.commands.has(normalized);
  }

  /**
   * Check if any command starts with the given prefix
   * @param {string} prefix - Prefix to check
   * @returns {boolean} - True if prefix matches any command
   */
  startsWith(prefix) {
    const normalized = prefix.toLowerCase().trim();
    if (!normalized) return true;

    let node = this.root;
    for (const char of normalized) {
      if (!node.children[char]) {
        return false;
      }
      node = node.children[char];
    }
    return true;
  }

  /**
   * Get autocomplete suggestions for a prefix
   * @param {string} prefix - Current input prefix
   * @param {number} limit - Max suggestions to return
   * @returns {string[]} - Array of suggested commands
   */
  autocomplete(prefix, limit = 10) {
    const normalized = prefix.toLowerCase().trim();
    if (!normalized) {
      return Array.from(this.commands).slice(0, limit);
    }

    let node = this.root;

    // Navigate to prefix node
    for (const char of normalized) {
      if (!node.children[char]) {
        return [];
      }
      node = node.children[char];
    }

    // Collect all commands from this node
    const suggestions = [];
    this._collectCommands(node, normalized, suggestions, limit);
    return suggestions;
  }

  /**
   * Collect all commands from a node (DFS)
   * @private
   */
  _collectCommands(node, prefix, results, limit) {
    if (results.length >= limit) return;

    if (node.isEndOfCommand) {
      results.push(node.command);
    }

    for (const [char, childNode] of Object.entries(node.children)) {
      this._collectCommands(childNode, prefix + char, results, limit);
    }
  }

  /**
   * Validate a command - check if it exists in trie
   * @param {string} command - Command to validate
   * @returns {{valid: boolean, suggestions: string[]}} - Validation result
   */
  validate(command) {
    const normalized = command.toLowerCase().trim();

    // Exact match
    if (this.search(normalized)) {
      return { valid: true, suggestions: [] };
    }

    // Check if it's a partial match (prefix of valid command)
    if (this.startsWith(normalized)) {
      const suggestions = this.autocomplete(normalized, 5);
      return {
        valid: false,
        suggestions,
        isPartial: true,
      };
    }

    // No match at all - command not in trie
    return {
      valid: false,
      suggestions: [],
      isPartial: false,
    };
  }

  /**
   * Get all registered commands
   * @returns {string[]} - Array of all commands
   */
  getAllCommands() {
    return Array.from(this.commands);
  }

  /**
   * Get command count
   * @returns {number} - Number of registered commands
   */
  size() {
    return this.commands.size;
  }

  /**
   * Clear all commands from trie
   */
  clear() {
    this.root = new TrieNode();
    this.commands.clear();
  }
}

/**
 * Create and populate the default command trie
 * @returns {CommandTrie} - Populated trie
 */
export function createCommandTrie() {
  const trie = new CommandTrie();

  // Base commands with abbreviations
  trie.insertAll([
    "help",
    "h", // help
    "?", // help alternative
    "charts",
    "list", // list charts
    "clear",
    "cls",
    "c", // clear
    "plot",
    "p", // plot umbrella
    "plot due",
    "pd", // plot due abbreviation
    "plot reviews",
    "pr", // plot reviews abbreviation
    "plot reviews time",
    "prt", // plot reviews time abbreviation
    "plot retention", // retention rate chart
    "due",
    "d", // due shortcut
    "future",
    "f", // future shortcut
    "reviews",
    "r", // reviews shortcut
    "reviews time",
    "rt", // reviews time shortcut
    "time",
    "t", // time shortcut
    "retention", // retention rate shortcut
    "show",
    "s", // show command
    "show due",
    "sd", // show due
    "show reviews",
    "sr", // show reviews
    "zoom", // terminal zoom
    "z", // zoom shortcut
  ]);

  // Range shortcuts (apply to current chart)
  // All 12 months + common year ranges + all
  const ranges = [];
  for (let m = 1; m <= 12; m++) ranges.push(`${m}m`);
  for (let y = 1; y <= 20; y++) ranges.push(`${y}y`);
  ranges.push("all");
  trie.insertAll(ranges);

  // Full plot/show commands with ranges
  ranges.forEach((range) => {
    trie.insert(`plot due ${range}`);
    trie.insert(`plot reviews ${range}`);
    trie.insert(`plot reviews time ${range}`);
    trie.insert(`plot retention ${range}`);
    trie.insert(`show due ${range}`);
    trie.insert(`show reviews ${range}`);
  });

  return trie;
}
