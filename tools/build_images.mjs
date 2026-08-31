// Builds AVIF/WebP tiers for the GitHub Pages site's CSS background images.
// Adapted from ryusoh.github.io scripts/build-images.mjs: same sharp encoder
// settings, but no exiftool pass (these backgrounds are digital renders with
// no GPS/serial EXIF) and no HTML rewriting (the load sites here are CSS
// `image-set()` declarations, maintained by hand alongside this manifest).
// Output files sit next to their sources and must be committed — Pages
// deploys the repo as-is with no build step (see .github/workflows/pages.yml).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

export const IMAGE_MANIFEST = [
  "assets/backgrounds/main_background.jpg",
  "assets/backgrounds/terminal_background.jpg",
  "assets/mobile_bg.jpg",
];

export async function buildImageTiers(inputPath) {
  const ext = path.extname(inputPath);
  const avifPath = inputPath.slice(0, -ext.length) + ".avif";
  const webpPath = inputPath.slice(0, -ext.length) + ".webp";

  await sharp(inputPath)
    .avif({ quality: 65, effort: 6, chromaSubsampling: "4:2:0" })
    .toFile(avifPath);
  await sharp(inputPath).webp({ quality: 75, effort: 6 }).toFile(webpPath);

  return {
    avifPath,
    webpPath,
    sourceBytes: fs.statSync(inputPath).size,
    avifBytes: fs.statSync(avifPath).size,
    webpBytes: fs.statSync(webpPath).size,
  };
}

const kb = (bytes) => `${(bytes / 1024).toFixed(1)}KB`;

export async function main() {
  let totalSource = 0;
  let totalAvif = 0;
  let totalWebp = 0;

  for (const relPath of IMAGE_MANIFEST) {
    const result = await buildImageTiers(relPath);
    totalSource += result.sourceBytes;
    totalAvif += result.avifBytes;
    totalWebp += result.webpBytes;
    console.log(
      `${relPath}: jpg ${kb(result.sourceBytes)} -> avif ${kb(result.avifBytes)}, webp ${kb(result.webpBytes)}`,
    );
  }

  console.log("\n=== Image Tier Summary ===");
  console.log(`Processed ${IMAGE_MANIFEST.length} images.`);
  console.log(
    `JPEG total: ${kb(totalSource)} -> AVIF ${kb(totalAvif)} (${((1 - totalAvif / totalSource) * 100).toFixed(1)}% smaller), WebP ${kb(totalWebp)} (${((1 - totalWebp / totalSource) * 100).toFixed(1)}% smaller)`,
  );
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
