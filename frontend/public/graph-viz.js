/**
 * Knowledge Graph Visualization Module
 * Uses D3.js for interactive graph visualization
 */

class GraphVisualizer {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.graphData = null;
        this.currentSessionId = null;
        this.simulation = null;
        this.svg = null;
        this.width = 0;
        this.height = 0;

        // Color schemes for different node types
        this.nodeColors = {
            paper: '#0ea5e9',     // Blue
            concept: '#d946ef',   // Purple
            author: '#f59e0b',    // Orange
            method: '#10b981'     // Green
        };

        this.init();
    }

    init() {
        // Set up container dimensions
        this.updateDimensions();
        window.addEventListener('resize', () => this.updateDimensions());
    }

    updateDimensions() {
        if (!this.container) return;

        const rect = this.container.getBoundingClientRect();
        this.width = rect.width || 1200;
        this.height = rect.height || 800;
    }

    async loadGraph(sessionId) {
        try {
            this.currentSessionId = sessionId;

            // Show loading state
            this.showLoading();

            // Fetch graph data
            const token = localStorage.getItem('aura_access_token');
            const response = await fetch(`http://localhost:8000/graph/data/${sessionId}`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            const data = await response.json();

            if (!data.success) {
                throw new Error('Failed to load graph data');
            }

            this.graphData = data.graph;

            // Render the graph
            this.render();

            // Load and display analysis
            await this.loadAnalysis(sessionId);

        } catch (error) {
            console.error('Error loading graph:', error);
            this.showError('Failed to load knowledge graph. ' + error.message);
        }
    }

    async loadAnalysis(sessionId) {
        try {
            const token = localStorage.getItem('aura_access_token');
            const response = await fetch(`http://localhost:8000/graph/analyze/${sessionId}`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            const data = await response.json();

            if (data.success) {
                this.displayInsights(data.analysis.insights);
                this.displayCentralNodes(data.analysis.central_nodes);
                this.displayCommunities(data.analysis.communities);
            }
        } catch (error) {
            console.error('Error loading analysis:', error);
        }
    }

    render() {
        if (!this.graphData || !this.graphData.nodes || this.graphData.nodes.length === 0) {
            this.showError('No graph data available');
            return;
        }

        // Clear container
        this.container.innerHTML = '';

        // Create SVG
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height)
            .attr('class', 'graph-svg');

        // Add zoom behavior
        const g = this.svg.append('g');

        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        this.svg.call(zoom);

        // Create arrow markers for directed edges
        this.svg.append('defs').selectAll('marker')
            .data(['authored', 'discusses', 'uses_method'])
            .enter().append('marker')
            .attr('id', d => `arrow-${d}`)
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#999');

        // Create force simulation
        this.simulation = d3.forceSimulation(this.graphData.nodes)
            .force('link', d3.forceLink(this.graphData.edges)
                .id(d => d.id)
                .distance(d => {
                    // Adjust link distance based on type
                    if (d.type === 'related_to') return 100;
                    return 150;
                }))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => this.getNodeRadius(d) + 5));

        // Create edges
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(this.graphData.edges)
            .enter().append('line')
            .attr('class', 'graph-edge')
            .attr('stroke', d => this.getEdgeColor(d.type))
            .attr('stroke-width', d => d.weight ? d.weight * 2 : 1)
            .attr('stroke-opacity', 0.6)
            .attr('marker-end', d => {
                if (['authored', 'discusses', 'uses_method'].includes(d.type)) {
                    return `url(#arrow-${d.type})`;
                }
                return null;
            });

        // Create nodes
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(this.graphData.nodes)
            .enter().append('g')
            .attr('class', 'graph-node')
            .call(d3.drag()
                .on('start', (event, d) => this.dragStarted(event, d))
                .on('drag', (event, d) => this.dragged(event, d))
                .on('end', (event, d) => this.dragEnded(event, d)));

        // Add circles to nodes
        node.append('circle')
            .attr('r', d => this.getNodeRadius(d))
            .attr('fill', d => this.nodeColors[d.type] || '#6b7280')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .attr('class', 'node-circle');

        // Add labels
        node.append('text')
            .text(d => this.getNodeLabel(d))
            .attr('x', 0)
            .attr('y', d => this.getNodeRadius(d) + 15)
            .attr('text-anchor', 'middle')
            .attr('class', 'node-label')
            .attr('font-size', '11px')
            .attr('fill', 'currentColor');

        // Add tooltips
        node.append('title')
            .text(d => this.getTooltipText(d));

        // Add click handler
        node.on('click', (event, d) => this.onNodeClick(event, d));

        // Update positions on tick
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    getNodeRadius(node) {
        if (node.type === 'paper') {
            const relevance = node.metrics?.relevance_score || 5;
            return 8 + (relevance / 10) * 8; // 8-16px based on relevance
        }

        if (node.type === 'concept') {
            const centrality = node.metrics?.centrality || 0.5;
            return 6 + centrality * 12; // 6-18px based on centrality
        }

        return 10; // Default size
    }

    getNodeLabel(node) {
        const label = node.label || 'Unknown';

        // Truncate long labels
        if (label.length > 30) {
            return label.substring(0, 27) + '...';
        }
        return label;
    }

    getEdgeColor(type) {
        const colors = {
            'authored': '#f59e0b',
            'discusses': '#0ea5e9',
            'uses_method': '#10b981',
            'related_to': '#d946ef'
        };
        return colors[type] || '#999';
    }

    getTooltipText(node) {
        let text = `${node.label}\nType: ${node.type}`;

        if (node.type === 'paper') {
            text += `\nAuthors: ${node.authors || 'Unknown'}`;
            text += `\nYear: ${node.year || 'N/A'}`;
            text += `\nRelevance: ${node.metrics?.relevance_score || 'N/A'}`;
        } else if (node.type === 'concept') {
            text += `\nFrequency: ${node.metrics?.frequency || 0}`;
        } else if (node.type === 'author') {
            text += `\nPapers: ${node.metrics?.paper_count || 0}`;
        } else if (node.type === 'method') {
            text += `\nUsage: ${node.metrics?.frequency || 0} papers`;
        }

        return text;
    }

    onNodeClick(event, node) {
        // Display detailed information in side panel
        this.displayNodeDetails(node);

        // Highlight connected nodes
        this.highlightConnections(node);
    }

    displayNodeDetails(node) {
        const detailsPanel = document.getElementById('graph-details-panel');
        if (!detailsPanel) return;

        let html = `
            <div class="p-4 border-b border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900">${node.label}</h3>
                <span class="inline-block px-2 py-1 text-xs font-medium rounded mt-2"
                      style="background-color: ${this.nodeColors[node.type]}20; color: ${this.nodeColors[node.type]}">
                    ${node.type.toUpperCase()}
                </span>
            </div>
            <div class="p-4 space-y-3">
        `;

        if (node.type === 'paper') {
            html += `
                <div>
                    <p class="text-sm font-medium text-gray-700">Authors</p>
                    <p class="text-sm text-gray-600">${node.authors || 'Unknown'}</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">Year</p>
                    <p class="text-sm text-gray-600">${node.year || 'N/A'}</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">Summary</p>
                    <p class="text-sm text-gray-600">${node.summary || 'No summary available'}</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">Domain</p>
                    <p class="text-sm text-gray-600">${node.metadata?.domain || 'Unknown'}</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">Relevance Score</p>
                    <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                        <div class="bg-blue-500 h-2 rounded-full" style="width: ${(node.metrics?.relevance_score || 5) * 10}%"></div>
                    </div>
                    <p class="text-xs text-gray-500 mt-1">${node.metrics?.relevance_score || 5}/10</p>
                </div>
            `;

            if (node.source) {
                html += `
                    <div>
                        <a href="${node.source}" target="_blank"
                           class="text-sm text-blue-500 hover:text-blue-700 underline">
                            View Source →
                        </a>
                    </div>
                `;
            }
        } else if (node.type === 'concept') {
            html += `
                <div>
                    <p class="text-sm font-medium text-gray-700">Frequency</p>
                    <p class="text-sm text-gray-600">Appears in ${node.metrics?.frequency || 0} papers</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">Centrality</p>
                    <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                        <div class="bg-purple-500 h-2 rounded-full" style="width: ${(node.metrics?.centrality || 0) * 100}%"></div>
                    </div>
                </div>
            `;
        } else if (node.type === 'author') {
            html += `
                <div>
                    <p class="text-sm font-medium text-gray-700">Papers</p>
                    <p class="text-sm text-gray-600">${node.metrics?.paper_count || 0} papers</p>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">Domains</p>
                    <p class="text-sm text-gray-600">${node.metrics?.domains?.join(', ') || 'N/A'}</p>
                </div>
            `;
        } else if (node.type === 'method') {
            html += `
                <div>
                    <p class="text-sm font-medium text-gray-700">Usage</p>
                    <p class="text-sm text-gray-600">Used in ${node.metrics?.frequency || 0} papers</p>
                </div>
            `;
        }

        html += '</div>';
        detailsPanel.innerHTML = html;
    }

    highlightConnections(node) {
        // This would highlight connected nodes - implement as needed
        console.log('Highlighting connections for', node);
    }

    displayInsights(insights) {
        const insightsPanel = document.getElementById('graph-insights-panel');
        if (!insightsPanel || !insights) return;

        insightsPanel.innerHTML = insights.map(insight => `
            <div class="p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p class="text-sm text-gray-700">${insight}</p>
            </div>
        `).join('');
    }

    displayCentralNodes(centralNodes) {
        const panel = document.getElementById('graph-central-nodes-panel');
        if (!panel || !centralNodes) return;

        let html = '<div class="space-y-4">';

        // Most Influential
        if (centralNodes.most_influential && centralNodes.most_influential.length > 0) {
            html += `
                <div>
                    <h4 class="text-sm font-semibold text-gray-900 mb-2">Most Influential</h4>
                    <div class="space-y-2">
                        ${centralNodes.most_influential.slice(0, 5).map(node => `
                            <div class="flex items-center justify-between p-2 bg-gray-50 rounded">
                                <span class="text-sm text-gray-700 truncate flex-1">${node.label}</span>
                                <span class="text-xs text-gray-500 ml-2">${node.score.toFixed(3)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        panel.innerHTML = html;
    }

    displayCommunities(communities) {
        const panel = document.getElementById('graph-communities-panel');
        if (!panel || !communities) return;

        panel.innerHTML = communities.slice(0, 5).map((community, idx) => `
            <div class="p-3 bg-purple-50 rounded-lg border border-purple-200">
                <div class="flex items-center justify-between mb-1">
                    <span class="text-sm font-semibold text-gray-900">Cluster ${idx + 1}</span>
                    <span class="text-xs text-gray-500">${community.size} nodes</span>
                </div>
                <p class="text-xs text-gray-600">${community.theme}</p>
            </div>
        `).join('');
    }

    showLoading() {
        this.container.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="text-center">
                    <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                    <p class="mt-4 text-gray-600">Building knowledge graph...</p>
                </div>
            </div>
        `;
    }

    showError(message) {
        this.container.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="text-center p-6 bg-red-50 rounded-lg border border-red-200 max-w-md">
                    <p class="text-red-700">${message}</p>
                </div>
            </div>
        `;
    }

    // Drag handlers
    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Initialize graph visualizer when needed
let graphVisualizer = null;

function initGraphVisualizer() {
    if (!graphVisualizer) {
        graphVisualizer = new GraphVisualizer('graph-container');
    }
    return graphVisualizer;
}
