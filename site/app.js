const $ = id => document.getElementById(id);
let payload = null, selected = null;
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function casesFor(skill) {
  if (!skill.evals) return [];
  return Array.isArray(skill.evals) ? skill.evals : (skill.evals.cases || skill.evals.evals || []);
}

function queryGroups(skill) {
  const q = skill.trigger_queries || {};
  return {
    yes: q.should_trigger || q.should_activate || q.positive || [],
    no: q.should_not_trigger || q.should_not_activate || q.negative || []
  };
}

function renderList(items) {
  $('skills').innerHTML = items.map(s => `<button class="skill ${selected?.name===s.name?'active':''}" data-name="${escapeHtml(s.name)}"><b>${escapeHtml(s.name)}</b><small>${escapeHtml(s.description)}</small><span class="tags"><i class="tag ${s.validation.passed?'ok':''}">${s.validation.passed?'VALID':'CHECK'}</i><i class="tag">${escapeHtml(s.domain)}</i></span></button>`).join('') || '<p class="loading">No matching skills.</p>';
  document.querySelectorAll('.skill').forEach(el => el.addEventListener('click', () => select(el.dataset.name)));
}

function select(name) {
  selected = payload.skills.find(s => s.name === name);
  renderList(filter());
  const evals = casesFor(selected), q = queryGroups(selected), v = selected.validation;
  $('detail').innerHTML = `<div class="detail-head"><div><p class="eyebrow">${escapeHtml(selected.domain)} · V${escapeHtml(selected.version)}</p><h2>${escapeHtml(selected.name)}</h2></div><span class="status ${v.passed?'pass':'fail'}">${v.passed?'✓ STATIC CHECK PASSED':'✕ VALIDATION FAILED'}</span></div><p class="desc">${escapeHtml(selected.description)}</p>
  <div class="tabs"><button class="active" data-tab="overview">Overview</button><button data-tab="contract">SKILL.md</button><button data-tab="evals">Evals (${evals.length})</button><button data-tab="triggers">Trigger boundary</button></div>
  <div class="panel active" id="overview"><div class="cards"><div class="card"><span>TAGS</span><strong>${selected.tags.length}</strong></div><div class="card"><span>EVAL CASES</span><strong>${evals.length}</strong></div><div class="card"><span>RESOURCES</span><strong>${Object.values(selected.resources).reduce((a,b)=>a+b,0)}</strong></div></div><div class="validation"><h3>Repository validator</h3>${v.errors.length?`<ul>${v.errors.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>`:'<p>No blocking errors.</p>'}${v.warnings.length?`<ul>${v.warnings.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>`:'<p>No warnings.</p>'}</div></div>
  <div class="panel" id="contract"><pre>${escapeHtml(selected.content)}</pre></div>
  <div class="panel" id="evals">${evals.length?evals.map((e,i)=>`<div class="eval"><b>${escapeHtml(e.id || `case-${i+1}`)}</b><span>${escapeHtml(e.task || e.query || e.input || JSON.stringify(e))}</span></div>`).join(''):'<p>No eval cases in this skill.</p>'}</div>
  <div class="panel" id="triggers"><div class="queries"><div class="query-group"><h3>SHOULD TRIGGER</h3>${q.yes.map(x=>`<div class="query">${escapeHtml(typeof x==='string'?x:(x.query||x.input||JSON.stringify(x)))}</div>`).join('')||'<p>Not specified.</p>'}</div><div class="query-group"><h3>SHOULD NOT TRIGGER</h3>${q.no.map(x=>`<div class="query no">${escapeHtml(typeof x==='string'?x:(x.query||x.input||JSON.stringify(x)))}</div>`).join('')||'<p>Not specified.</p>'}</div></div></div>`;
  document.querySelectorAll('.tabs button').forEach(btn => btn.addEventListener('click', () => {document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));btn.classList.add('active');$(btn.dataset.tab).classList.add('active')}));
}

function filter() {
  const q = $('search').value.toLowerCase();
  return payload.skills.filter(s => [s.name,s.description,s.domain,...s.tags].join(' ').toLowerCase().includes(q));
}

async function init() {
  try {
    payload = await fetch('data/skills.json').then(r => {if(!r.ok) throw new Error(r.status); return r.json()});
    $('build').textContent = `VERIFIED BUILD · ${payload.commit}`;
    $('total').textContent = payload.summary.total; $('valid').textContent = payload.summary.valid; $('cases').textContent = payload.summary.eval_cases;
    renderList(payload.skills); if (payload.skills.length) select(payload.skills[0].name);
  } catch (error) { $('skills').innerHTML = `<p class="loading">Build data unavailable: ${escapeHtml(error)}</p>`; }
}
$('search').addEventListener('input', () => renderList(filter()));
init();
