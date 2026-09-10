type IdleRequestCallback = (deadline: { didTimeout: boolean, timeRemaining: () => number }) => void;
interface IdleRequestOptions { timeout: number; }

interface Window {
  __SW_FORCE_SW_HOSTNAME__?: string;
  gsap?: unknown;
  cursorInstances?: {
    cursor?: unknown;
  };
  requestIdleCallback?: (callback: IdleRequestCallback, options?: IdleRequestOptions) => number;
}

interface Navigator {
  connection?: { effectiveType?: string, saveData?: boolean };
  mozConnection?: { effectiveType?: string, saveData?: boolean };
  webkitConnection?: { effectiveType?: string, saveData?: boolean };
}

declare module "*/quantum_shader.js" {}
declare module "*/videoFallback.js" {
  export function initVideoFallback(): void;
}
