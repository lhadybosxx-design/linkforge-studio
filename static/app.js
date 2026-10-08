const API = '';

function render(targetId, html) {
  document.getElementById(targetId).innerHTML = html;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

// ---------- Analyze Repo ----------
document.getElementById('analyzeBtn').addEventListener('click', async () => {
  const repoUrl = document.getElementById('repoUrl').value.trim();
  if (!repoUrl) return alert('Enter a repo URL');
  render('analyzeResult', '<div class="result">Cloning & analyzing...</div>');

  try {
    const r = await fetch(`${API}/api/analyze-repo`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({repo_url: repoUrl})
    });
    const data = await r.json();
    if (data.error) return render('analyzeResult', `<div class="result err">${escapeHtml(data.error)}</div>`);

    const kws = (data.top_keywords || []).map(k => `<span class="badge">${escapeHtml(k)}</span>`).join('');
    render('analyzeResult', `
      <div class="result">
        <div><strong>Category:</strong> <span class="badge">${escapeHtml(data.category)}</span></div>
        <div style="margin-top:8px"><strong>Top keywords:</strong></div>
        <div style="margin-top:6px">${kws}</div>
      </div>
    `);
  } catch (e) {
    render('analyzeResult', `<div class="result err">${escapeHtml(e.message)}</div>`);
  }
});

// ---------- Generate Links ----------
let generatedLinks = [];

document.getElementById('generateBtn').addEventListener('click', async () => {
  const keywords = document.getElementById('keywords').value.trim();
  const baseUrl = document.getElementById('baseUrl').value.trim();
  const numLinks = parseInt(document.getElementById('numLinks').value, 10) || 10;

  if (!keywords || !baseUrl) return alert('Enter keywords and base URL');
  render('linksResult', '<div class="result">Generating...</div>');

  try {
    const r = await fetch(`${API}/api/generate-links`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        base_url: baseUrl,
        keywords: keywords.split(',').map(k => k.trim()),
        num_links: numLinks
      })
    });
    const data = await r.json();
    if (data.error) return render('linksResult', `<div class="result err">${escapeHtml(data.error)}</div>`);

    generatedLinks = data.links;
    const rows = data.links.map((l, i) =>
      `<div class="item"><span class="badge">${i+1}</span>${escapeHtml(l.tracker_url)}</div>`
    ).join('');
    render('linksResult', `<div class="result"><div class="ok">Generated ${data.count} links (with local tracker)</div>${rows}</div>`);
  } catch (e) {
    render('linksResult', `<div class="result err">${escapeHtml(e.message)}</div>`);
  }
});

// ---------- Find Communities ----------
let foundCommunities = [];

document.getElementById('findBtn').addEventListener('click', async () => {
  const repoUrl = document.getElementById('repoUrl').value.trim();
  const keywords = document.getElementById('keywords').value.trim().split(',').map(k => k.trim()).filter(Boolean);
  if (!repoUrl && !keywords.length) return alert('Enter repo URL or keywords');
  render('communitiesResult', '<div class="result">Finding communities...</div>');

  try {
    const r = await fetch(`${API}/api/find-communities`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({repo_url: repoUrl, keywords})
    });
    const data = await r.json();
    if (data.error) return render('communitiesResult', `<div class="result err">${escapeHtml(data.error)}</div>`);

    foundCommunities = data.communities.map(c => c.community);
    const rows = data.communities.map(c =>
      `<div class="item"><span class="badge">${c.score}</span>r/${escapeHtml(c.community)} <span class="hint">${escapeHtml(c.reason)}</span></div>`
    ).join('');
    render('communitiesResult', `<div class="result"><div class="ok">Category: ${escapeHtml(data.category)} · ${data.communities.length} matches</div>${rows || '<div class="warn">No communities met the threshold.</div>'}</div>`);
  } catch (e) {
    render('communitiesResult', `<div class="result err">${escapeHtml(e.message)}</div>`);
  }
});

// ---------- Post ----------
document.getElementById('postBtn').addEventListener('click', async () => {
  if (!generatedLinks.length) return alert('Generate links first');
  if (!foundCommunities.length) return alert('Find communities first');
  const dryRun = document.getElementById('dryRun').checked;

  render('postResult', '<div class="result">Starting distribution...</div>');

  try {
    const r = await fetch(`${API}/api/post`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        links: generatedLinks,
        communities: foundCommunities,
        dry_run: dryRun
      })
    });
    const data = await r.json();
    if (data.error) return render('postResult', `<div class="result err">${escapeHtml(data.error)}</div>`);

    render('postResult', `
      <div class="result">
        <div class="ok">Distribution started (${data.dry_run ? 'DRY RUN' : 'LIVE'})</div>
        <div style="margin-top:8px">Links: ${data.links} · Communities: ${data.communities}</div>
        <div style="margin-top:8px">Open <a href="/dashboard" style="color:#58a6ff">Live Dashboard</a> to monitor progress.</div>
      </div>
    `);
  } catch (e) {
    render('postResult', `<div class="result err">${escapeHtml(e.message)}</div>`);
  }
});