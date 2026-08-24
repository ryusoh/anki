export interface CursorConfig {
  hoverTargets?: string;
  followEase?: number;
  fadeEase?: number;
  hoverScale?: number;
}

export interface CursorInitOptions {
  cursor?: CursorConfig;
}

export interface CursorInstance {
  cursor?: unknown;
}

export function initCursor(options?: CursorInitOptions): CursorInstance;
