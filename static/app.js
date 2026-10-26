// ============================================================
//  AI Job Recommendation – Frontend Application
// ============================================================

const API = '';   // same-origin Flask

// ============ Utility ============

function $(id) { return document.getElementById(id); }

function req(url, opts = {}) {
  return fetch(API + url, opts).then(r => r.json());
}

function skillList(raw) {
  if (!raw) return [];
  return raw.split(/[,;]+/).map(s => s.trim()).filter(Boolean);
}

function tagsHtml(skills, matchSet) {
  return skills.map(s => {
    const cls = matchSet && matchSet.has(s.toLowerCase()) ? 'sk-tag match' : 'sk-tag';
    return `<span class="${cls}">${s}</span>`;
  }).join('');
}

function cardTagsHtml(arr) {
  return arr.slice(0, 6).map(s => `<span class="card-tag">${s}</span>`).join('');
}

// ============ Theme Management (Light / Dark) ============

function initTheme() {
  const toggleBtn = $('theme-toggle');
  const icon = $('theme-icon');
  const label = $('theme-label');

  // Load saved theme or default to light
  const savedTheme = localStorage.getItem('app-theme') || 'light';
  applyTheme(savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem('app-theme', next);
    });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      if (icon) icon.textContent = '☀️';
      if (label) label.textContent = 'Light';
    } else {
      if (icon) icon.textContent = '🌙';
      if (label) label.textContent = 'Dark';
    }
  }
}

// ============ Tab navigation ============

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetPane = $(btn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
      if (btn.dataset.tab === 'tab-jobs') loadJobs();
      if (btn.dataset.tab === 'tab-profiles') loadProfiles();
      if (btn.dataset.tab === 'tab-alerts') loadAlerts();
    });
  });
}

// ============ Stats & Dropdowns ============

async function loadStats() {
  try {
    const d = await req('/api/stats');
    // populate candidate dropdown
    const sel = $('candidate-select');
    if (sel) {
      sel.innerHTML = '<option value="">— or load from database —</option>';
      const profiles = await req('/api/profiles');
      profiles.forEach(p => {
        const opt = document.createElement('option');
        opt.value = JSON.stringify(p);
        opt.textContent = p.name || 'Unknown';
        sel.appendChild(opt);
      });
    }
    // populate role filter
    const roleFilter = $('job-role-filter');
    if (roleFilter) {
      roleFilter.innerHTML = '<option value="">All Roles</option>';
      (d.classes || []).forEach(r => {
        const opt = document.createElement('option');
        opt.value = r; opt.textContent = r;
        roleFilter.appendChild(opt);
      });
    }
  } catch (e) { console.error('Stats error', e); }
}

// ============ Candidate dropdown load ============

function initCandidateDropdown() {
  const sel = $('candidate-select');
  if (!sel) return;
  sel.addEventListener('change', function() {
    if (!this.value) return;
    try {
      const p = JSON.parse(this.value);
      if (p.name) $('candidate-name').value = p.name;
      if (p.skills) $('candidate-skills').value = p.skills;
      if (p.experience !== undefined) {
        $('candidate-experience').value = p.experience;
        $('exp-display').textContent = p.experience + ' year' + (p.experience !== 1 ? 's' : '');
      }
      if (p.bio) $('candidate-bio').value = p.bio;
      if (p.location) $('candidate-location').value = p.location;
    } catch {}
  });
}

// ============ Experience slider ============

function initSlider() {
  const slider = $('candidate-experience');
  const display = $('exp-display');
  if (!slider || !display) return;
  slider.addEventListener('input', () => {
    const v = parseInt(slider.value);
    display.textContent = v + ' year' + (v !== 1 ? 's' : '');
  });
}

// ============ Preset buttons ============

const PRESETS = {
  'preset-ml': {
    name: 'Ananya Iyer', experience: 4, location: 'Bangalore',
    skills: 'Python, TensorFlow, Keras, Scikit-learn, Machine Learning, NLP',
    bio: 'ML researcher with focus on NLP and deep learning.'
  },
  'preset-devops': {
    name: 'Rahul Singh', experience: 5, location: 'Hyderabad',
    skills: 'Docker, Kubernetes, AWS, Terraform, CI/CD, Linux',
    bio: 'Cloud-native DevOps engineer with extensive AWS experience.'
  },
  'preset-fullstack': {
    name: 'Meera Nair', experience: 3, location: 'Pune',
    skills: 'React, Node.js, TypeScript, MongoDB, REST API, HTML, CSS',
    bio: 'Full stack developer building scalable web applications.'
  },
  'preset-data': {
    name: 'Vikram Patel', experience: 2, location: 'Mumbai',
    skills: 'Python, SQL, Pandas, Tableau, Power BI, Data Visualization',
    bio: 'Data analyst with strong skills in business intelligence tools.'
  }
};

