/* ── Cognitive ETL — Client-side Logic ── */

// ── Data Loading ─────────────────────────────────────────────────────────────

async function loadJSON(name) {
  try {
    const resp = await fetch(`./data/${name}.json`);
    if (!resp.ok) return name === 'graph' ? { nodes: [], edges: [] } : [];
    return resp.json();
  } catch {
    return name === 'graph' ? { nodes: [], edges: [] } : [];
  }
}

// ── Search (Fuse.js) ─────────────────────────────────────────────────────────

let fuseInstance = null;

async function initSearch() {
  const searchInput = document.getElementById('search-input');
  if (!searchInput) return;

  const index = await loadJSON('search_index');
  if (!index.length) return;

  // Load Fuse.js from CDN
  if (typeof Fuse === 'undefined') {
    await new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js';
      script.onload = resolve;
      document.head.appendChild(script);
    });
  }

  fuseInstance = new Fuse(index, {
    keys: [
      { name: 'title', weight: 0.5 },
      { name: 'body', weight: 0.3 },
      { name: 'domain', weight: 0.1 },
      { name: 'tags', weight: 0.1 },
    ],
    threshold: 0.3,
    includeScore: true,
  });

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    const resultsEl = document.getElementById('search-results');
    if (!resultsEl) return;

    if (!query) {
      resultsEl.innerHTML = '';
      resultsEl.style.display = 'none';
      // Show all cards again
      document.querySelectorAll('.card, .atom-card').forEach(c => c.style.display = '');
      return;
    }

    const results = fuseInstance.search(query, { limit: 20 });
    renderSearchResults(results, resultsEl);
  });

  document.querySelectorAll('[data-query]').forEach((button) => {
    button.addEventListener('click', () => {
      const query = button.dataset.query || '';
      searchInput.value = query;
      searchInput.dispatchEvent(new Event('input', { bubbles: true }));
      searchInput.focus();
    });
  });
}

function renderSearchResults(results, container) {
  if (!results.length) {
    container.innerHTML = '<div class="empty-state"><p class="empty-state__body">No results found.</p></div>';
    container.style.display = 'block';
    return;
  }

  const typeIcons = { atom: '⚛️', artifact: '📦', source: '📚', capture: '📝' };
  
  container.innerHTML = results.map(r => {
    const item = r.item;
    const href = item.href ? escapeHtml(item.href) : '';
    const openTag = href ? `<a class="card card--interactive card--search" href="${href}">` : '<div class="card">';
    const closeTag = href ? '</a>' : '</div>';
    return `
      ${openTag}
        <span class="card__badge">${typeIcons[item.type] || ''} ${item.type}</span>
        <h3 class="card__title">${escapeHtml(item.title)}</h3>
        ${item.body ? `<p class="card__body">${escapeHtml(item.body.slice(0, 150))}${item.body.length > 150 ? '…' : ''}</p>` : ''}
        <div class="card__meta">
          ${(item.domain || []).map(d => `<span class="tag">${escapeHtml(d)}</span>`).join('')}
        </div>
      ${closeTag}
    `;
  }).join('');
  container.style.display = 'grid';
  container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(320px, 1fr))';
  container.style.gap = '20px';
}

// ── Domain Filtering ─────────────────────────────────────────────────────────

function initFilters() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  if (!filterBtns.length) return;

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const domain = btn.dataset.domain;
      
      // Toggle active
      if (domain === 'all') {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      } else {
        document.querySelector('.filter-btn[data-domain="all"]')?.classList.remove('active');
        btn.classList.toggle('active');
      }

      filterBtns.forEach((button) => {
        button.setAttribute('aria-pressed', button.classList.contains('active') ? 'true' : 'false');
      });

      // Get active domains
      const activeDomains = [...document.querySelectorAll('.filter-btn.active')]
        .map(b => b.dataset.domain)
        .filter(d => d !== 'all');

      // Filter cards
      const showAll = activeDomains.length === 0 || 
                      document.querySelector('.filter-btn[data-domain="all"]')?.classList.contains('active');
      
      document.querySelectorAll('[data-domains]').forEach(card => {
        const cardDomains = card.dataset.domains.split(',');
        card.style.display = showAll || activeDomains.some(d => cardDomains.includes(d)) 
          ? '' : 'none';
      });
    });
  });
}

// ── Knowledge Graph (D3.js) ──────────────────────────────────────────────────

