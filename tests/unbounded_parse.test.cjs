const assert = require('assert');

// 1. Test ambient URLSearchParams
let globalURLSearchParamsCalled = false;
global.window = {
  URLSearchParams: class {
    constructor(query) {
      globalURLSearchParamsCalled = true;
    }
    get() { return null; }
  },
  location: {
    search: '?a=' + 'x'.repeat(2500)
  },
  AMBIENT_CONFIG: {}
};

try {
  const fs = require('fs');
  const path = require('path');
  const ambientPath = path.join(__dirname, '../js/ambient/ambient.js');
  const code = fs.readFileSync(ambientPath, 'utf8');
  eval(code);
} catch (e) {
  // Ignore
}
assert.strictEqual(globalURLSearchParamsCalled, false, "URLSearchParams should not be called with overly long search string");

// 2. Test nav_prefetch window.URL
let globalURLCalled = false;
global.window.URL = class {
  constructor(a, b) {
    globalURLCalled = true;
  }
};
global.window.location.origin = 'http://localhost';
global.window.location.href = 'http://localhost/' + 'x'.repeat(2500);
global.document = {
  querySelector: () => ({ getAttribute: () => 'http://localhost/' }),
  querySelectorAll: () => []
};

try {
  const fs = require('fs');
  const path = require('path');
  const prefetchPath = path.join(__dirname, '../js/ui/nav_prefetch.js');
  const code = fs.readFileSync(prefetchPath, 'utf8');
  eval(code);
} catch (e) {
  // Ignore
}
assert.strictEqual(globalURLCalled, false, "window.URL should not be called with overly long window.location.href");

// 3. Test sw.js new URL(req.url)
let swURLCalled = false;
global.URL = class {
  constructor(a, b) {
    swURLCalled = true;
    this.origin = 'http://localhost';
    this.pathname = '/';
  }
};
global.self = {
  addEventListener: () => {},
  location: { origin: 'http://localhost' },
};
global.caches = {};

try {
  const fs = require('fs');
  const path = require('path');
  const swPath = path.join(__dirname, '../sw.js');
  const code = fs.readFileSync(swPath, 'utf8');
  eval(code);

  const fetchEvent = {
    request: {
      method: 'GET',
      url: 'http://localhost/' + 'x'.repeat(2500),
      headers: { has: () => false },
      destination: 'image'
    },
    respondWith: () => {}
  };

  let fetchHandler;
  global.self.addEventListener = (event, handler) => {
    if (event === 'fetch') {
      fetchHandler = handler;
    }
  };

  eval(code);
  if (fetchHandler) {
     fetchHandler(fetchEvent);
  }
} catch (e) {
  // Ignore
}
assert.strictEqual(swURLCalled, false, "URL should not be called with overly long req.url");

console.log("✅ Unbounded parse tests passed");
