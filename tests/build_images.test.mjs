import test, { describe, afterEach } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import sharp from "sharp";
import { IMAGE_MANIFEST, buildImageTiers, main } from "../tools/build_images.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");

describe("tools/build_images.mjs", () => {
  const tmpDirs = [];

  afterEach(() => {
    while (tmpDirs.length) {
      fs.rmSync(tmpDirs.pop(), { recursive: true, force: true });
    }
  });

  function makeTmpDir() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "build-images-"));
    tmpDirs.push(dir);
    return dir;
  }

  // A noise-filled JPEG stands in for a photographic background: flat-color
  // fixtures compress to near-nothing in every format and prove nothing about
  // the byte savings the tool exists to deliver.
  async function makeNoiseJpeg(filePath) {
    const width = 800;
    const height = 600;
    const pixels = Buffer.alloc(width * height * 3);
    for (let i = 0; i < pixels.length; i++) {
      pixels[i] = Math.floor(Math.random() * 256);
    }
    await sharp(pixels, { raw: { width, height, channels: 3 } })
      .jpeg({ quality: 90 })
      .toFile(filePath);
    return { width, height };
  }

  test("manifest covers only real site background JPEGs that exist on disk", () => {
    assert.ok(IMAGE_MANIFEST.length > 0);
    for (const relPath of IMAGE_MANIFEST) {
      assert.ok(relPath.endsWith(".jpg"), `${relPath} must be a .jpg source`);
      assert.ok(
        fs.existsSync(path.join(REPO_ROOT, relPath)),
        `${relPath} missing from the repo`,
      );
    }
  });

  test("buildImageTiers emits avif and webp next to the source at native size", async () => {
    const dir = makeTmpDir();
    const src = path.join(dir, "sample.jpg");
    const { width } = await makeNoiseJpeg(src);

    const result = await buildImageTiers(src);

    for (const tier of [result.avifPath, result.webpPath]) {
      assert.ok(fs.existsSync(tier), `${tier} was not written`);
      const meta = await sharp(tier).metadata();
      assert.equal(meta.width, width);
    }
    // libvips reports AVIF files as format "heif" with compression "av1".
    const avifMeta = await sharp(result.avifPath).metadata();
    assert.equal(avifMeta.format, "heif");
    assert.equal(avifMeta.compression, "av1");
    assert.equal((await sharp(result.webpPath).metadata()).format, "webp");
  });

  test("buildImageTiers reports byte sizes and avif beats the jpeg source", async () => {
    const dir = makeTmpDir();
    const src = path.join(dir, "sample.jpg");
    await makeNoiseJpeg(src);

    const result = await buildImageTiers(src);

    assert.equal(result.sourceBytes, fs.statSync(src).size);
    assert.equal(result.avifBytes, fs.statSync(result.avifPath).size);
    assert.equal(result.webpBytes, fs.statSync(result.webpPath).size);
    assert.ok(
      result.avifBytes < result.sourceBytes,
      `avif (${result.avifBytes}) should be smaller than jpeg (${result.sourceBytes})`,
    );
  });

  test("main runs over manifest and logs summary", async () => {
    const origLog = console.log;
    const logs = [];
    console.log = (...args) => logs.push(args.join(" "));
    try {
      await main();
      assert.ok(logs.some((l) => l.includes("Image Tier Summary")));
    } finally {
      console.log = origLog;
    }
  });
});
