// ==========================================================
// JobMatch AI • Frontend Application Logic
// ==========================================================

document.addEventListener('DOMContentLoaded', () => {
  // Global State
  let allJobs = [];
  let allProfiles = [];
  let allNotifications = [];
  let statsData = {};

  // DOM Elements
  const tabs = document.querySelectorAll('.nav-tab');
  const tabContents = document.querySelectorAll('.tab-content');

  const expRange = document.getElementById('candidate-experience');
  const expDisplay = document.getElementById('exp-val-display');

  const candidateSelect = document.getElementById('candidate-select');
  const form = document.getElementById('recommendation-form');
  const btnPredict = document.getElementById('btn-predict');

  const resultPlaceholder = document.getElementById('result-placeholder');
  const resultBody = document.getElementById('result-body');
  const resultStatusBadge = document.getElementById('result-status-badge');

  // Tab Switching
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetTabId = tab.getAttribute('data-tab');
      const targetContent = document.getElementById(targetTabId);
      if (targetContent) {
        targetContent.classList.add('active');
      }

      // Refresh specific tab data on switch
      if (targetTabId === 'tab-notifications') {
        loadNotifications();
      } else if (targetTabId === 'tab-jobs') {
        loadJobs();
      } else if (targetTabId === 'tab-profiles') {
        loadProfiles();
      }
    });
  });

  // Experience Slider Display
  if (expRange && expDisplay) {
    expRange.addEventListener('input', (e) => {
      const val = e.target.value;
      expDisplay.textContent = `${val} Year${val === '1' ? '' : 's'}`;
    });
  }

  // Quick Preset Handlers
  document.getElementById('preset-ml')?.addEventListener('click', () => {
    document.getElementById('candidate-name').value = 'Dr. Priya Sharma';
    document.getElementById('candidate-skills').value = 'Python, ML, TensorFlow, Keras, Data Science';
    document.getElementById('candidate-experience').value = 4;
    expDisplay.textContent = '4 Years';
    document.getElementById('candidate-location').value = 'Hyderabad';
    document.getElementById('candidate-bio').value = 'Senior machine learning practitioner experienced with deep neural networks and NLP architectures.';
    triggerRecommend();
  });

  document.getElementById('preset-devops')?.addEventListener('click', () => {
    document.getElementById('candidate-name').value = 'Rohan Verma';
    document.getElementById('candidate-skills').value = 'AWS, Azure, Docker, Linux, Kubernetes, Python';
    document.getElementById('candidate-experience').value = 5;
    expDisplay.textContent = '5 Years';
    document.getElementById('candidate-location').value = 'Pune';
    document.getElementById('candidate-bio').value = 'DevOps specialist focused on automated CI/CD pipelines, cloud orchestration, and high availability systems.';
    triggerRecommend();
  });

  document.getElementById('preset-fullstack')?.addEventListener('click', () => {
    document.getElementById('candidate-name').value = 'Aarav Mehta';
    document.getElementById('candidate-skills').value = 'React, Node.js, JavaScript, MongoDB, Express';
    document.getElementById('candidate-experience').value = 2;
    expDisplay.textContent = '2 Years';
    document.getElementById('candidate-location').value = 'Bangalore';
    document.getElementById('candidate-bio').value = 'Full-stack engineer passionate about responsive user interfaces, RESTful microservices, and modern web frameworks.';
    triggerRecommend();
  });

  // Clickable Skill Suggestion Tags
  document.querySelectorAll('.add-skill-tag').forEach(btn => {
    btn.addEventListener('click', () => {
      const skill = btn.getAttribute('data-skill');
      const input = document.getElementById('candidate-skills');
      const current = input.value.trim();
      if (!current) {
        input.value = skill;
      } else if (!current.toLowerCase().includes(skill.toLowerCase())) {
        input.value = `${current}, ${skill}`;
      }
    });
  });

  // Load Initial Data
  loadStats();
  loadCandidateDropdown();
  loadJobs();
  loadProfiles();
  loadNotifications();

  // Load Stats from API
  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      statsData = await res.json();

      document.getElementById('count-jobs-badge').textContent = statsData.total_jobs || '99';
      document.getElementById('count-profiles-badge').textContent = statsData.total_profiles || '99';
      document.getElementById('count-notifications-badge').textContent = statsData.total_notifications || '0';

      // Populate Role Filter Dropdown in Catalog
      const roleFilter = document.getElementById('job-role-filter');
      if (roleFilter && statsData.classes) {
        roleFilter.innerHTML = '<option value="">All Job Roles</option>';
        statsData.classes.forEach(cls => {
          const opt = document.createElement('option');
          opt.value = cls;
          opt.textContent = cls;
          roleFilter.appendChild(opt);
        });
      }

      // Populate Theory Stats List
      const skillsList = document.getElementById('stats-skills-list');
      if (skillsList && statsData.top_skills) {
        skillsList.innerHTML = statsData.top_skills.map(s => `
          <div class="stat-item">
            <span><strong>${s.skill}</strong> in job postings</span>
            <span class="code-pill">${s.count} mentions</span>
          </div>
        `).join('');
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }

  // Populate Candidate Select Dropdown
  async function loadCandidateDropdown() {
    try {
      const res = await fetch('/api/profiles');
      allProfiles = await res.json();

      if (candidateSelect) {
        candidateSelect.innerHTML = '<option value="">-- Load from MongoDB Profiles --</option>';
        allProfiles.forEach((p, idx) => {
          const opt = document.createElement('option');
          opt.value = idx;
          opt.textContent = `${p.name} (${p.experience || 0} yrs exp • ${p.skills || 'No skills'})`;
          candidateSelect.appendChild(opt);
        });

        candidateSelect.addEventListener('change', (e) => {
          const idx = e.target.value;
          if (idx !== '') {
            const p = allProfiles[idx];
            document.getElementById('candidate-name').value = p.name || '';
            document.getElementById('candidate-skills').value = p.skills || '';
            const exp = p.experience || 0;
            document.getElementById('candidate-experience').value = exp;
            expDisplay.textContent = `${exp} Year${exp === 1 ? '' : 's'}`;
            document.getElementById('candidate-location').value = p.location || '';
            document.getElementById('candidate-bio').value = p.bio || '';
            triggerRecommend();
          }
        });
      }
    } catch (err) {
      console.error('Error loading profiles:', err);
    }
  }

  // Handle Form Submission
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    triggerRecommend();
  });

  async function triggerRecommend() {
    const name = document.getElementById('candidate-name').value.trim();
    const skills = document.getElementById('candidate-skills').value.trim();
    const exp = parseInt(document.getElementById('candidate-experience').value || 0);
    const bio = document.getElementById('candidate-bio').value.trim();
    const location = document.getElementById('candidate-location').value.trim();

    if (!skills && !bio) {
      alert('Please provide candidate skills or a bio.');
      return;
    }

    // Set UI Loading State
    btnPredict.disabled = true;
    btnPredict.innerHTML = '<span class="status-dot"></span> <span>Classifying via Naive Bayes...</span>';
    resultStatusBadge.textContent = 'Processing Model...';

    try {
      const startTime = performance.now();
      const res = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          skills: skills,
          experience: exp,
          bio: bio,
          location: location,
          save_notification: true
        })
      });

      const data = await res.json();
      const endTime = performance.now();
      document.getElementById('result-exec-time').textContent = `${Math.round(endTime - startTime)}ms`;

      renderRecommendationResult(data, exp, skills);
      loadStats(); // Update notification counts
    } catch (err) {
      console.error('Recommendation failed:', err);
      alert('Failed to connect to recommendation server.');
    } finally {
      btnPredict.disabled = false;
      btnPredict.innerHTML = '<span class="btn-icon">⚡</span> <span>Run AI Recommendation</span>';
    }
  }

  // Render Recommendation Results
  function renderRecommendationResult(data, userExp, userSkillsRaw) {
    if (!data.success) {
      alert(data.error || 'No recommendation available');
      return;
    }

    resultPlaceholder.classList.add('hidden');
    resultBody.classList.remove('hidden');
    resultStatusBadge.textContent = 'Recommendation Generated';

    // 1. Predicted Role Banner
    document.getElementById('predicted-role-title').textContent = data.predicted_role;
    document.getElementById('confidence-val').textContent = `${Math.round(data.confidence)}%`;

    // 2. Probability Distribution Bars
    const probContainer = document.getElementById('prob-bars-container');
    if (probContainer && data.top_predictions) {
      probContainer.innerHTML = data.top_predictions.map(p => `
        <div class="prob-bar-row">
          <div class="prob-bar-label">
            <span>${p.title}</span>
            <span><strong>${p.confidence}%</strong></span>
          </div>
          <div class="prob-bar-track">
            <div class="prob-bar-fill" style="width: ${Math.max(p.confidence, 4)}%;"></div>
          </div>
        </div>
      `).join('');
    }

    // 3. Best Matched Job Card & Constraint Check
    const spotlight = data.best_match;
    const qualContainer = document.getElementById('qualification-badge-container');
    const alertBox = document.getElementById('constraint-alert');

    if (spotlight) {
      document.getElementById('spotlight-title').textContent = spotlight.title;
      document.getElementById('spotlight-company').textContent = `🏢 ${spotlight.company}`;
      document.getElementById('spotlight-location').textContent = `📍 ${spotlight.location}`;
      document.getElementById('spotlight-exp').textContent = `⏳ Min Experience: ${spotlight.experience_required} yrs`;
      document.getElementById('spotlight-desc').textContent = spotlight.description;

      // Required Skills Pills
      const reqSkillsDiv = document.getElementById('spotlight-req-skills');
      const reqSkillsArr = (spotlight.required_skills || '').split(',').map(s => s.trim()).filter(Boolean);
      reqSkillsDiv.innerHTML = reqSkillsArr.map(s => `<span class="skill-pill">${s}</span>`).join('');

      // Matched Skills Pills
      const matchedSkillsDiv = document.getElementById('spotlight-matched-skills');
      if (spotlight.matched_skills && spotlight.matched_skills.length > 0) {
        matchedSkillsDiv.innerHTML = spotlight.matched_skills.map(s => `<span class="skill-pill matched">✓ ${s.toUpperCase()}</span>`).join('');
      } else {
        matchedSkillsDiv.innerHTML = '<span class="text-dim">Overall role similarity match via TF-IDF</span>';
      }

      // Constraint verification
      qualContainer.innerHTML = `<span class="badge-qualified">✓ Qualified Candidate</span>`;
      alertBox.className = 'constraint-alert qualified';
      alertBox.innerHTML = `
        <span>✅</span>
        <div>
          <strong>Experience Constraint Passed:</strong>
          Candidate has <strong>${userExp} years</strong> experience, which satisfies the required <strong>${spotlight.experience_required} years</strong>.
        </div>
      `;
    } else {
      // Experience conflict
      document.getElementById('spotlight-title').textContent = `${data.predicted_role} (Position Found)`;
      document.getElementById('spotlight-company').textContent = 'Multiple Companies';
      document.getElementById('spotlight-location').textContent = 'Various Locations';
      document.getElementById('spotlight-exp').textContent = 'Requirements Not Met';
      document.getElementById('spotlight-desc').textContent = 'The AI model matched your technical skill profile with this job title, but all currently open listings require higher years of experience than the candidate currently holds.';

      qualContainer.innerHTML = `<span class="badge-unqualified">⚠️ Experience Mismatch</span>`;
      alertBox.className = 'constraint-alert unqualified';
      alertBox.innerHTML = `
        <span>⚠️</span>
        <div>
          <strong>Constraint Rule Check:</strong>
          Candidate has <strong>${userExp} years</strong>. All available ${data.predicted_role} positions in MongoDB require higher experience. (Post-filtering applied).
        </div>
      `;
      document.getElementById('spotlight-req-skills').innerHTML = '<span class="text-dim">N/A</span>';
      document.getElementById('spotlight-matched-skills').innerHTML = '<span class="text-dim">N/A</span>';
    }

    // 4. Notification Alert Box
    const notifAlert = document.getElementById('db-notification-alert');
    if (data.notification_saved) {
      notifAlert.classList.remove('hidden');
    } else {
      notifAlert.classList.add('hidden');
    }
  }

  // Load and Render Jobs
  async function loadJobs() {
    const container = document.getElementById('jobs-cards-container');
    if (!container) return;

    const query = document.getElementById('job-search-input')?.value.trim() || '';
    const role = document.getElementById('job-role-filter')?.value.trim() || '';

    let url = `/api/jobs?q=${encodeURIComponent(query)}`;
    if (role) url += `&role=${encodeURIComponent(role)}`;

    try {
      const res = await fetch(url);
      allJobs = await res.json();

      container.innerHTML = allJobs.map(job => {
        const skills = (job.required_skills || '').split(',').map(s => `<span class="skill-pill">${s.trim()}</span>`).join('');
        return `
          <div class="job-card">
            <div>
              <div class="job-card-top">
                <span class="company-badge">${job.company}</span>
                <span class="exp-badge">Min ${job.experience_required} yrs</span>
              </div>
              <h3 class="job-card-title">${job.title}</h3>
              <p class="job-card-desc">${job.description}</p>
            </div>
            <div class="job-card-footer">
              <span class="meta-item">📍 ${job.location}</span>
              <div class="skill-tags-group">${skills}</div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      console.error('Error fetching jobs:', err);
    }
  }

  document.getElementById('job-search-input')?.addEventListener('input', debounce(loadJobs, 300));
  document.getElementById('job-role-filter')?.addEventListener('change', loadJobs);

  // Load and Render Profiles
  async function loadProfiles() {
    const container = document.getElementById('profiles-cards-container');
    if (!container) return;

    const query = document.getElementById('profile-search-input')?.value.trim() || '';
    try {
      const res = await fetch(`/api/profiles?q=${encodeURIComponent(query)}`);
      const profiles = await res.json();

      container.innerHTML = profiles.map((p, idx) => {
        const skills = (p.skills || '').split(',').map(s => `<span class="skill-pill">${s.trim()}</span>`).join('');
        return `
          <div class="profile-card">
            <div>
              <div class="profile-card-top">
                <span class="company-badge">Candidate #${idx + 1}</span>
                <span class="exp-badge">${p.experience || 0} yrs exp</span>
              </div>
              <h3 class="profile-card-title">${p.name}</h3>
              <p class="profile-card-bio">${p.bio || 'No bio provided.'}</p>
            </div>
            <div class="profile-card-footer">
              <span class="meta-item">📍 ${p.location || 'Remote'}</span>
              <button class="btn-card-action" onclick="window.pickProfile(${idx})">🎯 Test Match</button>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      console.error('Error fetching profiles:', err);
    }
  }

  document.getElementById('profile-search-input')?.addEventListener('input', debounce(loadProfiles, 300));

  // Quick helper to select candidate from profile card
  window.pickProfile = function(idx) {
    if (candidateSelect) {
      candidateSelect.value = idx;
      candidateSelect.dispatchEvent(new Event('change'));
      // Switch to Recommender Tab
      document.getElementById('tab-btn-recommender')?.click();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Load and Render Notifications
  async function loadNotifications() {
    const container = document.getElementById('notifications-list-container');
    if (!container) return;

    try {
      const res = await fetch('/api/notifications');
      allNotifications = await res.json();

      if (allNotifications.length === 0) {
        container.innerHTML = `
          <div class="result-placeholder">
            <div class="placeholder-icon">📭</div>
            <h4>No Notifications Yet</h4>
            <p>Run a live recommendation above or click <strong>"Run Batch for All 99 Candidates"</strong> to populate MongoDB notifications.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = allNotifications.map((notif, idx) => `
        <div class="notification-item">
          <div>
            <div class="notif-user">${notif.user_name}</div>
            <div class="notif-role">🎯 Recommended: <strong>${notif.job_title}</strong> at ${notif.company}</div>
            <div class="notif-company">📍 Location: ${notif.location} • Status: <span class="badge badge-outline">${notif.status}</span></div>
          </div>
          <span class="code-pill">Notification #${allNotifications.length - idx}</span>
        </div>
      `).join('');
    } catch (err) {
      console.error('Error fetching notifications:', err);
    }
  }

  // Clear Notifications
  document.getElementById('btn-clear-notifications')?.addEventListener('click', async () => {
    if (confirm('Are you sure you want to clear all MongoDB notifications?')) {
      try {
        await fetch('/api/notifications/clear', { method: 'POST' });
        loadNotifications();
        loadStats();
      } catch (err) {
        console.error('Error clearing notifications:', err);
      }
    }
  });

  // Batch Evaluation on all 99 Candidates
  document.getElementById('btn-batch-eval')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-batch-eval');
    btn.disabled = true;
    btn.innerHTML = '<span class="status-dot"></span> <span>Running batch matching...</span>';

    try {
      const res = await fetch('/api/run-batch', { method: 'POST' });
      const data = await res.json();
      alert(`🎉 Batch complete! Successfully evaluated ${data.processed} candidates and saved matching notifications to MongoDB.`);
      loadNotifications();
      loadStats();
    } catch (err) {
      console.error('Batch error:', err);
      alert('Error running batch evaluation.');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>🚀 Run Batch for All 99 Candidates</span>';
    }
  });

  // Utility: Debounce function for smooth search
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
});
