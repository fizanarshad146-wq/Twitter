// Global Variables
let postingChart = null;

document.addEventListener('DOMContentLoaded', () => {
  initChart();
  fetchStats();
  fetchAccounts();
  fetchProjects();
  fetchHistory();
  fetchGuide();

  // Poll stats every 3 seconds for live telemetry
  setInterval(fetchStats, 3000);
});

// Tab Navigation
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) {
    targetPane.classList.add('active');
  }

  const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => 
    btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)
  );
  if (activeBtn) {
    activeBtn.classList.add('active');
  }
}

// Chart Initialization
function initChart() {
  const ctx = document.getElementById('postingChart').getContext('2d');
  
  postingChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00'],
      datasets: [{
        label: 'Posts Published',
        data: [0, 0, 0, 0, 0, 0],
        borderColor: '#00f3ff',
        backgroundColor: 'rgba(0, 243, 255, 0.1)',
        borderWidth: 3,
        pointBackgroundColor: '#00f3ff',
        pointBorderColor: '#fff',
        pointRadius: 5,
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#8492a6', font: { family: 'Outfit' } }
        }
      },
      scales: {
        x: {
          ticks: { color: '#8492a6' },
          grid: { color: 'rgba(255, 255, 255, 0.05)' }
        },
        y: {
          ticks: { color: '#8492a6', precision: 0 },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          beginAtZero: true
        }
      }
    }
  });
}

// Fetch Live Stats & Logs
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();

    document.getElementById('stat-remaining').textContent = data.unposted_remaining || 0;
    document.getElementById('stat-posted').textContent = data.posted_total || 0;
    document.getElementById('stat-skipped').textContent = data.campaign?.skipped_duplicates || 0;
    document.getElementById('stat-failed').textContent = data.campaign?.failed || 0;

    const navDot = document.getElementById('nav-status-dot');
    const navText = document.getElementById('nav-status-text');

    if (data.campaign?.is_running) {
      if (data.campaign?.is_paused) {
        navDot.className = 'status-dot paused';
        navText.textContent = 'Engine Paused';
      } else {
        navDot.className = 'status-dot active';
        navText.textContent = `Posting on @${data.campaign?.current_account || 'Multi-Accounts'}...`;
      }
    } else {
      navDot.className = 'status-dot';
      navText.textContent = 'Engine Idle';
    }

    if (data.graph_data && postingChart) {
      postingChart.data.labels = data.graph_data.labels;
      postingChart.data.datasets[0].data = data.graph_data.data;
      postingChart.update();
    }

    if (data.campaign?.logs) {
      renderLogs(data.campaign.logs);
    }

  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

let activeLogCategory = 'all';
let currentLogsCache = [];

function filterLogCategory(cat) {
  activeLogCategory = cat;
  document.querySelectorAll('.log-filter-pill').forEach(pill => pill.classList.remove('active'));
  const activePill = Array.from(document.querySelectorAll('.log-filter-pill')).find(p => p.getAttribute('onclick').includes(cat));
  if (activePill) activePill.classList.add('active');
  renderLogs(currentLogsCache);
}

function renderLogs(logs) {
  currentLogsCache = logs || [];
  const dashboardContainer = document.getElementById('dashboard-logs-container');
  const fullContainer = document.getElementById('full-logs-container');
  
  if (!logs || logs.length === 0) return;

  // Dashboard activity stream: show posting logs
  const postingLogs = logs.filter(log => (log.category === 'posting' || log.category === 'error'));
  const dHtml = (postingLogs.length === 0)
    ? `<div class="log-item info"><span class="msg">No recent posting activity logged yet.</span></div>`
    : postingLogs.slice(0, 50).map(log => `
        <div class="log-item ${log.level}">
          <span class="time">[${log.timestamp.split(' ')[1]}]</span>
          <span class="msg">[${(log.category || 'posting').toUpperCase()}] ${log.message}</span>
        </div>
      `).join('');

  // Full telemetry console: show selected filter category
  const filtered = logs.filter(log => {
    if (activeLogCategory === 'all') return true;
    return (log.category || 'system') === activeLogCategory;
  });

  const fHtml = filtered.length === 0 
    ? `<div class="log-item info"><span class="msg">No logs in category '${activeLogCategory}'.</span></div>`
    : filtered.map(log => `
        <div class="log-item ${log.level}">
          <span class="time">[${log.timestamp.split(' ')[1]}]</span>
          <span class="msg">[${(log.category || 'system').toUpperCase()}] ${log.message}</span>
        </div>
      `).join('');

  if (dashboardContainer) dashboardContainer.innerHTML = dHtml;
  if (fullContainer) fullContainer.innerHTML = fHtml;
}