async function initGraph() {
  const container = document.getElementById('knowledge-graph');
  if (!container) return;

  const graph = await loadJSON('graph');
  if (!graph.nodes || !graph.nodes.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">🕸️</div>
        <h3 class="empty-state__title">Graph Empty</h3>
        <p class="empty-state__body">Add atoms to Notion and sync to see your knowledge graph.</p>
      </div>
    `;
    return;
  }

  // Load D3
  if (typeof d3 === 'undefined') {
    await new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js';
      script.onload = resolve;
      document.head.appendChild(script);
    });
  }

  renderForceGraph(container, graph);
}

function renderForceGraph(container, graph) {
  const width = container.clientWidth;
  const height = container.clientHeight;
  const styles = getComputedStyle(document.documentElement);
  const labelColor = styles.getPropertyValue('--graph-label').trim() || 'rgba(23, 19, 14, 0.82)';
  const edgeColor = styles.getPropertyValue('--graph-edge').trim() || '#c7baa1';
  const edgeStrongColor = styles.getPropertyValue('--graph-edge-strong').trim() || '#9f8563';
  const nodeStroke = styles.getPropertyValue('--color-bg').trim() || '#f7f3ea';
  const sourceRelationColor = styles.getPropertyValue('--accent-graph').trim() || '#7b6a52';
  const sourceColor = styles.getPropertyValue('--color-source').trim() || '#7b6a52';
  const captureColor = styles.getPropertyValue('--color-capture').trim() || '#a9854f';
  const atomColor = styles.getPropertyValue('--color-atom').trim() || '#8f3e22';
  const artifactColor = styles.getPropertyValue('--color-artifact').trim() || '#6f7b61';
  const captureEdgeColor = '#b08f5e';
  const artifactEdgeColor = '#8b9681';

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height]);

  // Colors by type
  const colorMap = {
    atom: atomColor,
    source: sourceColor,
    capture: captureColor,
    artifact: artifactColor,
  };

  const domainColors = {
    'alignment': '#7f6a56',
    'causal inference': '#8f3e22',
    'systems': '#6f7b61',
    'RL': '#9d5d3a',
    'deep learning': '#7a4e35',
    'probability': '#8c6b4a',
    'neuroscience': '#92754d',
    'economics': '#6d6252',
    'philosophy': '#746d63',
    'complexity': '#89785d',
  };

  // Build simulation
  const simulation = d3.forceSimulation(graph.nodes)
    .force('link', d3.forceLink(graph.edges)
      .id(d => d.id)
      .distance(d => {
        if (d.type === 'related_source') return 120;
        if (d.type === 'capture_to_atom' || d.type === 'captured_from_source') return 95;
        if (d.type === 'artifact_from_atom' || d.type === 'artifact_from_source' || d.type === 'capture_to_artifact') return 90;
        return 80;
      })
      .strength(d => d.type === 'related_source' ? 0.18 : 0.32))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(d => {
      if (d.type === 'source') return 20;
      if (d.type === 'capture') return 16;
      if (d.type === 'artifact') return 14;
      return 12 + (d.reuse_count || 0);
    }));

  // Edges
  const link = svg.append('g')
    .selectAll('line')
    .data(graph.edges)
    .join('line')
    .attr('stroke', d => {
      if (d.type === 'related_source') return sourceRelationColor;
      if (d.type === 'captured_from_source' || d.type === 'capture_to_atom') return captureEdgeColor;
      if (d.type === 'artifact_from_atom' || d.type === 'artifact_from_source' || d.type === 'capture_to_artifact') return artifactEdgeColor;
      return d.type === 'related' ? edgeStrongColor : edgeColor;
    })
    .attr('stroke-width', d => {
      if (d.type === 'related_source') return 2;
      if (d.type === 'capture_to_atom' || d.type === 'captured_from_source') return 1.5;
      if (d.type === 'artifact_from_atom' || d.type === 'artifact_from_source' || d.type === 'capture_to_artifact') return 1.4;
      return d.type === 'related' ? 1.6 : 1.2;
    })
    .attr('stroke-dasharray', d => {
      if (d.type === 'related_source') return '6 4';
      if (d.type === 'artifact_from_source') return '3 3';
      return null;
    })
    .attr('stroke-opacity', d => d.type === 'related_source' ? 0.85 : 0.78);

  // Nodes
  const node = svg.append('g')
    .selectAll('circle')
    .data(graph.nodes)
    .join('circle')
    .attr('r', d => {
      if (d.type === 'source') return 14;
      if (d.type === 'capture') return 10;
      if (d.type === 'artifact') return 9;
      return 6 + (d.reuse_count || 0) * 2;
    })
    .attr('fill', d => {
      if (d.type === 'source') return colorMap.source;
      if (d.type === 'capture') return colorMap.capture;
      if (d.type === 'artifact') return colorMap.artifact;
      const primaryDomain = (d.domain || [])[0];
      return domainColors[primaryDomain] || colorMap.atom;
    })
    .attr('stroke', nodeStroke)
    .attr('stroke-width', 1.5)
    .style('cursor', 'pointer')
    .on('click', (_, d) => {
      if (d.url) {
        window.location.href = d.url;
      }
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  // Labels
  const label = svg.append('g')
    .selectAll('text')
    .data(graph.nodes)
    .join('text')
    .text(d => d.label.length > 30 ? d.label.slice(0, 30) + '…' : d.label)
    .attr('font-size', d => {
      if (d.type === 'source') return 11;
      if (d.type === 'capture' || d.type === 'artifact') return 10;
      return 9;
    })
    .attr('font-family', styles.getPropertyValue('--font-mono').trim() || "'IBM Plex Mono', monospace")
    .attr('fill', labelColor)
    .attr('dx', d => d.type === 'source' ? 18 : 12)
    .attr('dy', 4);

  // Tooltip
  node.append('title').text(d => d.label);

  // Tick
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y);

    label
      .attr('x', d => d.x)
      .attr('y', d => d.y);
  });

  // Drag handlers
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }

  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }

  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }

  // Zoom
  svg.call(d3.zoom()
    .extent([[0, 0], [width, height]])
    .scaleExtent([0.3, 4])
    .on('zoom', (event) => {
      svg.selectAll('g').attr('transform', event.transform);
    }));
}

// ── Utilities ────────────────────────────────────────────────────────────────

function applyLegendColors() {
  const domainColors = {
    'alignment': '#7f6a56',
    'causal inference': '#8f3e22',
    'systems': '#6f7b61',
    'RL': '#9d5d3a',
    'deep learning': '#7a4e35',
    'probability': '#8c6b4a',
    'neuroscience': '#92754d',
    'economics': '#6d6252',
    'philosophy': '#746d63',
    'complexity': '#89785d',
  };

  document.querySelectorAll('[data-domain-color]').forEach((dot) => {
    const domain = dot.dataset.domainColor;
    dot.style.background = domainColors[domain] || '#8f3e22';
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  applyLegendColors();
  initSearch();
  initFilters();
  initGraph();
});