function initPresets() {
  Object.keys(PRESETS).forEach(id => {
    const btn = $(id);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const p = PRESETS[id];
      $('candidate-name').value = p.name;
      $('candidate-skills').value = p.skills;
      $('candidate-experience').value = p.experience;
      $('exp-display').textContent = p.experience + ' years';
      $('candidate-bio').value = p.bio;
      $('candidate-location').value = p.location;
      if ($('candidate-select')) $('candidate-select').value = '';
    });
  });
}

// ============ Skill chips ============

function initSkillChips() {
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const skillInput = $('candidate-skills');
      const current = skillInput.value.split(',').map(s => s.trim()).filter(Boolean);
      const skill = chip.dataset.skill;
      if (!current.map(s => s.toLowerCase()).includes(skill.toLowerCase())) {
        current.push(skill);
        skillInput.value = current.join(', ');
      }
    });
  });
}

// ============ Recommender form submit ============

function initRecommendForm() {
  const form = $('recommendation-form');
  const btn = $('btn-predict');
  if (!form || !btn) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    btn.disabled = true;
    btn.textContent = 'Running…';
    $('result-tag').className = 'result-tag loading';
    $('result-tag').textContent = 'Processing…';
    $('result-placeholder').classList.add('hidden');
    $('result-body').classList.add('hidden');

    const payload = {
      name: $('candidate-name').value || 'Candidate',
      skills: $('candidate-skills').value,
      bio: $('candidate-bio').value,
      experience: parseInt($('candidate-experience').value) || 0,
      location: $('candidate-location').value,
      save_notification: true
    };

    try {
      const res = await req('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      renderResult(res, payload);
      loadStats();
    } catch (err) {
      $('result-tag').textContent = 'Error';
      $('result-tag').className = 'result-tag';
      $('result-placeholder').classList.remove('hidden');
      $('result-placeholder').querySelector('p').textContent = 'Failed to connect to server. Is Flask running?';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Run AI Recommendation';
    }
  });
}

