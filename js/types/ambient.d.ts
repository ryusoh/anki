export interface AmbientConfig {
  enabled?: boolean;
  minWidth?: number;
  maxParticles?: number;
  densityDivisor?: number;
  radius?: { min: number; max: number };
  alpha?: { min: number; max: number };
  speed?: number;
  zIndex?: number;
  blend?: string;
  respectReducedMotion?: boolean;
}

declare global {
  interface Window {
    AMBIENT_CONFIG?: AmbientConfig;
  }
}

export {};
