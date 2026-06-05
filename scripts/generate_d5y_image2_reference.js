#!/usr/bin/env node
"use strict";

const fs = require("fs/promises");
const { spawn } = require("child_process");
const path = require("path");
const os = require("os");
const sharp = require("sharp");

const ROOT = path.join(os.homedir(), "Projects", "RodiO");
const BASE = path.join(ROOT, "pwa", "assets", "source", "bmng_staging");

const OUTPUTS = {
  image2: path.join(BASE, "image2_d5y_regional_ocean_reference_1536.png"),
  palette: path.join(BASE, "image2_d5y_palette_reference.png"),
  notes: path.join(BASE, "image2_d5y_reference_notes.json"),
};

const ENDPOINT = "https://api.openai.com/v1/images/generations";
const MODEL = "gpt-image-2";
const SIZE = "1536x1024";
const QUALITY = "high";
const OUTPUT_FORMAT = "png";

const PROMPT = `Generate a wide-format Earth ocean color reference for a realistic daytime Blue Marble style texture.

This is NOT a fantasy map and NOT a political map.

Preserve the impression of a NASA Blue Marble / natural Earth satellite texture.
Do not add labels, borders, clouds, city lights, icons, grid lines, text, bathymetric contour lines, or artistic decorations.

The goal is regional ocean color differentiation, subtle and natural:

- East Asian marginal seas, including Bohai Sea, Yellow Sea, East China Sea, Taiwan Strait, northern South China Sea and Japan Sea:
  muted grey-blue, slightly turbid, low saturation, not tropical, not green, not muddy yellow.

- Tropical shallow seas, including Bahamas, Caribbean, Great Barrier Reef, northern Australia, Philippines, Indonesia, Maldives and South Pacific island chains:
  clear low-saturation cyan-blue, visible shallow banks and reefs, not candy-colored, not neon, no hard rings.

- Persian Gulf and Red Sea:
  warm grey shallow water, slightly hazy, lower blue feeling, not tropical cyan, not muddy yellow.

- High latitude shallow seas, including North Sea, Bering Sea, Sea of Okhotsk, Greenland margins, Arctic margins and Southern Ocean:
  cool grey-blue, icy water feeling, low saturation, not white, not tropical.

- Deep ocean:
  preserve existing deep blue tone, do not add abyssal terrain patterns, do not darken the Pacific, do not add seafloor texture.

- Land and ice:
  preserve original land and ice appearance. Do not recolor continents, Antarctica, Greenland, deserts, forests, mountains or snow.

The result should be restrained, photographic, globally coherent, and useful as a color reference for algorithmic texture generation.

Important:
The output is only a visual reference. It does not need to be pixel-perfect GIS data. It must preserve the recognizable world map layout and recognizable coastlines as much as possible.`;

const SWATCHES = [
  { label: "deep-ocean", rgb: [46, 76, 112] },
  { label: "global-200-1000", rgb: [72, 107, 126] },
  { label: "global-50-200", rgb: [85, 137, 159] },
  { label: "global-20-50", rgb: [102, 157, 174] },
  { label: "global-0-20", rgb: [120, 170, 178] },
  { label: "east-asia", rgb: [130, 175, 174] },
  { label: "tropical", rgb: [142, 216, 200] },
  { label: "gulf-redsea", rgb: [169, 191, 175] },
  { label: "high-latitude", rgb: [124, 169, 180] },
];

function parseArgs(argv) {
  const set = new Set(argv);
  return {
    dryRun: set.has("--dry-run"),
    force: set.has("--force"),
    help: set.has("--help") || set.has("-h"),
  };
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(filePath) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
}

async function maybeWriteFile(filePath, buffer, force) {
  if (!force && (await fileExists(filePath))) {
    return { written: false, skipped: true, reason: "exists" };
  }
  await ensureDir(filePath);
  await fs.writeFile(filePath, buffer);
  return { written: true, skipped: false };
}

async function maybeWriteText(filePath, text, force) {
  if (!force && (await fileExists(filePath))) {
    return { written: false, skipped: true, reason: "exists" };
  }
  await ensureDir(filePath);
  await fs.writeFile(filePath, text, "utf8");
  return { written: true, skipped: false };
}

async function buildPaletteReference(force) {
  const palettePath = OUTPUTS.palette;
  if (!force && (await fileExists(palettePath))) {
    return { written: false, skipped: true, reason: "exists" };
  }

  const swatchW = 160;
  const swatchH = 384;
  const width = swatchW * SWATCHES.length;
  const height = swatchH;
  const base = sharp({
    create: {
      width,
      height,
      channels: 3,
      background: { r: 14, g: 20, b: 28 },
    },
  });

  const layers = [];
  for (let i = 0; i < SWATCHES.length; i += 1) {
    const sw = SWATCHES[i];
    const tile = await sharp({
      create: {
        width: swatchW - 4,
        height: swatchH - 4,
        channels: 3,
        background: { r: sw.rgb[0], g: sw.rgb[1], b: sw.rgb[2] },
      },
    })
      .png()
      .toBuffer();
    layers.push({ input: tile, left: i * swatchW + 2, top: 2 });
  }

  const out = await base.composite(layers).png().toBuffer();
  await ensureDir(palettePath);
  await fs.writeFile(palettePath, out);
  return { written: true, skipped: false };
}