function renderResult(res, payload) {
  $('result-body').classList.remove('hidden');
  $('result-placeholder').classList.add('hidden');
  $('result-tag').textContent = 'Matched';
  $('result-tag').className = 'result-tag matched';

  // Role + Confidence
  // Engine returns confidence as fraction 0.0–1.0, so multiply by 100 for display
  const predicted = res.predicted_role || '—';
  const confFrac  = typeof res.confidence === 'number' ? res.confidence : 0;
  const confPct   = Math.min(100, Math.round(confFrac * 100));
  $('predicted-role-title').textContent = predicted;
  $('confidence-val').textContent = confPct + '%';

  // Probability bars (top 5)
  // probabilities dict: {role: fraction} — multiply by 100 for display
  const probContainer = $('prob-bars-container');
  probContainer.innerHTML = '';
  const probs  = res.probabilities || {};
  const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, 5);
  if (sorted.length === 0) {
    probContainer.innerHTML = '<p style="color:var(--text-4);font-size:12px">No probability data returned.</p>';
  }
  sorted.forEach(([label, prob]) => {
    const pct = Math.min(100, Math.round(prob * 100));
    const row = document.createElement('div');
    row.className = 'prob-bar-row';
    row.innerHTML = `
      <div class="prob-bar-label" title="${label}">${label}</div>
      <div class="prob-bar-track"><div class="prob-bar-fill" style="width:${pct}%"></div></div>
      <div class="prob-bar-val">${pct}%</div>`;
    probContainer.appendChild(row);
  });

  // Best matched job
  const job = res.matched_job;
  if (job && Object.keys(job).length > 0) {
    $('jm-title').textContent     = job.title || '—';
    $('jm-company').textContent   = job.company || '—';
    $('jm-location').textContent  = job.location || '—';
    $('jm-exp').textContent       = 'Min ' + (job.experience_required || 0) + ' yrs';
    $('jm-desc').textContent      = job.description || '';

    const reqSkills          = skillList(job.required_skills || '');
    const candidateSkillsRaw = payload.skills || '';
    const candidateSkillsLower = new Set(
      candidateSkillsRaw.split(/[,;]+/).map(s => s.trim().toLowerCase()).filter(Boolean)
    );

    $('jm-req-skills').innerHTML     = tagsHtml(reqSkills, candidateSkillsLower);
    const matchedSkills              = reqSkills.filter(s => candidateSkillsLower.has(s.toLowerCase()));
    $('jm-matched-skills').innerHTML = matchedSkills.length
      ? matchedSkills.map(s => `<span class="sk-tag match">${s}</span>`).join('')
      : '<span style="color: var(--text-4); font-size:12px">No matching skills</span>';

    const badge         = $('jm-badge');
    badge.innerHTML     = `<span class="status-pill unread">${matchedSkills.length}/${reqSkills.length} skills</span>`;

    // ── Inline Candidate Details (visible right on the result card) ──
    const existingDetail = document.getElementById('inline-candidate-detail');
    if (existingDetail) existingDetail.remove();

    const candidateSkillsList = candidateSkillsRaw
      .split(/[,;]+/).map(s => s.trim()).filter(Boolean);

    const inlineDetail = document.createElement('div');
    inlineDetail.id    = 'inline-candidate-detail';
    inlineDetail.className = 'inline-detail-card';
    inlineDetail.innerHTML = `
      <div class="inline-detail-grid">
        <div class="inline-section">
          <div class="section-label">Candidate Summary</div>
          <div class="irow"><span class="ikey">Name</span><span class="ival">${payload.name || '—'}</span></div>
          <div class="irow"><span class="ikey">Location</span><span class="ival">${payload.location || '—'}</span></div>
          <div class="irow"><span class="ikey">Experience</span><span class="ival">${payload.experience || 0} years</span></div>
          <div class="irow"><span class="ikey">Bio</span><span class="ival" style="font-style:italic">${(payload.bio || '—').slice(0, 100)}</span></div>
          <div class="irow"><span class="ikey">Skills</span><div class="sk-tags" style="margin-top:2px">${tagsHtml(candidateSkillsList, new Set(reqSkills.map(s=>s.toLowerCase())))}</div></div>
        </div>
        <div class="inline-section">
          <div class="section-label">Match Quality</div>
          <div class="irow"><span class="ikey">Matched Role</span><span class="ival fw">${predicted}</span></div>
          <div class="irow"><span class="ikey">AI Confidence</span><span class="ival fw" style="color:var(--blue)">${confPct}%</span></div>
          <div class="irow"><span class="ikey">Company</span><span class="ival fw">${job.company || '—'}</span></div>
          <div class="irow"><span class="ikey">Job Location</span><span class="ival">${job.location || '—'}</span></div>
          <div class="irow"><span class="ikey">Skill Match</span><span class="ival fw" style="color:var(--green)">${matchedSkills.length} / ${reqSkills.length}</span></div>
          <div class="irow"><span class="ikey">Exp. Eligible</span><span class="ival">${(payload.experience || 0) >= (job.experience_required || 0)
            ? '✓ Yes (' + (payload.experience||0) + ' ≥ ' + (job.experience_required||0) + ' yrs)'
            : '✗ No (' + (payload.experience||0) + ' < ' + (job.experience_required||0) + ' yrs)'}</span></div>
        </div>
      </div>`;

    // Insert before the matched job section
    const matchSection = $('matched-job-section');
    matchSection.parentNode.insertBefore(inlineDetail, matchSection);

    $('matched-job-section').classList.remove('hidden');
  } else {
    $('matched-job-section').classList.add('hidden');
  }

  // Constraint message
  const msg = $('constraint-msg');
  msg.textContent = res.constraint_message || '';

  // DB saved notice
  const notice = $('db-saved-notice');
  if (res.notification_saved) {
    notice.classList.remove('hidden');
  } else {
    notice.classList.add('hidden');
  }
}

// ============ Jobs tab ============

let allJobs = [];

async function loadJobs() {
  if (allJobs.length === 0) {
    try { allJobs = await req('/api/jobs'); } catch { return; }
  }
  renderJobs(allJobs);
}

function renderJobs(jobs) {
  const grid = $('jobs-grid');
  if (!grid) return;
  if (!jobs.length) { grid.innerHTML = '<p style="color:var(--text-3)">No jobs found.</p>'; return; }
  grid.innerHTML = jobs.map(j => {
    const skills = skillList(j.required_skills || '').slice(0, 6);
    return `<div class="card">
      <div class="card-title">${j.title || '—'}</div>
      <div class="card-sub">${j.company || '—'} · ${j.location || '—'} · Min ${j.experience_required || 0} yrs</div>
      <p style="font-size:12px;color:var(--text-3);line-height:1.5;margin-bottom:6px">${(j.description || '').slice(0, 90)}…</p>
      <div class="card-tags">${cardTagsHtml(skills)}</div>
    </div>`;
  }).join('');
}

