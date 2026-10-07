interface GsapTweenVars {
  x?: number;
  y?: number;
  duration?: number;
  ease?: string;
  overwrite?: boolean;
  opacity?: number;
  scale?: number;
  height?: number | string;
  clearProps?: string;
}

interface GsapQuickTo {
  (value: number): void;
}

type IdleRequestCallback = (deadline: {
  didTimeout: boolean;
  timeRemaining: () => number;
}) => void;
interface IdleRequestOptions {
  timeout: number;
}

interface Window {
  __SW_FORCE_SW_HOSTNAME__?: string;
  gsap?: Gsap;
  Chart?: typeof Chart;
  reviewStatsData?: {
    reviews: any[];
  };
  cursorInstances?: {
    cursor?: unknown;
  };
  requestIdleCallback?: (
    callback: IdleRequestCallback,
    options?: IdleRequestOptions,
  ) => number;
}

interface Navigator {
  connection?: { effectiveType?: string; saveData?: boolean };
  mozConnection?: { effectiveType?: string; saveData?: boolean };
  webkitConnection?: { effectiveType?: string; saveData?: boolean };
}

declare module "*/quantum_shader.js" {}
declare module "*/videoFallback.js" {
  export function initVideoFallback(): void;
}

interface GsapTimeline {
  to(
    target: Element | HTMLElement | null,
    vars: GsapTweenVars,
    position?: number | string,
  ): this;
}

interface GsapTimelineVars {
  onComplete?: () => void;
}

interface Gsap {
  quickTo(target: Element, property: string, vars?: GsapTweenVars): GsapQuickTo;
  to(target: Element | HTMLElement | null, vars: GsapTweenVars): void;
  timeline(vars?: GsapTimelineVars): GsapTimeline;
  set(target: Element | HTMLElement | null, vars: any): void;
}

declare var gsap: Gsap;
