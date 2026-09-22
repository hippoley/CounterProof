const byId = id => document.getElementById(id);
let cases = [], activeCase = null, activeHypothesis = null, replayDone = false, promoted = false;

const esc = value => String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const confidence = h => Math.round((1 - Number(h.uncertainty ?? .5)) * 100);

function candidate() {
  return activeCase?.candidates.find(c => c.hypothesis_id === activeHypothesis?.id) || null;
}
function packetState(label, mode="neutral") {
  byId("packetStatus").textContent = label;
  byId("packetStatus").className = "pill " + mode;
}
function toast(message) {
  const el = byId("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 2200);
}
function renderCaseSelector() {
  byId("caseSelect").innerHTML = cases.map(c => '<option value="' + esc(c.id) + '">' + esc(c.short_title) + '</option>').join("");
}
function renderHypotheses() {
  byId("hypothesisList").innerHTML = activeCase.hypotheses.map(h =>
    '<button class="hypothesis ' + (activeHypothesis?.id === h.id ? "active" : "") + '" data-id="' + esc(h.id) + '">' +
      '<div class="hypothesis-top"><div><span class="hypothesis-id">' + esc(h.id) + '</span><span class="surface">' + esc(h.target_surface) + '</span></div><span class="confidence">' + confidence(h) + '%</span></div>' +
      '<p>' + esc(h.mechanism) + '</p></button>'
  ).join("");
  document.querySelectorAll(".hypothesis").forEach(btn => btn.addEventListener("click", () => {
    activeHypothesis = activeCase.hypotheses.find(h => h.id === btn.dataset.id);
    replayDone = false; promoted = false;
    renderHypotheses(); renderMutation(); resetReplay();
    packetState("HYPOTHESIS SELECTED");
  }));
}
function renderMutation() {
  const c = candidate();
  if (!c) return;
  byId("mutationTitle").textContent = c.title;
  byId("surfaceTag").textContent = c.surface.toUpperCase();
  byId("beforeDiff").textContent = c.behavior.before;
  byId("afterDiff").textContent = c.behavior.after;
}
function resetReplay() {
  byId("worldFork").classList.add("hidden");
  byId("meanDelta").textContent = "—";
  byId("regressions").textContent = "—";
  byId("riskFlags").textContent = "—";
  byId("promoteBtn").disabled = true;
  byId("rollbackBtn").disabled = true;
  byId("gateText").textContent = "WAITING FOR REPLAY";
  byId("gateLight").className = "gate-light";
  byId("replayMatrix").className = "replay-matrix empty";
  byId("replayMatrix").innerHTML = '<span>REPLAY MATRIX</span><p>Fork the world and run replay to produce promotion evidence.</p>';
}
function renderCase() {
  activeHypothesis = [...activeCase.hypotheses].sort((a,b) => confidence(b) - confidence(a))[0];
  replayDone = false; promoted = false;
  byId("packetId").textContent = activeCase.id;
  byId("failureTitle").textContent = activeCase.failure_title;
  byId("failureSummary").textContent = activeCase.failure_summary;
  byId("outcomeReceipt").textContent = activeCase.outcome_receipt;
  byId("decisionCapsule").innerHTML = Object.entries(activeCase.decision_capsule).map(([k,v]) =>
    '<div class="capsule-row"><span>' + esc(k.replaceAll("_"," ")) + '</span><span>' + esc(v) + '</span></div>'
  ).join("");
  byId("evidenceList").innerHTML = activeCase.evidence.map(e =>
    '<div class="evidence"><div class="evidence-top"><b>' + esc(e.kind.replaceAll("_"," ")) + '</b><i>' + Math.round(e.confidence*100) + '% CONF</i></div><p>' + esc(e.note) + '</p></div>'
  ).join("");
  packetState("READY TO PROBE");
  renderHypotheses(); renderMutation(); resetReplay();
}
function flow(target, steps, changed=false) {
  byId(target).innerHTML = steps.map((step,i) => '<div class="flow-step ' + (changed && i===steps.length-2 ? "changed":"") + '">' + esc(step) + '</div>').join("");
}
function forkWorld() {
  const c = candidate();
  byId("worldFork").classList.remove("hidden");
  byId("forkHypothesis").textContent = activeHypothesis.id + " · " + c.surface;
  flow("baselineFlow", c.baseline_flow);
  flow("candidateFlow", c.candidate_flow, true);
  byId("baselineResult").textContent = c.baseline_result;
  byId("baselineResult").className = "world-result bad";
  byId("candidateResult").textContent = "NOT RUN";
  byId("candidateResult").className = "world-result pending";
  packetState("WORLD FORKED","running");
}
function runReplay() {
  const c = candidate();
  packetState("REPLAYING","running");
  byId("replayBtn").disabled = true;
  byId("candidateResult").textContent = "RUNNING…";
  setTimeout(() => {
    replayDone = true;
    byId("replayBtn").disabled = false;
    byId("candidateResult").textContent = c.candidate_result;
    byId("candidateResult").className = "world-result " + (c.eligible ? "good":"bad");
    byId("meanDelta").textContent = (c.mean_delta >= 0 ? "+" : "") + c.mean_delta.toFixed(3);
    byId("regressions").textContent = c.regressions;
    byId("riskFlags").textContent = c.risk_flags.length;
    byId("replayMatrix").className = "replay-matrix";
    byId("replayMatrix").innerHTML = '<span>REPLAY MATRIX</span><table class="replay-table"><thead><tr><th>CASE</th><th>SUITE</th><th>BASE</th><th>CAND</th><th>Δ</th></tr></thead><tbody>' +
      c.replays.map(r => '<tr><td>' + esc(r.case_id) + '</td><td>' + esc(r.suite) + '</td><td>' + r.baseline.toFixed(1) + '</td><td>' + r.candidate.toFixed(1) + '</td><td class="' + (r.delta>=0?"delta-good":"") + '">' + (r.delta>=0?"+":"") + r.delta.toFixed(1) + '</td></tr>').join("") +
      '</tbody></table>';
    byId("gateText").textContent = c.eligible ? "ELIGIBLE FOR PROMOTION" : "HOLD / REJECT";
    byId("gateLight").className = "gate-light " + (c.eligible ? "pass":"fail");
    byId("promoteBtn").disabled = !c.eligible;
    packetState(c.eligible ? "REPLAY PASSED":"REPLAY FAILED", c.eligible ? "pass":"running");
    toast(c.eligible ? "Replay passed. Candidate can be promoted." : "Replay exposed a regression.");
  }, 650);
}
function promote() {
  if (!replayDone || !candidate()?.eligible) return;
  promoted = true;
  byId("promoteBtn").disabled = true;
  byId("rollbackBtn").disabled = false;
  byId("gateText").textContent = "PROMOTED · ROLLBACK READY";
  packetState("PROMOTED","promoted");
  toast("Capability promoted in demo state.");
}
function rollback() {
  if (!promoted) return;
  promoted = false;
  byId("rollbackBtn").disabled = true;
  byId("promoteBtn").disabled = false;
  byId("gateText").textContent = "ROLLED BACK · CANDIDATE STILL VALID";
  packetState("ROLLED BACK");
  toast("Rolled back to previous capability.");
}
async function init() {
  try {
    const [payload, build] = await Promise.all([
      fetch("data/evolution_cases.json").then(r => { if(!r.ok) throw new Error(r.status); return r.json(); }),
      fetch("data/skills.json").then(r => r.ok ? r.json() : null).catch(() => null)
    ]);
    cases = payload.cases;
    if (build?.commit) byId("build").textContent = "BUILD " + build.commit;
    renderCaseSelector();
    activeCase = cases[0];
    renderCase();
  } catch (error) {
    document.querySelector(".workspace").innerHTML = '<div style="padding:40px;color:#ff6b5f">Demo data unavailable: ' + esc(error) + '</div>';
  }
}

byId("caseSelect").addEventListener("change", e => { activeCase = cases.find(c => c.id === e.target.value); renderCase(); });
byId("forkBtn").addEventListener("click", forkWorld);
byId("replayBtn").addEventListener("click", runReplay);
byId("promoteBtn").addEventListener("click", promote);
byId("rollbackBtn").addEventListener("click", rollback);
document.addEventListener("keydown", e => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !byId("worldFork").classList.contains("hidden")) runReplay();
});
init();
