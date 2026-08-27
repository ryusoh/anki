declare global {
  interface Window {
    __SW_FORCE_SW_HOSTNAME__?: string;
    gsap?: unknown;
    cursorInstances?: {
      cursor?: unknown;
    };
  }
}
export {};