function copyFilteredLogs() {
  const filtered = currentLogsCache.filter(log => {
    if (activeLogCategory === 'all') return true;
    return (log.category || 'system') === activeLogCategory;
  });
  
  const text = filtered.map(l => `[${l.timestamp}] [${(l.category || 'system').toUpperCase()}] ${l.message}`).join('\n');
  navigator.clipboard.writeText(text).then(() => {
    alert(`📋 Copied ${filtered.length} visible logs to clipboard!`);
  }).catch(() => {
    alert('Failed to copy logs.');
  });
}

function copyAllLogs() {
  const text = currentLogsCache.map(l => `[${l.timestamp}] [${(l.category || 'system').toUpperCase()}] ${l.message}`).join('\n');
  navigator.clipboard.writeText(text).then(() => {
    alert(`📋 Copied all ${currentLogsCache.length} system logs to clipboard!`);
  }).catch(() => {
    alert('Failed to copy logs.');
  });
}

// Fetch Multi-Accounts List
async function fetchAccounts() {
  try {
    const res = await fetch('/api/accounts');
    const accounts = await res.json();

    const tbody = document.getElementById('accounts-table-body');
    if (tbody) {
      if (!accounts || accounts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No Twitter accounts added yet.</td></tr>`;
      } else {
        tbody.innerHTML = accounts.map(acc => `
          <tr>
            <td>
              <strong style="color: var(--cyan-electro);">@${acc.username}</strong>
              <div style="font-size: 0.75rem; color: var(--text-muted);">ID: ${acc.id}</div>
            </td>
            <td>
              <span class="badge ${acc.has_cookies ? 'badge-posted' : 'badge-failed'}">
                ${acc.has_cookies ? '🟢 Active Session' : '🔴 Session Expired'}
              </span>
            </td>
            <td>
              <div style="display: flex; gap: 6px;">
                <button class="btn-electro btn-cyan" style="padding: 5px 12px; font-size: 0.78rem;" onclick="reloginAccount('${acc.id}')">
                  <i class="fa-solid fa-arrows-rotate"></i> Re-login
                </button>
                <button class="btn-electro btn-magenta" style="padding: 5px 12px; font-size: 0.78rem;" onclick="deleteAccount('${acc.id}')">
                  <i class="fa-solid fa-trash"></i> Delete
                </button>
              </div>
            </td>
          </tr>
        `).join('');
      }
    }

    const select = document.getElementById('target-account-select');
    const projSelect = document.getElementById('project-account-select');
    let optionsHtml = `<option value="all">🔄 All Active Accounts (Multi-Rotation)</option>`;
    if (accounts && accounts.length > 0) {
      accounts.forEach(acc => {
        optionsHtml += `<option value="${acc.id}">👤 @${acc.username} ${acc.has_cookies ? '(Active)' : '(No Session)'}</option>`;
      });
    }
    if (select) select.innerHTML = optionsHtml;
    if (projSelect) projSelect.innerHTML = optionsHtml;

  } catch (err) {
    console.error('Error fetching accounts:', err);
  }
}

// Handle 1-Click Interactive Window Login for New Account
async function handleInteractiveLoginAdd() {
  const label = document.getElementById('interactive-label-input').value.trim();
  const statusMsg = document.getElementById('login-status-msg');

  statusMsg.innerHTML = '<span style="color: var(--cyan-electro);">⏳ Launching Twitter login browser window... Look for Chrome/Browser popup on your screen & log in!</span>';

  try {
    const res = await fetch('/api/accounts/add_and_launch_login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: label })
    });
    const result = await res.json();

    if (res.ok) {
      statusMsg.innerHTML = '<span style="color: var(--green-electro);">🌐 Browser window launched on your desktop! Log into your Twitter account in that window. Session will save automatically.</span>';
      
      // Poll accounts list to update DOM automatically when login completes
      let polls = 0;
      const interval = setInterval(async () => {
        polls++;
        await fetchAccounts();
        if (polls > 60) clearInterval(interval);
      }, 3000);
    } else {
      statusMsg.innerHTML = `<span style="color: var(--magenta-electro);">❌ ${result.error}</span>`;
    }
  } catch (err) {
    statusMsg.innerHTML = '<span style="color: var(--magenta-electro);">❌ Network error launching browser window.</span>';
  }
}

// Re-login into existing account
async function reloginAccount(accId) {
  const statusMsg = document.getElementById('login-status-msg');
  if (statusMsg) {
    statusMsg.innerHTML = `<span style="color: var(--cyan-electro);">⏳ Opening Twitter login browser window on your desktop screen... Log in inside that window.</span>`;
  }
  try {
    const res = await fetch(`/api/accounts/relogin/${accId}`, { method: 'POST' });
    if (res.ok) {
      let polls = 0;
      const interval = setInterval(async () => {
        polls++;
        await fetchAccounts();
        if (polls > 60) clearInterval(interval);
      }, 3000);
    }
  } catch (err) {
    alert('Failed to launch 1-Click login window.');
  }
}

// Manual Cookie Add Fallback
async function handleManualCookieAdd() {
  const nameEl = document.getElementById('manual-account-name') || document.getElementById('manual-user-input');
  const cookieEl = document.getElementById('manual-cookie-input');
  
  const username = nameEl ? nameEl.value.trim() : '';
  const cookies = cookieEl ? cookieEl.value.trim() : '';

  if (!cookies) {
    alert('Please paste auth_token string or Cookie JSON.');
    return;
  }

  try {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, cookies: cookies })
    });
    const result = await res.json();

    if (res.ok) {
      alert(`🔑 Account saved and session cookies attached!`);
      if (nameEl) nameEl.value = '';
      if (cookieEl) cookieEl.value = '';
      fetchAccounts();
    } else {
      alert(`Error: ${result.error}`);
    }
  } catch (err) {
    alert('Failed to save manual cookie.');
  }
}

// Delete Account
async function deleteAccount(accId) {
  if (!confirm('Are you sure you want to delete this account?')) return;
  try {
    await fetch(`/api/accounts/${accId}`, { method: 'DELETE' });
    fetchAccounts();
  } catch (err) {
    alert('Failed to delete account.');
  }
}

// Handle Folder Selection
async function handleFolderSelect(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files[]', files[i]);
  }

  const statusMsg = document.getElementById('upload-status-msg');
  statusMsg.textContent = '⏳ Processing and uploading posts folder...';

  try {
    const res = await fetch('/api/upload_folder', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    
    if (res.ok) {
      statusMsg.innerHTML = `✅ ${result.message} (${result.imported} new imported, ${result.duplicates} duplicates skipped)`;
      fetchStats();
      fetchHistory();
    } else {
      statusMsg.textContent = `❌ Upload failed: ${result.error}`;
    }
  } catch (err) {
    statusMsg.textContent = '❌ Network error during folder upload.';
  }
}

// Create Single Text Post
async function createSingleTextPost() {
  const title = document.getElementById('txt-title').value.trim();
  const content = document.getElementById('txt-content').value.trim();

  if (!content) {
    alert('Please enter tweet content.');
    return;
  }

  try {
    const res = await fetch('/api/upload_text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: title || 'tweet', text: content })
    });
    const result = await res.json();

    if (res.ok) {
      alert(`✅ Text post saved as '${result.filename}'`);
      document.getElementById('txt-title').value = '';
      document.getElementById('txt-content').value = '';
      fetchStats();
      fetchHistory();
    } else {
      alert(`Error: ${result.error}`);
    }
  } catch (err) {
    alert('Failed to save text post.');
  }
}

function toggleCustomCaptionInput(mode, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (mode === 'custom') {
    container.style.display = 'block';
  } else {
    container.style.display = 'none';
  }
}

// Campaign Control
async function controlCampaign(action) {
  const delayMin = document.getElementById('delay-min').value;
  const delayMax = document.getElementById('delay-max').value;
  const delayUnit = document.getElementById('delay-unit')?.value || 'sec';
  const captionMode = document.getElementById('caption-mode-select')?.value || 'auto_filename';
  const customCaption = document.getElementById('custom-caption-text')?.value.trim() || '';
  const maxPostsDay = document.getElementById('max-posts-day')?.value || 0;
  const dryRun = document.getElementById('dry-run-checkbox').checked;
  const manualRadio = document.getElementById('mode-manual-radio');
  const headless = manualRadio ? !manualRadio.checked : true;
  const targetAccount = document.getElementById('target-account-select').value;

  try {
    const res = await fetch('/api/campaign/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: action,
        delay_min: delayMin,
        delay_max: delayMax,
        delay_unit: delayUnit,
        caption_mode: captionMode,
        custom_caption: customCaption,
        max_posts_per_day: maxPostsDay,
        dry_run: dryRun,
        headless: headless,
        target_account_id: targetAccount
      })
    });
    const result = await res.json();
    fetchStats();
  } catch (err) {
    console.error('Error controlling campaign:', err);
  }
}

// Projects Management
let cachedProjects = [];

async function fetchProjects() {
  try {
    const res = await fetch('/api/projects');
    cachedProjects = await res.json();

    const launcherSelect = document.getElementById('launcher-project-select');
    if (launcherSelect) {
      let lOptions = `<option value="">-- Use Default Upload Folder --</option>`;
      cachedProjects.forEach(p => {
        lOptions += `<option value="${p.id}">📁 ${p.name} (@${p.account_username})</option>`;
      });
      launcherSelect.innerHTML = lOptions;
    }

    const tbody = document.getElementById('projects-table-body');
    if (!tbody) return;

    if (!cachedProjects || cachedProjects.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No projects created yet. Create one on the left!</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedProjects.map(p => `
      <tr>
        <td>
          <strong style="color: var(--cyan-electro);">${p.name}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);" title="${p.folder_path}">${p.folder_path}</div>
        </td>
        <td><span class="badge badge-posted">@${p.account_username}</span></td>
        <td>
          <span class="badge ${p.posting_mode === 'manual' ? 'badge-warning' : 'badge-posted'}">
            ${p.posting_mode === 'manual' ? '👁️ Visible' : '🙈 Silent'}
          </span>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">Limit: ${p.max_posts_per_day ? p.max_posts_per_day + '/24h' : 'Unlimited'}</div>
        </td>
        <td><strong>${p.remaining_files}</strong> / ${p.total_files} remaining</td>
        <td>
          <div style="display: flex; gap: 4px; flex-wrap: wrap;">
            <button class="btn-electro btn-cyan" style="padding: 4px 8px; font-size: 0.78rem;" onclick="runProjectCampaign('${p.id}')" title="Run Campaign">
              <i class="fa-solid fa-play"></i> Run
            </button>
            <button class="btn-electro btn-outline" style="padding: 4px 8px; font-size: 0.78rem;" onclick="openProjectFolder('${p.id}')" title="Open Folder in File Explorer">
              <i class="fa-solid fa-folder-open"></i> Open
            </button>
            <button class="btn-electro btn-outline" style="padding: 4px 8px; font-size: 0.78rem;" onclick="viewProjectFiles('${p.id}')" title="View Attached Folder Files">
              <i class="fa-solid fa-eye"></i> Files
            </button>
            <button class="btn-electro btn-outline" style="padding: 4px 6px; font-size: 0.78rem;" onclick="triggerProjectUpload('${p.id}')" title="Upload Files to Folder">
              <i class="fa-solid fa-upload"></i>
            </button>
            <button class="btn-electro btn-magenta" style="padding: 4px 6px; font-size: 0.78rem;" onclick="deleteProject('${p.id}')" title="Delete Project">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error fetching projects:', err);
  }
}

async function browseProjectFolder() {
  try {
    const res = await fetch('/api/browse_folder', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.folder_path) {
      document.getElementById('project-folder-input').value = data.folder_path;
      return;
    }
  } catch (err) {
    console.log('Native folder picker unavailable, falling back to Web Folder Picker.');
  }

  // Fallback for Web/Cloud (Render): Trigger HTML5 Folder Picker directly in browser
  let input = document.getElementById('web-folder-picker-input');
  if (!input) {
    input = document.createElement('input');
    input.id = 'web-folder-picker-input';
    input.type = 'file';
    input.webkitdirectory = true;
    input.directory = true;
    input.multiple = true;
    input.style.display = 'none';
    document.body.appendChild(input);
  }

  input.onchange = (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    let folderName = 'Selected_Media_Folder';
    if (files[0] && files[0].webkitRelativePath) {
      folderName = files[0].webkitRelativePath.split('/')[0];
    }

    const folderInput = document.getElementById('project-folder-input');
    const nameInput = document.getElementById('project-name-input');
    if (folderInput) folderInput.value = `[Uploaded Folder] ${folderName}`;
    if (nameInput && !nameInput.value.trim()) nameInput.value = folderName;

    window.selectedProjectFolderFiles = files;
    const statusMsg = document.getElementById('project-status-msg');
    if (statusMsg) {
      statusMsg.innerHTML = `<span style="color: var(--cyan-electro);">📁 Folder "${folderName}" loaded (${files.length} media files ready to save & upload)!</span>`;
    }
  };

  input.click();
}

async function openProjectFolder(projId) {
  try {
    const res = await fetch('/api/open_folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proj_id: projId })
    });
    const data = await res.json();
    if (!res.ok) alert(`Error: ${data.error}`);
  } catch (err) {
    alert('Failed to open File Explorer.');
  }
}

