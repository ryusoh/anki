interface SketchContext extends CanvasRenderingContext2D {
  width: number;
  height: number;
  save(): void;
  restore(): void;
  globalCompositeOperation: string;
  globalAlpha: number;
  fillStyle: string;
  fillRect(x: number, y: number, w: number, h: number): void;
  beginPath(): void;
  arc(x: number, y: number, radius: number, startAngle: number, endAngle: number, counterclockwise?: boolean): void;
  fill(): void;
}

interface SketchInstance {
  canvas: HTMLCanvasElement;
  width: number;
  height: number;
  setup(): void;
  resize(): void;
  update(): void;
  draw(this: SketchContext): void;
}

interface Window {
  Sketch?: {
    create(options: any): SketchInstance;
  };
  AMBIENT_CONFIG?: any;
}
