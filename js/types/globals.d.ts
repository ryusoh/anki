declare global {
  interface Window {
    __SW_FORCE_SW_HOSTNAME__?: string;
    gsap?: unknown;
    cursorInstances?: {
      cursor?: unknown;
    };
  }
}
declare module "/js/ambient/quantum_shader.js" {}
declare module "/js/ui/videoFallback.js" {
  export function initVideoFallback(): void;
}

export {};