async function viewProjectFiles(projId) {
  try {
    const res = await fetch(`/api/projects/${projId}/files`);
    const data = await res.json();
    if (!res.ok) {
      alert(`Error loading project files: ${data.error}`);
      return;
    }

    document.getElementById('modal-project-title').innerHTML = `<i class="fa-solid fa-folder-open"></i> ${data.project_name} - Attached Folder`;
    document.getElementById('modal-project-path').textContent = `Location: ${data.folder_path}`;

    const tbody = document.getElementById('modal-files-table-body');
    if (!data.files || data.files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No media or text files found in attached folder.</td></tr>`;
    } else {
      tbody.innerHTML = data.files.map(f => `
        <tr>
          <td><strong style="color: #fff;">${f.filename}</strong></td>
          <td><span class="badge badge-cyan">${f.ftype.toUpperCase()}</span></td>
          <td>${f.size_kb} KB</td>
          <td><span class="badge ${f.is_posted ? 'badge-posted' : 'badge-warning'}">${f.status}</span></td>
          <td>
            <button class="btn-electro btn-magenta" style="padding: 3px 8px; font-size: 0.75rem;" onclick="deleteProjectFile('${projId}', '${encodeURIComponent(f.filename)}')">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </td>
        </tr>
      `).join('');
    }

    document.getElementById('project-files-modal').style.display = 'flex';
  } catch (err) {
    alert('Failed to view project files.');
  }
}

function closeProjectFilesModal() {
  document.getElementById('project-files-modal').style.display = 'none';
}

async function deleteProjectFile(projId, encodedFilename) {
  if (!confirm('Are you sure you want to delete this file from the project folder?')) return;
  try {
    const res = await fetch(`/api/projects/${projId}/files/${encodedFilename}`, { method: 'DELETE' });
    if (res.ok) {
      viewProjectFiles(projId);
      fetchProjects();
    } else {
      const data = await res.json();
      alert(`Error deleting file: ${data.error}`);
    }
  } catch (err) {
    alert('Failed to delete file.');
  }
}

async function saveProject() {
  const name = document.getElementById('project-name-input').value.trim();
  const accId = document.getElementById('project-account-select').value;
  const folderPath = document.getElementById('project-folder-input').value.trim();
  const postingMode = document.getElementById('project-mode-select').value;
  const delayMin = document.getElementById('project-delay-min').value;
  const delayMax = document.getElementById('project-delay-max').value;
  const delayUnit = document.getElementById('project-delay-unit')?.value || 'sec';
  const captionMode = document.getElementById('project-caption-mode-select')?.value || 'auto_filename';
  const customCaption = document.getElementById('project-custom-caption-text')?.value.trim() || '';
  const maxPostsDay = document.getElementById('project-max-posts-day')?.value || 0;
  const projId = document.getElementById('project-id-input').value;
  const statusMsg = document.getElementById('project-status-msg');

  if (!name) {
    alert('Please enter a Project Name.');
    return;
  }

  try {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: projId,
        name: name,
        account_id: accId,
        folder_path: folderPath,
        posting_mode: postingMode,
        delay_min: delayMin,
        delay_max: delayMax,
        delay_unit: delayUnit,
        caption_mode: captionMode,
        custom_caption: customCaption,
        max_posts_per_day: maxPostsDay
      })
    });
    const result = await res.json();
    if (res.ok) {
      const savedProjId = result.id || (result.project && result.project.id);
      if (window.selectedProjectFolderFiles && window.selectedProjectFolderFiles.length > 0 && savedProjId) {
        statusMsg.innerHTML = `<span style="color: var(--cyan-electro);">⏳ Uploading ${window.selectedProjectFolderFiles.length} media files to project...</span>`;
        const formData = new FormData();
        for (let i = 0; i < window.selectedProjectFolderFiles.length; i++) {
          formData.append('files[]', window.selectedProjectFolderFiles[i]);
        }
        await fetch(`/api/projects/${savedProjId}/upload`, { method: 'POST', body: formData });
        window.selectedProjectFolderFiles = null;
      }

      statusMsg.innerHTML = `<span style="color: var(--green-electro);">✅ Project saved & folder files synced successfully!</span>`;
      document.getElementById('project-name-input').value = '';
      document.getElementById('project-folder-input').value = '';
      document.getElementById('project-id-input').value = '';
      fetchProjects();
    } else {
      statusMsg.innerHTML = `<span style="color: var(--magenta-electro);">❌ ${result.error}</span>`;
    }
  } catch (err) {
    statusMsg.innerHTML = `<span style="color: var(--magenta-electro);">❌ Failed to save project.</span>`;
  }
}

async function deleteProject(projId) {
  if (!confirm('Are you sure you want to delete this project?')) return;
  try {
    await fetch(`/api/projects/${projId}`, { method: 'DELETE' });
    fetchProjects();
  } catch (err) {
    alert('Failed to delete project.');
  }
}

async function runProjectCampaign(projId) {
  try {
    const res = await fetch(`/api/projects/${projId}/run`, { method: 'POST' });
    const result = await res.json();
    if (res.ok) {
      alert(`🚀 Campaign started for project!`);
      switchTab('dashboard');
      fetchStats();
    } else {
      alert(`Error starting project campaign: ${result.error}`);
    }
  } catch (err) {
    alert('Failed to start project campaign.');
  }
}

function handleLauncherProjectSelect(projId) {
  if (!projId) return;
  const proj = cachedProjects.find(p => p.id === projId);
  if (!proj) return;

  if (proj.account_id) {
    document.getElementById('target-account-select').value = proj.account_id;
  }
  if (proj.delay_min) document.getElementById('delay-min').value = proj.delay_min;
  if (proj.delay_max) document.getElementById('delay-max').value = proj.delay_max;
  if (proj.delay_unit && document.getElementById('delay-unit')) {
    document.getElementById('delay-unit').value = proj.delay_unit;
  }
  if (proj.caption_mode && document.getElementById('caption-mode-select')) {
    document.getElementById('caption-mode-select').value = proj.caption_mode;
    toggleCustomCaptionInput(proj.caption_mode, 'custom-caption-container');
  }
  if (proj.custom_caption && document.getElementById('custom-caption-text')) {
    document.getElementById('custom-caption-text').value = proj.custom_caption;
  }

  if (proj.posting_mode === 'manual') {
    const manualRadio = document.getElementById('mode-manual-radio');
    if (manualRadio) manualRadio.checked = true;
  } else {
    const silentRadio = document.getElementById('mode-silent-radio');
    if (silentRadio) silentRadio.checked = true;
  }
}

function triggerProjectUpload(projId) {
  const input = document.createElement('input');
  input.type = 'file';
  input.webkitdirectory = true;
  input.multiple = true;
  input.onchange = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files[]', files[i]);
    }
    try {
      const res = await fetch(`/api/projects/${projId}/upload`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        alert(`✅ Uploaded ${data.imported} files to project!`);
        fetchProjects();
      } else {
        alert(`Upload error: ${data.error}`);
      }
    } catch (err) {
      alert('Network error during project upload.');
    }
  };
  input.click();
}

// Clear Upload Folder
async function clearUploadFolder() {
  if (!confirm('Are you sure you want to clear all pending files from the queue folder?')) return;

  try {
    const res = await fetch('/api/clear_folder', { method: 'DELETE' });
    const data = await res.json();
    alert(`🗑️ ${data.message}`);
    fetchHistory();
    fetchStats();
  } catch (err) {
    alert('Failed to clear folder.');
  }
}

// Clear History Logs
async function clearHistoryLogs() {
  if (!confirm('Are you sure you want to clear completed posting history logs?')) return;
  try {
    const res = await fetch('/api/history', { method: 'DELETE' });
    const data = await res.json();
    alert(`🧹 ${data.message}`);
    fetchHistory();
    fetchStats();
  } catch (err) {
    alert('Failed to clear history.');
  }
}

// Clear All (History Logs + Queue Folder Files)
async function clearAllLogsAndQueue() {
  if (!confirm('Are you sure you want to clear BOTH posting history AND all queue folder files?')) return;
  try {
    const res = await fetch('/api/clear_all', { method: 'DELETE' });
    const data = await res.json();
    alert(`🧹 ${data.message}`);
    fetchHistory();
    fetchStats();
  } catch (err) {
    alert('Failed to clear history and queue.');
  }
}

// History & Queue Logs
let currentHistoryCache = [];
let currentQueueCache = [];
let activeHistoryFilter = 'all';

function filterHistoryStatus(status) {
  activeHistoryFilter = status;
  document.querySelectorAll('#tab-history .log-filter-pill').forEach(pill => pill.classList.remove('active'));
  const btn = document.getElementById(`history-filter-${status}`);
  if (btn) btn.classList.add('active');
  renderHistoryTable();
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    if (data.history) {
      currentHistoryCache = data.history || [];
      currentQueueCache = data.queue || [];
    } else if (Array.isArray(data)) {
      currentHistoryCache = data;
      currentQueueCache = [];
    }
    renderHistoryTable();
  } catch (err) {
    console.error('Error fetching history & queue:', err);
  }
}

function renderHistoryTable() {
  const tbody = document.getElementById('history-table-body');
  if (!tbody) return;

  let combined = [];

  if (activeHistoryFilter === 'all' || activeHistoryFilter === 'queued') {
    combined = combined.concat(currentQueueCache);
  }
  if (activeHistoryFilter === 'all' || activeHistoryFilter === 'posted' || activeHistoryFilter === 'failed') {
    const filteredHistory = currentHistoryCache.filter(item => {
      if (activeHistoryFilter === 'all') return true;
      return item.status === activeHistoryFilter;
    });
    combined = combined.concat(filteredHistory.slice().reverse());
  }

  if (!combined || combined.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No items matching filter '${activeHistoryFilter}'.</td></tr>`;
    return;
  }

  tbody.innerHTML = combined.map(item => {
    let badgeClass = 'badge-warning';
    let statusText = item.status;
    if (item.status === 'posted') {
      badgeClass = 'badge-posted';
      statusText = '✅ Posted';
    } else if (item.status === 'failed') {
      badgeClass = 'badge-failed';
      statusText = '❌ Failed';
    } else if (item.status === 'queued') {
      badgeClass = 'badge-cyan';
      statusText = '⏳ Queued';
    }

    const actionCol = item.status === 'queued'
      ? `<button class="btn-electro btn-magenta" style="padding: 2px 8px; font-size: 0.72rem; margin-left: 6px;" onclick="deleteQueuedFile('${encodeURIComponent(item.filename)}')"><i class="fa-solid fa-trash"></i> Remove</button>`
      : '';

    return `
      <tr>
        <td><strong>${item.filename}</strong></td>
        <td>${item.account || 'Multi-Account'}</td>
        <td>${item.timestamp}</td>
        <td>
          <span class="badge ${badgeClass}">${statusText}</span>
        </td>
        <td>${item.message} ${actionCol}</td>
      </tr>
    `;
  }).join('');
}

async function deleteQueuedFile(encodedFilename) {
  if (!confirm('Are you sure you want to remove this file from the queue folder?')) return;
  try {
    const res = await fetch(`/api/queue/${encodedFilename}`, { method: 'DELETE' });
    if (res.ok) {
      fetchHistory();
      fetchStats();
    } else {
      const data = await res.json();
      alert(`Error removing file: ${data.error}`);
    }
  } catch (err) {
    alert('Failed to remove queued file.');
  }
}

// User Guide Management (Editable)
let cachedGuideSteps = [];

async function fetchGuide() {
  try {
    const res = await fetch('/api/guide');
    cachedGuideSteps = await res.json();
    renderGuideView(cachedGuideSteps);
  } catch (err) {
    console.error('Error fetching guide:', err);
  }
}

function renderGuideView(steps) {
  const container = document.getElementById('guide-steps-container');
  if (!container) return;

  if (!steps || steps.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); text-align: center;">No guide steps configured. Click 'Edit Guide' to add steps!</p>`;
    return;
  }

  container.innerHTML = steps.map((step, idx) => `
    <div class="guide-step">
      <div class="step-num">${step.num || (idx + 1)}</div>
      <div class="step-content">
        <h3>${step.title || 'Step'}</h3>
        <div>${step.content || ''}</div>
      </div>
    </div>
  `).join('');
}

