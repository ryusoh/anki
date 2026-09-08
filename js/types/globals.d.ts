interface Window {
  __SW_FORCE_SW_HOSTNAME__?: string;
  gsap?: unknown;
  cursorInstances?: {
    cursor?: unknown;
  };
}

declare module "*/quantum_shader.js" {}
declare module "*/videoFallback.js" {
  export function initVideoFallback(): void;
}
