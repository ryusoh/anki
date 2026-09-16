interface CDNLoaderType {
  preconnect: (origins: string[]) => void;
  loadScriptSequential: (urls: string[], attrs?: { defer?: boolean; async?: boolean }) => Promise<void>;
  loadCssWithFallback: (urls: string[]) => Promise<void>;
}

interface Window {
  CDNLoader?: CDNLoaderType;
}