function initJobSearch() {
  let debounce;
  const s = $('job-search');
  if (s) {
    s.addEventListener('input', function() {
      clearTimeout(debounce);
      debounce = setTimeout(() => filterJobs(), 200);
    });
  }
  const rf = $('job-role-filter');
  if (rf) rf.addEventListener('change', filterJobs);
}

function filterJobs() {
  const q = ($('job-search') ? $('job-search').value : '').toLowerCase();
  const role = $('job-role-filter') ? $('job-role-filter').value : '';
  const filtered = allJobs.filter(j => {
    const matchQ = !q || [j.title, j.company, j.required_skills, j.location].some(f => (f || '').toLowerCase().includes(q));
    const matchRole = !role || j.title === role;
    return matchQ && matchRole;
  });
  renderJobs(filtered);
}

// ============ Profiles tab ============

let allProfiles = [];

async function loadProfiles() {
  if (allProfiles.length === 0) {
    try { allProfiles = await req('/api/profiles'); } catch { return; }
  }
  renderProfiles(allProfiles);
}

function renderProfiles(profiles) {
  const grid = $('profiles-grid');
  if (!grid) return;
  if (!profiles.length) { grid.innerHTML = '<p style="color:var(--text-3)">No profiles found.</p>'; return; }
  grid.innerHTML = profiles.map(p => {
    const skills = skillList(p.skills || '').slice(0, 6);
    return `<div class="card">
      <div class="card-title">${p.name || '—'}</div>
      <div class="card-sub">${p.location || '—'} · ${p.experience || 0} yr${p.experience !== 1 ? 's' : ''} exp · ${p.email || ''}</div>
      <p style="font-size:12px;color:var(--text-3);line-height:1.5;margin-bottom:6px">${(p.bio || '').slice(0, 90)}…</p>
      <div class="card-tags">${cardTagsHtml(skills)}</div>
    </div>`;
  }).join('');
}

function initProfileSearch() {
  let debounce;
  const s = $('profile-search');
  if (!s) return;
  s.addEventListener('input', function() {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      const q = this.value.toLowerCase();
      renderProfiles(allProfiles.filter(p =>
        [p.name, p.skills, p.location].some(f => (f || '').toLowerCase().includes(q))
      ));
    }, 200);
  });
}

// ============ Alerts (Notifications) tab ============

async function loadAlerts() {
  try {
    const notifs = await req('/api/notifications');
    const table = $('alerts-table');
    const tbody = $('alerts-tbody');
    const empty = $('alerts-empty');
    if (!tbody) return;
    if (!notifs.length) {
      tbody.innerHTML = '';
      if (table) table.classList.add('hidden');
      if (empty) empty.classList.remove('hidden');
      return;
    }
    if (table) table.classList.remove('hidden');
    if (empty) empty.classList.add('hidden');
    tbody.innerHTML = notifs.map((n, i) => `
      <tr data-id="${n._id || ''}"
          data-user="${encodeURIComponent(n.user_name || '')}"
          data-job="${encodeURIComponent(n.job_title || '')}"
          data-company="${encodeURIComponent(n.company || '')}"
          data-job-loc="${encodeURIComponent(n.location || '')}">
        <td>${i + 1}</td>
        <td><strong>${n.user_name || '—'}</strong></td>
        <td><span class="city-pill">${n.candidate_location || '—'}</span></td>
        <td>${n.job_title || '—'}</td>
        <td>${n.company || '—'}</td>
        <td>${n.location || '—'}</td>
        <td><span class="status-pill ${n.status || 'unread'}">${n.status || 'unread'}</span></td>
      </tr>`).join('');

    // Make rows clickable
    tbody.querySelectorAll('tr').forEach(row => {
      row.addEventListener('click', () => openModal(
        decodeURIComponent(row.dataset.user),
        decodeURIComponent(row.dataset.job),
        decodeURIComponent(row.dataset.company),
        decodeURIComponent(row.dataset.jobLoc),
        row.dataset.id
      ));
    });
  } catch (e) {
    console.error('Alerts error', e);
  }
}