function toggleEditGuideMode(showEdit) {
  const viewContainer = document.getElementById('guide-steps-container');
  const editContainer = document.getElementById('guide-edit-container');

  if (showEdit) {
    populateGuideEditor(cachedGuideSteps);
    if (viewContainer) viewContainer.style.display = 'none';
    if (editContainer) editContainer.style.display = 'block';
  } else {
    if (editContainer) editContainer.style.display = 'none';
    if (viewContainer) viewContainer.style.display = 'block';
  }
}

function populateGuideEditor(steps) {
  const list = document.getElementById('guide-steps-editor-list');
  if (!list) return;
  list.innerHTML = '';
  (steps || []).forEach((step, idx) => {
    addGuideStepEditorRow(step.num || (idx + 1), step.title || '', step.content || '');
  });
}

function addGuideStepEditorRow(num = '', title = '', content = '') {
  const list = document.getElementById('guide-steps-editor-list');
  if (!list) return;

  const count = list.children.length + 1;
  const rowNum = num || count;

  const card = document.createElement('div');
  card.className = 'guide-editor-row';
  card.style.background = 'rgba(15, 20, 38, 0.9)';
  card.style.padding = '12px';
  card.style.borderRadius = '8px';
  card.style.border = '1px solid var(--border-neon)';

  card.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <span style="color: var(--cyan-electro); font-weight: 700;">Step ${rowNum}</span>
      <button type="button" class="btn-electro btn-magenta" style="padding: 2px 8px; font-size: 0.72rem;" onclick="this.closest('.guide-editor-row').remove()">
        <i class="fa-solid fa-trash"></i> Remove
      </button>
    </div>
    <div class="form-group" style="margin-bottom: 8px;">
      <label style="font-size: 0.78rem;">Step Title</label>
      <input type="text" class="input-electro guide-edit-title" value="${title.replace(/"/g, '&quot;')}" placeholder="Step Title">
    </div>
    <div class="form-group" style="margin-bottom: 0;">
      <label style="font-size: 0.78rem;">Step Description / Content (HTML/Text)</label>
      <textarea class="input-electro guide-edit-content" rows="3" placeholder="Step instructions content...">${content}</textarea>
    </div>
  `;

  list.appendChild(card);
}

async function saveEditedGuide() {
  const rows = document.querySelectorAll('#guide-steps-editor-list .guide-editor-row');
  const updatedSteps = [];

  rows.forEach((row, idx) => {
    const title = row.querySelector('.guide-edit-title').value.trim();
    const content = row.querySelector('.guide-edit-content').value.trim();
    if (title || content) {
      updatedSteps.push({
        num: idx + 1,
        title: title || `Step ${idx + 1}`,
        content: content
      });
    }
  });

  try {
    const res = await fetch('/api/guide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedSteps)
    });
    const result = await res.json();
    if (res.ok) {
      alert('✅ User Guide updated successfully!');
      cachedGuideSteps = result.guide || updatedSteps;
      renderGuideView(cachedGuideSteps);
      toggleEditGuideMode(false);
    } else {
      alert(`Error saving guide: ${result.error}`);
    }
  } catch (err) {
    alert('Failed to save guide.');
  }
}

async function resetGuideToDefault() {
  if (!confirm('Are you sure you want to reset the User Guide to default system instructions?')) return;
  try {
    const res = await fetch('/api/guide/reset', { method: 'POST' });
    const result = await res.json();
    if (res.ok) {
      alert('🔄 User Guide reset to default instructions!');
      cachedGuideSteps = result.guide;
      renderGuideView(cachedGuideSteps);
      toggleEditGuideMode(false);
    }
  } catch (err) {
    alert('Failed to reset guide.');
  }
}
