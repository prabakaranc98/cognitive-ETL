/* ── Cognitive ETL — Client-side Logic ── */

async function loadJSON(name) {
  try {
    const resp = await fetch(`./data/${name}.json`);
    if (!resp.ok) return name === 'graph' ? { nodes: [], edges: [] } : [];
    return resp.json();
  } catch {
    return name === 'graph' ? { nodes: [], edges: [] } : [];
  }
}

let searchEnginePromise = null;

async function ensureFuse() {
  if (typeof Fuse !== 'undefined') return;
  await new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js';
    script.onload = resolve;
    document.head.appendChild(script);
  });
}

async function getSearchEngine() {
  if (searchEnginePromise) return searchEnginePromise;

  searchEnginePromise = (async () => {
    const index = await loadJSON('search_index');
    if (!index.length) return null;

    await ensureFuse();
    const fuse = new Fuse(index, {
      keys: [
        { name: 'title', weight: 0.5 },
        { name: 'body', weight: 0.3 },
        { name: 'domain', weight: 0.1 },
        { name: 'tags', weight: 0.1 },
      ],
      threshold: 0.3,
      includeScore: true,
    });

    return { index, fuse };
  })();

  return searchEnginePromise;
}

function scopeMatches(item, scope) {
  return scope === 'all' || item.type === scope;
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(text, length) {
  if (!text) return '';
  return text.length > length ? `${text.slice(0, length)}…` : text;
}

function hideResults(container) {
  if (!container) return;
  container.hidden = true;
  container.innerHTML = '';
}

function renderSearchResults(results, container, options = {}) {
  if (!container) return;

  const { floating = false } = options;
  if (!results.length) {
    container.hidden = false;
    container.innerHTML = '<div class="search-empty">No matching items.</div>';
    return;
  }

  container.hidden = false;
  container.innerHTML = results.map(({ item }) => {
    const body = truncate(item.body || '', floating ? 110 : 150);
    const domains = (item.domain || []).slice(0, floating ? 2 : 4);
    return `
      <a class="search-result" href="${escapeHtml(item.href || '#')}">
        <div class="search-result__meta">
          <span class="search-result__type">${escapeHtml(item.type)}</span>
          ${domains.map((domain) => `<span class="search-result__tag">${escapeHtml(domain)}</span>`).join('')}
        </div>
        <strong class="search-result__title">${escapeHtml(item.title)}</strong>
        ${body ? `<p class="search-result__body">${escapeHtml(body)}</p>` : ''}
      </a>
    `;
  }).join('');
}

function getSearchInputForButton(button) {
  const context = button.closest('[data-search-context]');
  if (context) {
    return context.querySelector('[data-search-input][data-search-mode="results"]');
  }
  return document.querySelector('[data-search-input][data-search-mode="results"]');
}

async function initResultSearches() {
  const inputs = [...document.querySelectorAll('[data-search-input][data-search-mode="results"]')];
  if (!inputs.length) return;

  const engine = await getSearchEngine();
  if (!engine) return;

  for (const input of inputs) {
    const resultsId = input.dataset.resultsTarget;
    const scope = input.dataset.searchScope || 'all';
    const container = resultsId ? document.getElementById(resultsId) : null;
    if (!container) continue;

    const runSearch = () => {
      const query = input.value.trim();
      if (!query) {
        hideResults(container);
        return;
      }

      const matches = engine.fuse
        .search(query, { limit: scope === 'all' ? 12 : 24 })
        .filter((result) => scopeMatches(result.item, scope))
        .slice(0, scope === 'all' ? 8 : 12);

      renderSearchResults(matches, container, { floating: container.classList.contains('search-results--floating') });
    };

    input.addEventListener('input', runSearch);
    input.addEventListener('focus', () => {
      if (input.value.trim()) runSearch();
    });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        input.blur();
        hideResults(container);
      }
    });
  }

  document.addEventListener('click', (event) => {
    document.querySelectorAll('.search-results--floating').forEach((container) => {
      if (!container.parentElement?.contains(event.target)) {
        hideResults(container);
      }
    });
  });

  document.querySelectorAll('[data-query]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = getSearchInputForButton(button);
      if (!input) return;
      input.value = button.dataset.query || '';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
    });
  });
}

