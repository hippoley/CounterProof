import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

try {
  await page.goto("http://127.0.0.1:8765", { waitUntil: "networkidle" });

  await page.waitForSelector(".case-ticket");
  const title = await page.locator("#failureTitle").textContent();
  if (!title || title.includes("Loading")) throw new Error("case did not initialize");

  // Compare all causes first. The fixture matrix should identify one survivor
  // while explicitly treating the result as relative evidence.
  await page.locator("#compareBtn").click();
  await page.waitForSelector("#discriminationSection:not([hidden])");
  await page.waitForFunction(() =>
    document.querySelector("#discriminationStamp")?.textContent === "POLICY SURVIVES"
  );
  const discriminationText = await page.locator("#discriminationSection").textContent();
  if (!discriminationText.includes("relative support")) {
    throw new Error("discrimination UI overstates causal certainty");
  }
  if (!discriminationText.includes("cross-tenant-attack-07")) {
    throw new Error("diagnostic discrimination case is missing");
  }

  // Prove a bad hypothesis is rejected by fixture evidence.
  await page.locator('.lens[data-hypothesis="H3"]').click();
  await page.locator("#spliceBtn").click();
  await page.locator("#runProofBtn").click();
  await page.waitForSelector("#proofResult:not([hidden])");
  await page.waitForFunction(() => document.querySelector("#verdictStamp")?.textContent === "BROKE");
  if (!(await page.locator("#promoteBtn").isDisabled())) {
    throw new Error("regressing candidate became promotable");
  }

  // Prove the strongest hypothesis can survive, be accepted, then rolled back.
  await page.locator('.lens[data-hypothesis="H2"]').click();
  await page.locator("#spliceBtn").click();
  await page.locator("#runProofBtn").click();
  await page.waitForFunction(() => document.querySelector("#verdictStamp")?.textContent === "SURVIVED");
  if (await page.locator("#promoteBtn").isDisabled()) {
    throw new Error("eligible candidate was not promotable");
  }

  await page.locator("#promoteBtn").click();
  await page.waitForFunction(() => document.querySelector("#verdictStamp")?.textContent === "ACCEPTED");
  await page.locator("#rollbackBtn").click();
  await page.waitForFunction(() => document.querySelector("#verdictStamp")?.textContent === "ROLLED BACK");

  // Ambiguous evidence must stay ambiguous and surface a next probe instead of a fake winner.
  await page.locator('.case-ticket[data-case="evo-destructive-confirm-003"]').click();
  await page.locator("#compareBtn").click();
  await page.waitForSelector("#discriminationSection:not([hidden])");
  await page.waitForFunction(() =>
    document.querySelector("#discriminationStamp")?.textContent === "AMBIGUOUS"
  );
  const ambiguousText = await page.locator("#discriminationSection").textContent();
  if (!ambiguousText.includes("Next probe") || !ambiguousText.includes("Separate policy from skill")) {
    throw new Error("ambiguous comparison did not produce a next probe");
  }

  // The first screen must communicate the concrete proof-of-fix wedge.
  const witnessHero = await page.locator(".witness-hero").textContent();
  if (!witnessHero.includes("WITNESSED") || !witnessHero.includes("BASE CODE + PR TEST")) {
    throw new Error("Regression Witness hero is missing the before/after proof");
  }

  // Reality Lab must expose real external PR cases and keep their proof boundaries visible.
  await page.waitForSelector(".reality-card");
  const realityCards = await page.locator(".reality-card").count();
  if (realityCards < 5) {
    throw new Error(`expected at least 5 Reality Lab cases, got ${realityCards}`);
  }

  const realityText = await page.locator(".reality-lab").textContent();
  for (const expected of [
    "rundef/async_rithmic#53",
    "openai/codex-plugin-cc#731",
    "openai/codex-plugin-cc#456",
    "MetrolistGroup/Metrolist#4097",
    "anthropics/claude-code#89404",
    "WITNESSED",
    "INCONCLUSIVE",
    "OPEN PROBE",
  ]) {
    if (!realityText.includes(expected)) {
      throw new Error(`Reality Lab is missing ${expected}`);
    }
  }

  const sourceLinks = await page.locator('.reality-links a').count();
  if (sourceLinks < 10) {
    throw new Error("Reality Lab did not render both source and probe links");
  }

  const productChanges = await page.locator('.reality-change').count();
  if (productChanges < 5) {
    throw new Error("Reality Lab did not expose the reality-to-product feedback loop");
  }

  const realityCta = await page.locator(".reality-cta a").getAttribute("href");
  if (!realityCta || !realityCta.includes("issues/new?template=reality-probe.yml")) {
    throw new Error("Reality Lab intake does not use the structured Reality Probe issue form");
  }

  const productChangeText = await page.locator(".reality-lab").textContent();
  for (const expected of [
    "Node .test.mjs/.cjs discovery",
    "Changed test-support integrity finding",
    "Infrastructure failure no longer mints a witness",
    "Not built yet — waiting for reviewer validation",
  ]) {
    if (!productChangeText.includes(expected)) {
      throw new Error(`Reality Lab is missing product change: ${expected}`);
    }
  }

  // The capability truth table must be visible and honest.
  await page.waitForSelector(".capability-row");
  const pageText = await page.locator("body").textContent();
  if (
    !pageText.includes("planned") ||
    !pageText.includes("Command replay") ||
    !pageText.includes("Active discrimination")
  ) {
    throw new Error("capability truth table is missing");
  }

  console.log("CounterProof browser smoke: PASS");
} finally {
  await browser.close();
}