async function generateImage2(prompt, apiKey) {
  const payloadBody = JSON.stringify({
    model: MODEL,
    prompt,
    size: SIZE,
    quality: QUALITY,
    output_format: OUTPUT_FORMAT,
    n: 1,
  });

  const rawResponse = await new Promise((resolve, reject) => {
    const child = spawn(
      "curl",
      [
        "-sS",
        "-X",
        "POST",
        ENDPOINT,
        "-H",
        "Content-Type: application/json",
        "-H",
        `Authorization: Bearer ${apiKey}`,
        "--data-binary",
        "@-",
        "-o",
        "-",
        "-w",
        "\n%{http_code}",
      ],
      { stdio: ["pipe", "pipe", "pipe"] },
    );

    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0 && !stdout) {
        reject(new Error(`curl exited with code ${code}${stderr ? `: ${stderr.trim()}` : ""}`));
        return;
      }
      resolve({ stdout, stderr });
    });
    child.stdin.end(payloadBody);
  });

  const stdout = rawResponse.stdout || "";
  const lastNewline = stdout.lastIndexOf("\n");
  if (lastNewline < 0) {
    throw new Error(`OpenAI Images API returned an unexpected response: ${stdout.slice(0, 200)}`);
  }

  const body = stdout.slice(0, lastNewline);
  const statusText = stdout.slice(lastNewline + 1).trim();
  const status = Number(statusText);
  if (!Number.isFinite(status)) {
    throw new Error(`OpenAI Images API returned an invalid status marker: ${statusText}`);
  }
  if (status < 200 || status >= 300) {
    throw new Error(`OpenAI Images API error ${status}: ${body}`);
  }

  const payload = JSON.parse(body);
  const b64 = payload?.data?.[0]?.b64_json;
  if (!b64) {
    throw new Error("OpenAI Images API returned no b64_json image data.");
  }
  return Buffer.from(b64, "base64");
}

async function main() {
  const { dryRun, force, help } = parseArgs(process.argv.slice(2));
  if (help) {
    console.log([
      "Usage: node scripts/generate_d5y_image2_reference.js [--dry-run] [--force]",
      "",
      "--dry-run  Print endpoint/model/size/quality/output paths and whether OPENAI_API_KEY exists. Do not call API or write files.",
      "--force    Allow overwriting existing outputs.",
    ].join("\n"));
    return;
  }

  const apiKey = process.env.OPENAI_API_KEY || "";
  const apiKeyExists = Boolean(apiKey);

  if (dryRun) {
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          OPENAI_API_KEY_exists: apiKeyExists,
          endpoint: ENDPOINT,
          model: MODEL,
          size: SIZE,
          quality: QUALITY,
          outputFormat: OUTPUT_FORMAT,
          force,
          outputs: OUTPUTS,
        },
        null,
        2,
      ),
    );
    return;
  }

  const paletteResult = await buildPaletteReference(force);

  let image2Result = {
    created: false,
    skipped: true,
    reason: apiKeyExists ? "exists or not run" : "OPENAI_API_KEY is missing",
  };

  if (!apiKeyExists) {
    image2Result.reason = "OPENAI_API_KEY is missing";
  } else if (!force && (await fileExists(OUTPUTS.image2))) {
    image2Result.reason = "exists";
  } else {
    const imageBuffer = await generateImage2(PROMPT, apiKey);
    const writeResult = await maybeWriteFile(OUTPUTS.image2, imageBuffer, force);
    image2Result = {
      created: writeResult.written,
      skipped: writeResult.skipped,
      reason: writeResult.reason || null,
    };
  }

  const notes = {
    apiKeyPresent: apiKeyExists,
    image2Stage: apiKeyExists
      ? image2Result.created
        ? "created"
        : `skipped: ${image2Result.reason}`
      : "skipped: OPENAI_API_KEY is missing",
    endpoint: ENDPOINT,
    model: MODEL,
    size: SIZE,
    quality: QUALITY,
    outputFormat: OUTPUT_FORMAT,
    outputs: OUTPUTS,
    prompt: PROMPT,
    paletteReference: paletteResult,
    image2Reference: image2Result,
    force,
    timestamp: new Date().toISOString(),
  };

  const notesResult = await maybeWriteText(OUTPUTS.notes, JSON.stringify(notes, null, 2) + "\n", force);

  console.log(
    JSON.stringify(
      {
        OPENAI_API_KEY_exists: apiKeyExists,
        endpoint: ENDPOINT,
        model: MODEL,
        size: SIZE,
        quality: QUALITY,
        outputFormat: OUTPUT_FORMAT,
        outputs: OUTPUTS,
        paletteReference: paletteResult,
        image2Reference: image2Result,
        notes: notesResult,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