function cardMatchesFilter(card, group, value) {
  if (value === 'all') return true;

  if (group === 'domain') {
    const domains = (card.dataset.domains || '').split(',').filter(Boolean);
    return domains.includes(value);
  }

  if (group === 'status') {
    return (card.dataset.status || '') === value;
  }

  if (group === 'capture-type') {
    return (card.dataset.captureType || '') === value;
  }

  if (group === 'usage') {
    return (card.dataset.usage || '') === value;
  }

  return true;
}

function initCollectionFiltering() {
  document.querySelectorAll('[data-collection]').forEach((collection) => {
    const cards = [...collection.querySelectorAll('[data-filterable-item]')];
    if (!cards.length) return;

    const searchInput = collection.querySelector('[data-collection-search]');
    const filterButtons = [...collection.querySelectorAll('.filter-btn[data-filter-group]')];
    const emptyState = collection.querySelector('[data-collection-empty]');

    const update = () => {
      const query = (searchInput?.value || '').trim().toLowerCase();
      const activeFilters = {};

      filterButtons.forEach((button) => {
        const group = button.dataset.filterGroup;
        const value = button.dataset.filterValue || 'all';
        if (!group || !button.classList.contains('active') || value === 'all') return;
        activeFilters[group] = value;
      });

      let visibleCount = 0;

      cards.forEach((card) => {
        const searchText = (card.dataset.searchText || '').toLowerCase();
        const queryMatch = !query || searchText.includes(query);
        const filterMatch = Object.entries(activeFilters).every(([group, value]) => cardMatchesFilter(card, group, value));
        const isVisible = queryMatch && filterMatch;

        card.hidden = !isVisible;
        if (isVisible) visibleCount += 1;
      });

      if (emptyState) {
        emptyState.hidden = visibleCount !== 0;
      }
    };

    filterButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const group = button.dataset.filterGroup;
        if (!group) return;

        collection.querySelectorAll(`.filter-btn[data-filter-group="${group}"]`).forEach((peer) => {
          peer.classList.remove('active');
          peer.setAttribute('aria-pressed', 'false');
        });

        button.classList.add('active');
        button.setAttribute('aria-pressed', 'true');
        update();
      });
    });

    if (searchInput) {
      searchInput.addEventListener('input', update);
    }

    update();
  });
}

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

  if (typeof d3 === 'undefined') {
    await new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js';
      script.onload = resolve;
      document.head.appendChild(script);
    });
  }

  const engine = await getSearchEngine();
  renderForceGraph(container, graph, engine?.index || []);
}

function buildGraphSummary(node) {
  if (node.summary) return node.summary;
  if (node.type === 'source') return 'A provenance node in the working library.';
  if (node.type === 'capture') return 'An extraction note preserved before it becomes a reusable claim.';
  if (node.type === 'artifact') return 'A public-facing output built from captures and atoms.';
  return 'A reusable claim in the graph.';
}

