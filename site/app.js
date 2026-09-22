const byId = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
let cases = [];
let capabilities = [];
let activeCase = null;
let activeHypothesis = null;
let proofRan = false;
let accepted = false;

const esc = value => String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const confidence = h => Math.round((1 - Number(h.uncertainty ?? .5)) * 100);
const candidate = () => activeCase?.candidates.find(c => c.hypothesis_id === activeHypothesis?.id) || null;

function toast(message) {
  const el = byId("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 1900);
}

function renderCaseReel() {
  byId("caseReel").innerHTML = cases.map((item, index) =>
    '<button type="button" class="case-ticket ' + (item.id === activeCase?.id ? "active" : "") + '" data-case="' + esc(item.id) + '">' +
    '<span>CASE ' + String(index + 1).padStart(2, "0") + '</span><b>' + esc(item.short_title) + '</b></button>'
  ).join("");
  document.querySelectorAll(".case-ticket").forEach(button => {
    button.addEventListener("click", () => {
      activeCase = cases.find(item => item.id === button.dataset.case);
      renderCase();
    });
  });
}

function renderEvidence() {
  byId("decisionCapsule").innerHTML = Object.entries(activeCase.decision_capsule).map(([key, value]) =>
    '<div><dt>' + esc(key.replaceAll("_", " ")) + '</dt><dd>' + esc(value) + '</dd></div>'
  ).join("");
  byId("outcomeReceipt").textContent = activeCase.outcome_receipt;
  byId("evidenceList").innerHTML = activeCase.evidence.map(item =>
    '<div class="evidence-line"><b>' + esc(item.kind) + ' · ' + Math.round(item.confidence * 100) + '%</b><span>' + esc(item.note) + '</span></div>'
  ).join("");
}

function renderHypotheses() {
  byId("hypothesisLenses").innerHTML = activeCase.hypotheses.map(item =>
    '<button type="button" class="lens ' + (item.id === activeHypothesis?.id ? "active" : "") + '" data-hypothesis="' + esc(item.id) + '">' +
      '<div class="lens-top"><span>' + esc(item.id) + ' / ' + esc(item.target_surface) + '</span><span>' + confidence(item) + '%</span></div>' +
      '<p>' + esc(item.mechanism) + '</p></button>'
  ).join("");
  document.querySelectorAll(".lens").forEach(button => {
    button.addEventListener("click", () => {
      activeHypothesis = activeCase.hypotheses.find(item => item.id === button.dataset.hypothesis);
      resetProof();
      renderHypotheses();
      updateSelectedMutation();
    });
  });
}

function updateSelectedMutation() {
  const c = candidate();
  byId("selectedConfidence").textContent = confidence(activeHypothesis) + "%";
  byId("surfaceLabel").textContent = activeHypothesis.target_surface.toUpperCase() + " MUTATION";
  byId("mutationNote").textContent = c.title + " — " + c.surface + " surface";
  byId("runProofBtn").disabled = true;
  drawIdleWorldline();
}

function renderCase() {
  proofRan = false;
  accepted = false;
  activeHypothesis = [...activeCase.hypotheses].sort((a, b) => confidence(b) - confidence(a))[0];
  const number = cases.indexOf(activeCase) + 1;
  byId("sheetNumber").textContent = "EVO—" + String(number).padStart(3, "0");
  byId("failureTitle").textContent = activeCase.failure_title;
  byId("failureSummary").textContent = activeCase.failure_summary;
  renderEvidence();
  renderHypotheses();
  renderCaseReel();
  byId("evidenceDrawer").hidden = true;
  byId("evidenceToggle").setAttribute("aria-expanded", "false");
  byId("evidenceToggle").textContent = "show evidence + decision capsule ↓";
  resetProof();
  updateSelectedMutation();
}

function svgEl(name, attrs = {}) {
  const node = document.createElementNS(NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  return node;
}

function addText(svg, x, y, text, options = {}) {
  const node = svgEl("text", {
    x, y,
    "font-size": options.size || 13,
    fill: options.fill || "#51534c",
    "text-anchor": options.anchor || "middle"
  });
  node.textContent = text;
  svg.appendChild(node);
}

function addNode(svg, x, y, label, color, side) {
  svg.appendChild(svgEl("circle", {cx:x, cy:y, r:7, fill:"#fbfaf6", stroke:color, "stroke-width":3}));
  const anchor = side === "left" ? "end" : "start";
  const tx = side === "left" ? x - 16 : x + 16;
  addText(svg, tx, y + 4, label, {anchor, size:11, fill:"#353730"});
}

function drawIdleWorldline() {
  const svg = byId("worldSvg");
  svg.innerHTML = "";
  svg.appendChild(svgEl("line", {x1:500,y1:28,x2:500,y2:325,stroke:"#cbc7bc","stroke-width":2,"stroke-dasharray":"5 8"}));
  svg.appendChild(svgEl("circle", {cx:500,cy:82,r:10,fill:"#f2efe8",stroke:"#171814","stroke-width":2}));
  addText(svg, 500, 20, "same recorded case", {size:11});
  addText(svg, 500, 116, "test a cause to split the worldline", {size:12});
}

function drawWorldline(ran = false) {
  const c = candidate();
  const svg = byId("worldSvg");
  svg.innerHTML = "";

  const baseColor = "#d74c35";
  const candidateColor = "#3f63a8";
  svg.appendChild(svgEl("path", {d:"M500 22 L500 84 C500 120 335 120 300 156 L300 322",fill:"none",stroke:baseColor,"stroke-width":3}));
  svg.appendChild(svgEl("path", {d:"M500 84 C500 120 665 120 700 156 L700 322",fill:"none",stroke:candidateColor,"stroke-width":3,"stroke-dasharray":ran ? "0" : "8 8",opacity:ran ? "1" : ".55"}));
  svg.appendChild(svgEl("circle", {cx:500,cy:84,r:10,fill:"#e2d46d",stroke:"#171814","stroke-width":2}));
  addText(svg, 500, 20, "shared state", {size:11});
  addText(svg, 500, 72, "mutation point", {size:10, fill:"#77796f"});

  const baseSteps = c.baseline_flow.slice(0, 5);
  const candSteps = c.candidate_flow.slice(0, 5);
  const yStart = 164;
  const yGapBase = Math.min(50, 150 / Math.max(1, baseSteps.length - 1));
  const yGapCand = Math.min(50, 150 / Math.max(1, candSteps.length - 1));

  baseSteps.forEach((step, i) => addNode(svg, 300, yStart + i * yGapBase, step, baseColor, "left"));
  candSteps.forEach((step, i) => addNode(svg, 700, yStart + i * yGapCand, step, candidateColor, "right"));

  addText(svg, 300, 345, c.baseline_result, {size:14, fill:baseColor});
  addText(svg, 700, 345, ran ? c.candidate_result : "UNRUN", {size:14, fill:ran ? (c.eligible ? "#386c49" : "#d74c35") : "#77796f"});
}

function spliceWorld() {
  byId("worldlineSection").classList.remove("muted-stage");
  drawWorldline(false);
  byId("runProofBtn").disabled = false;
  byId("mutationNote").textContent = "World fork prepared. Baseline stays fixed; only " + candidate().surface + " changes.";
  byId("worldlineSection").scrollIntoView({behavior:"smooth", block:"center"});
}

function resetProof() {
  proofRan = false;
  accepted = false;
  byId("proofResult").hidden = true;
  byId("worldlineSection").classList.add("muted-stage");
  byId("runProofBtn").disabled = true;
  byId("promoteBtn").disabled = true;
  byId("rollbackBtn").hidden = true;
  byId("rejectBtn").hidden = false;
  drawIdleWorldline();
}

function renderReceipts(c) {
  byId("replayReceipts").innerHTML = c.replays.map(item => {
    const regressed = item.delta < 0;
    return '<div class="receipt-ticket ' + (regressed ? "regressed" : "") + '">' +
      '<div class="r-head"><span>' + esc(item.case_id) + '</span><span>' + esc(item.suite) + '</span></div>' +
      '<strong>' + item.baseline.toFixed(1) + ' → ' + item.candidate.toFixed(1) + '</strong>' +
      '<span class="delta">' + (item.delta >= 0 ? "+" : "") + item.delta.toFixed(1) + ' delta</span></div>';
  }).join("");
}

function runProof() {
  const c = candidate();
  byId("runProofBtn").disabled = true;
  byId("runProofBtn").textContent = "MEASURING…";
  setTimeout(() => {
    proofRan = true;
    drawWorldline(true);
    byId("proofResult").hidden = false;
    byId("mutationTitle").textContent = c.title;
    byId("beforeDiff").textContent = c.behavior.before;
    byId("afterDiff").textContent = c.behavior.after;
    byId("meanDelta").textContent = (c.mean_delta >= 0 ? "+" : "") + c.mean_delta.toFixed(3);
    byId("regressions").textContent = c.regressions;
    byId("riskFlags").textContent = c.risk_flags.length;
    byId("verdictStamp").textContent = c.eligible ? "SURVIVED" : "BROKE";
    byId("verdictStamp").className = "verdict-stamp " + (c.eligible ? "pass" : "fail");
    byId("gateExplanation").textContent = c.eligible
      ? "The fixture replay improves the failing cases without measured regression. Eligible in this demo gate."
      : "The candidate fixes part of the failure but introduces a regression or risk flag. Do not promote.";
    byId("promoteBtn").disabled = !c.eligible;
    byId("runProofBtn").textContent = "RUN PROOF →";
    renderReceipts(c);
    byId("proofResult").scrollIntoView({behavior:"smooth", block:"start"});
    toast(c.eligible ? "Candidate survived the fixture proof." : "Proof found a regression.");
  }, 520);
}

function acceptMutation() {
  if (!proofRan || !candidate().eligible) return;
  accepted = true;
  byId("verdictStamp").textContent = "ACCEPTED";
  byId("promoteBtn").disabled = true;
  byId("rollbackBtn").hidden = false;
  byId("gateExplanation").textContent = "Accepted in browser demo state. No repository or runtime mutation was performed.";
  toast("Accepted locally. Runtime deployment is not wired yet.");
}

function rollback() {
  if (!accepted) return;
  accepted = false;
  byId("verdictStamp").textContent = "ROLLED BACK";
  byId("rollbackBtn").hidden = true;
  byId("promoteBtn").disabled = false;
  byId("gateExplanation").textContent = "Browser state returned to the pre-acceptance candidate.";
  toast("Demo state rolled back.");
}

function rejectMutation() {
  byId("verdictStamp").textContent = "REJECTED";
  byId("verdictStamp").className = "verdict-stamp fail";
  byId("promoteBtn").disabled = true;
  byId("gateExplanation").textContent = "Rejected by reviewer in browser demo state.";
  toast("Mutation rejected.");
}

function renderCapabilities() {
  byId("capabilityGrid").innerHTML = capabilities.map(item =>
    '<div class="capability-row"><span class="cap-status ' + esc(item.status) + '">' + esc(item.status) + '</span>' +
    '<b>' + esc(item.name) + '</b><p>' + esc(item.evidence) + (item.limitation ? ' <strong>Limit:</strong> ' + esc(item.limitation) : '') + '</p></div>'
  ).join("");
}

async function init() {
  try {
    const [casePayload, capabilityPayload, buildPayload] = await Promise.all([
      fetch("data/evolution_cases.json").then(r => { if (!r.ok) throw new Error("case data " + r.status); return r.json(); }),
      fetch("data/capabilities.json").then(r => { if (!r.ok) throw new Error("capabilities " + r.status); return r.json(); }),
      fetch("data/skills.json").then(r => r.ok ? r.json() : null).catch(() => null)
    ]);
    cases = casePayload.cases;
    capabilities = capabilityPayload.capabilities;
    activeCase = cases[0];
    if (buildPayload?.commit) byId("build").textContent = "build " + buildPayload.commit;
    renderCase();
    renderCapabilities();
  } catch (error) {
    byId("failureTitle").textContent = "Demo data could not be loaded.";
    byId("failureSummary").textContent = String(error);
  }
}

byId("evidenceToggle").addEventListener("click", () => {
  const drawer = byId("evidenceDrawer");
  drawer.hidden = !drawer.hidden;
  const expanded = !drawer.hidden;
  byId("evidenceToggle").setAttribute("aria-expanded", String(expanded));
  byId("evidenceToggle").textContent = expanded ? "hide evidence + decision capsule ↑" : "show evidence + decision capsule ↓";
});
byId("spliceBtn").addEventListener("click", spliceWorld);
byId("runProofBtn").addEventListener("click", runProof);
byId("promoteBtn").addEventListener("click", acceptMutation);
byId("rollbackBtn").addEventListener("click", rollback);
byId("rejectBtn").addEventListener("click", rejectMutation);
init();
