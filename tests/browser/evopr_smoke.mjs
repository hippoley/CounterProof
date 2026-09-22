import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

try {
  await page.goto("http://127.0.0.1:8765", { waitUntil: "networkidle" });

  await page.waitForSelector(".case-ticket");
  const title = await page.locator("#failureTitle").textContent();
  if (!title || title.includes("Loading")) throw new Error("case did not initialize");

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

  // The capability truth table must be visible and honest.
  await page.waitForSelector(".capability-row");
  const pageText = await page.locator("body").textContent();
  if (!pageText.includes("planned") || !pageText.includes("Command replay")) {
    throw new Error("capability truth table is missing");
  }

  console.log("EvoPR browser smoke: PASS");
} finally {
  await browser.close();
}
