
interface GsapTweenVars {
  x?: number;
  y?: number;
  duration?: number;
  ease?: string;
  overwrite?: boolean;
}

interface GsapQuickTo {
  (value: number): void;
}

interface Gsap {
  quickTo(target: Element, property: string, vars?: GsapTweenVars): GsapQuickTo;
  to(target: Element, vars: GsapTweenVars): void;
}

type IdleRequestCallback = (deadline: { didTimeout: boolean, timeRemaining: () => number }) => void;
interface IdleRequestOptions { timeout: number; }

interface Window {
  __SW_FORCE_SW_HOSTNAME__?: string;
  gsap?: Gsap;
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