function renderForceGraph(container, graph, searchIndex) {
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

  const lookup = new Map(searchIndex.map((item) => [`${item.type}:${item.id}`, item]));
  const nodes = graph.nodes.map((node) => ({
    ...node,
    summary: lookup.get(node.id)?.body || '',
  }));
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const adjacency = new Map(nodes.map((node) => [node.id, new Set()]));

  graph.edges.forEach((edge) => {
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  });

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height]);

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

  const orderedDomains = [...new Set(
    nodes.flatMap((node) => node.type === 'atom' ? (node.domain || []) : []).filter(Boolean),
  )].sort((a, b) => {
    const aIndex = Object.keys(domainColors).indexOf(a);
    const bIndex = Object.keys(domainColors).indexOf(b);
    const normalizedA = aIndex === -1 ? 999 : aIndex;
    const normalizedB = bIndex === -1 ? 999 : bIndex;
    if (normalizedA !== normalizedB) return normalizedA - normalizedB;
    return a.localeCompare(b);
  });

  const edgeMultiplicity = new Map();
  const edges = graph.edges.map((edge) => {
    const pairKey = [edge.source, edge.target].sort().join('|');
    const index = edgeMultiplicity.get(pairKey) || 0;
    edgeMultiplicity.set(pairKey, index + 1);
    return { ...edge, curveIndex: index };
  });

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges)
      .id((d) => d.id)
      .distance((d) => {
        if (d.type === 'related_source') return 150;
        if (d.type === 'capture_to_atom' || d.type === 'captured_from_source') return 110;
        if (d.type === 'artifact_from_atom' || d.type === 'artifact_from_source' || d.type === 'capture_to_artifact') return 104;
        return 90;
      })
      .strength((d) => d.type === 'related_source' ? 0.14 : 0.28))
    .force('charge', d3.forceManyBody().strength(-250))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('cluster-x', d3.forceX((d) => clusterAnchor(d).x).strength((d) => d.type === 'atom' ? 0.045 : 0.07))
    .force('cluster-y', d3.forceY((d) => clusterAnchor(d).y).strength((d) => d.type === 'atom' ? 0.038 : 0.055))
    .force('collision', d3.forceCollide().radius((d) => {
      if (d.type === 'source') return 24;
      if (d.type === 'capture') return 18;
      if (d.type === 'artifact') return 17;
      return 14 + (d.reuse_count || 0) * 1.4;
    }));

  function nodeRadius(d) {
    if (d.type === 'source') return 14;
    if (d.type === 'capture') return 10;
    if (d.type === 'artifact') return 9;
    return 6 + (d.reuse_count || 0) * 2;
  }

  function clusterAnchor(node) {
    const primaryDomain = (node.domain || [])[0] || '';
    const domainIndex = orderedDomains.indexOf(primaryDomain);
    const domainCount = Math.max(orderedDomains.length, 1);
    const top = height * 0.18;
    const bandHeight = height * 0.64;
    const atomY = domainIndex >= 0
      ? top + (bandHeight * (domainIndex + 0.5)) / domainCount
      : height * 0.48;

    if (node.type === 'source') return { x: width * 0.14, y: height * 0.24 };
    if (node.type === 'capture') return { x: width * 0.34, y: height * 0.7 };
    if (node.type === 'artifact') return { x: width * 0.86, y: height * 0.28 };
    return { x: width * 0.62, y: atomY };
  }

  function edgeCurveOffset(edge) {
    const sourceId = resolveNodeId(edge.source);
    const targetId = resolveNodeId(edge.target);
    const baseByType = {
      related_source: 48,
      captured_from_source: 26,
      capture_to_atom: 22,
      capture_to_artifact: 20,
      artifact_from_atom: 24,
      artifact_from_source: 28,
      related: 18,
    };
    const base = baseByType[edge.type] || 16;
    const hash = `${sourceId}|${targetId}`.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0);
    const sign = hash % 2 === 0 ? 1 : -1;
    return sign * (base + edge.curveIndex * 10);
  }

  function buildEdgePath(edge) {
    const source = edge.source;
    const target = edge.target;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const distance = Math.hypot(dx, dy) || 1;
    const ux = dx / distance;
    const uy = dy / distance;
    const startX = source.x + ux * nodeRadius(source);
    const startY = source.y + uy * nodeRadius(source);
    const endX = target.x - ux * nodeRadius(target);
    const endY = target.y - uy * nodeRadius(target);
    const mx = (startX + endX) / 2;
    const my = (startY + endY) / 2;
    const offset = edgeCurveOffset(edge);
    const nx = -uy;
    const ny = ux;
    const controlX = mx + nx * offset;
    const controlY = my + ny * offset;
    return `M${startX},${startY} Q${controlX},${controlY} ${endX},${endY}`;
  }

  const link = svg.append('g')
    .selectAll('path')
    .data(edges)
    .join('path')
    .attr('fill', 'none')
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .attr('stroke', (d) => {
      if (d.type === 'related_source') return sourceRelationColor;
      if (d.type === 'captured_from_source' || d.type === 'capture_to_atom') return captureEdgeColor;
      if (d.type === 'artifact_from_atom' || d.type === 'artifact_from_source' || d.type === 'capture_to_artifact') return artifactEdgeColor;
      return d.type === 'related' ? edgeStrongColor : edgeColor;
    })
    .attr('stroke-width', (d) => {
      if (d.type === 'related_source') return 2;
      if (d.type === 'capture_to_atom' || d.type === 'captured_from_source') return 1.5;
      if (d.type === 'artifact_from_atom' || d.type === 'artifact_from_source' || d.type === 'capture_to_artifact') return 1.4;
      return d.type === 'related' ? 1.6 : 1.2;
    })
    .attr('stroke-dasharray', (d) => {
      if (d.type === 'related_source') return '6 4';
      if (d.type === 'artifact_from_source') return '3 3';
      return null;
    })
    .attr('stroke-opacity', (d) => d.type === 'related_source' ? 0.85 : 0.78);

  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', (d) => nodeRadius(d))
    .attr('fill', (d) => {
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
      selectedId = d.id;
      updateInspector(d);
      refreshVisibility();
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended));

  const label = svg.append('g')
    .selectAll('text')
    .data(nodes)
    .join('text')
    .text((d) => d.label.length > 30 ? `${d.label.slice(0, 30)}…` : d.label)
    .attr('font-size', (d) => {
      if (d.type === 'source') return 11;
      if (d.type === 'capture' || d.type === 'artifact') return 10;
      return 9;
    })
    .attr('font-family', styles.getPropertyValue('--font-mono').trim() || "'IBM Plex Mono', monospace")
    .attr('fill', labelColor)
    .attr('dx', (d) => d.type === 'source' ? 18 : 12)
    .attr('dy', 4);

  node.append('title').text((d) => d.label);

  simulation.on('tick', () => {
    link
      .attr('d', (d) => buildEdgePath(d));

    node
      .attr('cx', (d) => d.x)
      .attr('cy', (d) => d.y);

    label
      .attr('x', (d) => d.x)
      .attr('y', (d) => d.y);
  });

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

  svg.call(d3.zoom()
    .extent([[0, 0], [width, height]])
    .scaleExtent([0.3, 4])
    .on('zoom', (event) => {
      svg.selectAll('g').attr('transform', event.transform);
    }));

  const filterState = { type: 'all', domain: 'all' };
  let selectedId = null;

  const inspectorTitle = document.getElementById('graph-inspector-title');
  const inspectorSummary = document.getElementById('graph-inspector-summary');
  const inspectorMeta = document.getElementById('graph-inspector-meta');
  const inspectorTags = document.getElementById('graph-inspector-tags');
  const inspectorLinks = document.getElementById('graph-inspector-links');
  const inspectorActions = document.getElementById('graph-inspector-actions');
  const inspector = document.getElementById('graph-inspector');

  function resolveNodeId(value) {
    return typeof value === 'object' ? value.id : value;
  }

  function nodeVisible(d) {
    const matchesType = filterState.type === 'all' || d.type === filterState.type;
    const matchesDomain = filterState.domain === 'all' || (d.domain || []).includes(filterState.domain);
    return matchesType && matchesDomain;
  }

  function refreshVisibility() {
    node
      .attr('opacity', (d) => {
        if (!nodeVisible(d)) return 0.14;
        if (!selectedId) return 0.95;
        return d.id === selectedId || adjacency.get(selectedId)?.has(d.id) ? 1 : 0.24;
      })
      .attr('stroke-width', (d) => d.id === selectedId ? 3 : 1.5);

    label.attr('opacity', (d) => {
      if (!nodeVisible(d)) return 0.08;
      if (!selectedId) return 0.82;
      return d.id === selectedId || adjacency.get(selectedId)?.has(d.id) ? 1 : 0.24;
    });

    link.attr('stroke-opacity', (d) => {
      const sourceId = resolveNodeId(d.source);
      const targetId = resolveNodeId(d.target);
      const sourceNode = nodeById.get(sourceId);
      const targetNode = nodeById.get(targetId);
      if (!sourceNode || !targetNode || !nodeVisible(sourceNode) || !nodeVisible(targetNode)) return 0.05;
      if (!selectedId) return d.type === 'related_source' ? 0.85 : 0.78;
      return sourceId === selectedId || targetId === selectedId ? 0.98 : 0.16;
    });
  }

  function updateInspector(nodeData) {
    if (!inspectorTitle || !inspectorSummary || !inspectorMeta || !inspectorTags || !inspectorLinks || !inspectorActions) {
      return;
    }

    const neighbors = [...(adjacency.get(nodeData.id) || [])]
      .map((neighborId) => nodeById.get(neighborId))
      .filter(Boolean)
      .slice(0, 6);

    inspectorTitle.textContent = nodeData.label;
    inspectorSummary.textContent = buildGraphSummary(nodeData);
    inspector?.classList.add('is-active');

    const metaBits = [
      `<span class="graph-meta-pill">${escapeHtml(nodeData.type)}</span>`,
    ];
    if (nodeData.atom_type) metaBits.push(`<span class="graph-meta-pill">${escapeHtml(nodeData.atom_type)}</span>`);
    if (nodeData.confidence) metaBits.push(`<span class="graph-meta-pill">${escapeHtml(nodeData.confidence)}</span>`);
    if (typeof nodeData.reuse_count === 'number') metaBits.push(`<span class="graph-meta-pill">reuse ${nodeData.reuse_count}</span>`);
    inspectorMeta.innerHTML = metaBits.join('');

    inspectorTags.innerHTML = (nodeData.domain || []).map((domain) => `<span class="tag">${escapeHtml(domain)}</span>`).join('');

    inspectorLinks.innerHTML = neighbors.length
      ? `
        <p class="graph-inspector__label">Connected items</p>
        <div class="graph-link-list">
          ${neighbors.map((neighbor) => `<a href="${escapeHtml(neighbor.url || '#')}">${escapeHtml(neighbor.label)}</a>`).join('')}
        </div>
      `
      : '<p class="graph-inspector__label">No connected items yet.</p>';

    inspectorActions.innerHTML = `
      ${nodeData.url ? `<a class="button-primary" href="${escapeHtml(nodeData.url)}">Open details</a>` : ''}
      <button class="button-secondary button-secondary--plain" type="button" id="graph-clear-selection">Clear selection</button>
    `;

    const clearButton = document.getElementById('graph-clear-selection');
    if (clearButton) {
      clearButton.addEventListener('click', () => {
        selectedId = null;
        inspectorTitle.textContent = 'Select a node';
        inspectorSummary.textContent = 'Click a node to inspect it without leaving the graph. Use the detail page only when you want the full reading view.';
        inspectorMeta.innerHTML = '';
        inspectorTags.innerHTML = '';
        inspectorLinks.innerHTML = '';
        inspectorActions.innerHTML = '';
        inspector?.classList.remove('is-active');
        refreshVisibility();
      });
    }
  }

  document.querySelectorAll('[data-graph-filter-group]').forEach((button) => {
    button.addEventListener('click', () => {
      const group = button.dataset.graphFilterGroup;
      const value = button.dataset.graphFilterValue || 'all';
      if (!group) return;

      document.querySelectorAll(`[data-graph-filter-group="${group}"]`).forEach((peer) => {
        peer.classList.remove('active');
        peer.setAttribute('aria-pressed', 'false');
      });

      button.classList.add('active');
      button.setAttribute('aria-pressed', 'true');
      filterState[group] = value;
      refreshVisibility();
    });
  });

  refreshVisibility();
}

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

document.addEventListener('DOMContentLoaded', () => {
  applyLegendColors();
  initResultSearches();
  initCollectionFiltering();
  initGraph();
});
