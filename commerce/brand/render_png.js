// Renders the final logo SVGs to PNG sizes with Chromium (no SVG rasteriser is installed here).
// Usage: node brand/render_png.js   (after: python3 -c "import make_logo; make_logo.export_final()")
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "logo", "final");
(async () => {
  const b = await chromium.launch();
  const icon = fs.readFileSync(path.join(dir, "icon.svg"), "utf8");
  for (const s of [16, 32, 48, 180, 192, 512]) {
    const p = await b.newPage({ viewport: { width: s, height: s } });
    await p.setContent(`<style>*{margin:0}svg{width:${s}px;height:${s}px;display:block}</style>${icon}`);
    await p.screenshot({ path: path.join(dir, `icon-${s}.png`), omitBackground: true });
    await p.close();
  }
  for (const [name, w] of [["logo", 1200], ["logo-reversed", 1200]]) {
    const svg = fs.readFileSync(path.join(dir, name + ".svg"), "utf8");
    const p = await b.newPage({ viewport: { width: w, height: 400 } });
    await p.setContent(`<style>*{margin:0}body{background:${name.includes("reversed") ? "#17243b" : "transparent"}}svg{width:${w}px;height:auto;display:block}</style>${svg}`);
    const el = await p.$("svg");
    await el.screenshot({ path: path.join(dir, name + ".png"), omitBackground: !name.includes("reversed") });
    await p.close();
  }
  const og = await b.newPage({ viewport: { width: 1200, height: 630 } });
  await og.goto("file://" + path.join(dir, "og.html"));
  await og.screenshot({ path: path.join(dir, "og.png") });
  await b.close();
  console.log("rendered PNGs into", dir);
})();