function initAlertActions() {
  const batchBtn = $('btn-batch');
  if (batchBtn) {
    batchBtn.addEventListener('click', async () => {
      batchBtn.disabled = true;
      batchBtn.textContent = 'Running batch…';
      try {
        const res = await req('/api/run-batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        batchBtn.textContent = `Done — ${res.processed} processed`;
        await loadAlerts();
        await loadStats();
      } catch (e) {
        console.error(e);
        batchBtn.textContent = 'Batch failed';
      } finally {
        setTimeout(() => {
          batchBtn.disabled = false;
          batchBtn.textContent = 'Run Batch (All 99 Candidates)';
        }, 3000);
      }
    });
  }

  const clearBtn = $('btn-clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', async (e) => {
      if (e) e.preventDefault();
      clearBtn.disabled = true;
      clearBtn.textContent = 'Clearing…';
      try {
        await req('/api/notifications/clear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        clearBtn.textContent = 'Cleared ✓';
        await loadAlerts();
        await loadStats();
      } catch (err) {
        console.error('Clear failed', err);
        clearBtn.textContent = 'Failed to clear';
      } finally {
        setTimeout(() => {
          clearBtn.disabled = false;
          clearBtn.textContent = 'Clear All Alerts';
        }, 1500);
      }
    });
  }
}

// ============ Detail Modal ============

async function openModal(userName, jobTitle, company, jobLocation, notifId) {
  const overlay = $('modal-overlay');
  const body = $('modal-body');
  $('modal-title').textContent = `${userName} → ${jobTitle}`;
  body.innerHTML = '<div class="modal-loading">Loading details…</div>';
  overlay.classList.remove('hidden');

  try {
    const params = new URLSearchParams({
      user_name: userName,
      job_title: jobTitle,
      company: company || '',
      job_location: jobLocation || '',
      notif_id: notifId || ''
    });
    const d = await req(`/api/notification-detail?${params}`);
    body.innerHTML = buildModalHtml(d.profile || {}, d.job || {});
  } catch {
    body.innerHTML = '<div class="modal-loading">Failed to load details.</div>';
  }
}

function buildModalHtml(profile, job) {
  const pSkills = skillList(profile.skills || '');
  const jSkills = skillList(job.required_skills || '');
  const pSkillSet = new Set(pSkills.map(s => s.toLowerCase()));
  const matchedCount = jSkills.filter(s => pSkillSet.has(s.toLowerCase())).length;

  function row(label, val) {
    if (!val && val !== 0) return '';
    return `<div class="modal-row">
      <div class="modal-row-label">${label}</div>
      <div class="modal-row-value">${val}</div>
    </div>`;
  }

  return `
    <div class="modal-grid">
      <div class="modal-section">
        <div class="modal-section-title">Candidate Profile</div>
        ${row('Name', profile.name)}
        ${row('Email', profile.email)}
        ${row('Candidate Location', profile.location)}
        ${row('Experience', profile.experience !== undefined ? profile.experience + ' years' : '')}
        ${row('Bio', profile.bio)}
        <div class="modal-row">
          <div class="modal-row-label">Skills</div>
          <div class="sk-tags" style="margin-top:4px">${tagsHtml(pSkills, new Set(jSkills.map(s => s.toLowerCase())))}</div>
        </div>
      </div>

      <div class="modal-section">
        <div class="modal-section-title">Matched Job</div>
        ${row('Job Title', job.title)}
        ${row('Company', job.company)}
        ${row('Job Location', job.location)}
        ${row('Min Experience', job.experience_required !== undefined ? job.experience_required + ' years' : '')}
        ${row('Description', job.description)}
        <div class="modal-row">
          <div class="modal-row-label">Required Skills</div>
          <div class="sk-tags" style="margin-top:4px">${tagsHtml(jSkills, pSkillSet)}</div>
        </div>
      </div>
    </div>
    <hr class="modal-divider">
    <div style="font-size:13px;color:var(--text-3)">
      <strong style="color:var(--text-1)">${matchedCount} of ${jSkills.length}</strong> required skills matched
      &nbsp;·&nbsp; Candidate has <strong style="color:var(--text-1)">${profile.experience || 0} yr</strong> experience
      &nbsp;·&nbsp; Job requires <strong style="color:var(--text-1)">${job.experience_required || 0} yr</strong>
    </div>`;
}

function initModal() {
  const closeBtn = $('modal-close');
  const overlay = $('modal-overlay');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

function closeModal() {
  const overlay = $('modal-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// ============ Boot ============

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initTabs();
  initSlider();
  initPresets();
  initSkillChips();
  initCandidateDropdown();
  initRecommendForm();
  initJobSearch();
  initProfileSearch();
  initAlertActions();
  initModal();
  loadStats();
});
