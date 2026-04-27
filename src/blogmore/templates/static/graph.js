(function () {
    'use strict';

    /** Force-graph CDN URL (loaded once, only on this page). */
    var FORCE_GRAPH_CDN = 'https://unpkg.com/force-graph';

    /** Base size (radius-equivalent) used when drawing custom node shapes. */
    var NODE_SIZE = 6;

    /** Node colour palette. */
    var NODE_COLORS = {
        post:     '#4299e1',
        tag:      '#f59e0b',
        category: '#48bb78'
    };

    /** Return colours appropriate for the currently active theme. */
    function getThemeColors() {
        var isDark = (
            document.documentElement.getAttribute('data-theme') === 'dark' ||
            (
                !document.documentElement.getAttribute('data-theme') &&
                window.matchMedia &&
                window.matchMedia('(prefers-color-scheme: dark)').matches
            )
        );
        return {
            background: isDark ? '#1a1a1a' : '#ffffff',
            link:       isDark ? '#555555' : '#cccccc',
            label:      isDark ? '#e0e0e0' : '#333333'
        };
    }

    /** Graph data injected by the page before this script is loaded. */
    var GRAPH_DATA = window.GRAPH_DATA || { nodes: [], links: [] };

    /** Global reference to the ForceGraph instance, updated after init. */
    var graphInstance = null;

    /* -------------------------------------------------------------------------
     * Highlight state
     * ---------------------------------------------------------------------- */

    /** Set of node objects that are currently highlighted. */
    var highlightNodes = new Set();

    /** Set of link objects whose edges are currently highlighted. */
    var highlightLinks = new Set();

    /** The single node that was clicked to initiate the current highlight. */
    var selectedNode = null;

    /** Update highlight sets from a newly selected node (or clear if null). */
    function selectNode(node) {
        highlightNodes.clear();
        highlightLinks.clear();
        selectedNode = node;

        if (!node || !graphInstance) { return; }

        highlightNodes.add(node);

        /* Walk resolved link objects to find directly connected edges. */
        graphInstance.graphData().links.forEach(function (link) {
            if (link.source === node || link.target === node) {
                highlightLinks.add(link);
                highlightNodes.add(link.source);
                highlightNodes.add(link.target);
            }
        });
    }

    /* -------------------------------------------------------------------------
     * Custom node drawing
     * ---------------------------------------------------------------------- */

    /**
     * Draw a single node on the canvas using the shape appropriate for its
     * type.  Posts use a square, tags a circle, and categories an upward-
     * pointing triangle.  Nodes that are not part of the current selection
     * are dimmed.  Labels are painted when the viewport zoom exceeds 1.5×.
     */
    function drawNode(node, ctx, globalScale) {
        var hasSelection = highlightNodes.size > 0;
        var isHighlighted = highlightNodes.has(node);
        var dimmed = hasSelection && !isHighlighted;
        var color = NODE_COLORS[node.type] || '#888888';
        var size = NODE_SIZE;

        ctx.save();

        if (dimmed) { ctx.globalAlpha = 0.15; }

        ctx.fillStyle = color;
        ctx.beginPath();

        if (node.type === 'post') {
            /* Square */
            ctx.rect(node.x - size, node.y - size, size * 2, size * 2);
        } else if (node.type === 'category') {
            /* Upward-pointing equilateral triangle */
            ctx.moveTo(node.x, node.y - size * 1.15);
            ctx.lineTo(node.x + size, node.y + size * 0.7);
            ctx.lineTo(node.x - size, node.y + size * 0.7);
            ctx.closePath();
        } else {
            /* Circle (tags) */
            ctx.arc(node.x, node.y, size, 0, Math.PI * 2);
        }

        ctx.fill();

        /* Highlight ring around the selected node and its direct neighbours. */
        if (!dimmed && hasSelection && isHighlighted) {
            ctx.strokeStyle = (node === selectedNode)
                ? 'rgba(255,255,255,0.95)'
                : 'rgba(255,255,255,0.55)';
            ctx.lineWidth = 2 / globalScale;
            ctx.stroke();
        }

        /* Label — only when zoomed in enough. */
        if (globalScale >= 1.5) {
            var label = node.label || '';
            var fontSize = 10 / globalScale;
            var themeColors = getThemeColors();
            ctx.font = fontSize + 'px Sans-Serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillStyle = themeColors.label;
            if (dimmed) { ctx.globalAlpha = 0.15; }
            ctx.fillText(label, node.x, node.y + size + 1 / globalScale);
        }

        ctx.restore();
    }

    /**
     * Paint the pointer-detection area for a node (must match the shape drawn
     * by drawNode so that click/hover hit-testing works correctly for
     * non-circular shapes).
     */
    function paintPointerArea(node, color, ctx) {
        var size = NODE_SIZE;
        ctx.fillStyle = color;
        ctx.beginPath();

        if (node.type === 'post') {
            ctx.rect(node.x - size, node.y - size, size * 2, size * 2);
        } else if (node.type === 'category') {
            ctx.moveTo(node.x, node.y - size * 1.15);
            ctx.lineTo(node.x + size, node.y + size * 0.7);
            ctx.lineTo(node.x - size, node.y + size * 0.7);
            ctx.closePath();
        } else {
            ctx.arc(node.x, node.y, size, 0, Math.PI * 2);
        }

        ctx.fill();
    }

    /* -------------------------------------------------------------------------
     * Link colour / width / particle helpers (called per-frame by force-graph)
     * ---------------------------------------------------------------------- */

    function getLinkColor(link) {
        if (highlightLinks.has(link)) { return 'rgba(255,255,255,0.8)'; }
        return getThemeColors().link;
    }

    function getLinkWidth(link) {
        return highlightLinks.has(link) ? 2 : 1;
    }

    function getParticleWidth(link) {
        return highlightLinks.has(link) ? 4 : 0;
    }

    /* -------------------------------------------------------------------------
     * Rich hover tooltip
     * ---------------------------------------------------------------------- */

    /**
     * Escape a string for safe insertion into HTML.
     *
     * @param {*} value - Value to escape (coerced to string).
     * @returns {string} HTML-escaped string.
     */
    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /**
     * Build an HTML string for the hover tooltip of a graph node.
     *
     * Category and tag nodes display the name and post count.  Post nodes
     * display the title, optional date, optional description, and an optional
     * thumbnail of the cover image.
     *
     * @param {Object} node - The graph node object.
     * @returns {string} HTML markup for the tooltip.
     */
    function buildNodeTooltip(node) {
        var html = '<div class="graph-floater">';

        if (node.type === 'category') {
            html += '<strong class="graph-floater-title">' +
                        escapeHtml(node.label) +
                    '</strong>';
            var cp = node.post_count || 0;
            html += '<span class="graph-floater-meta">' +
                        cp + ' post' + (cp !== 1 ? 's' : '') +
                    '</span>';

        } else if (node.type === 'tag') {
            html += '<strong class="graph-floater-title">' +
                        escapeHtml(node.label) +
                    '</strong>';
            var tp = node.post_count || 0;
            html += '<span class="graph-floater-meta">' +
                        tp + ' post' + (tp !== 1 ? 's' : '') +
                    '</span>';

        } else {
            /* Post node */
            html += '<strong class="graph-floater-title">' +
                        escapeHtml(node.label) +
                    '</strong>';
            if (node.date) {
                html += '<span class="graph-floater-date">' +
                            escapeHtml(node.date) +
                        '</span>';
            }
            if (node.cover) {
                html += '<img class="graph-floater-cover" src="' +
                            escapeHtml(node.cover) +
                        '" alt="" loading="lazy">';
            }
            if (node.description) {
                html += '<p class="graph-floater-desc">' +
                            escapeHtml(node.description) +
                        '</p>';
            }
        }

        html += '</div>';
        return html;
    }

    /* -------------------------------------------------------------------------
     * Graph initialisation
     * ---------------------------------------------------------------------- */

    function initGraph(container) {
        var colors = getThemeColors();
        var width  = container.clientWidth  || 800;
        var height = container.clientHeight || 500;

        /* Clear any previous canvas. */
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }

        /* Reset selection state so stale node references are discarded. */
        highlightNodes.clear();
        highlightLinks.clear();
        selectedNode = null;

        graphInstance = ForceGraph()(container)
            .width(width)
            .height(height)
            .backgroundColor(colors.background)
            .graphData(GRAPH_DATA)
            .nodeId('id')
            .nodeLabel(buildNodeTooltip)  /* rich HTML floater on hover */
            .nodeRelSize(NODE_SIZE)
            .nodeCanvasObjectMode(function () { return 'replace'; })
            .nodeCanvasObject(drawNode)
            .nodePointerAreaPaint(paintPointerArea)
            .linkColor(getLinkColor)
            .linkWidth(getLinkWidth)
            .linkDirectionalParticles(4)                    /* emitted for every link; */
            .linkDirectionalParticleWidth(getParticleWidth) /* width 0 hides them unless highlighted */
            .onNodeClick(function (node) {
                if (selectedNode === node) {
                    /* Second click on the same node — navigate to it. */
                    if (node.url) { window.location.href = node.url; }
                } else {
                    selectNode(node);
                }
            })
            .onBackgroundClick(function () {
                selectNode(null);
            })
            .onNodeDragEnd(function (node) {
                /* Pin the node at its released position so it does not
                 * snap back when the simulation continues. */
                node.fx = node.x;
                node.fy = node.y;
            });
    }

    /* -------------------------------------------------------------------------
     * Resize / colour helpers
     * ---------------------------------------------------------------------- */

    function resizeGraph() {
        if (!graphInstance) { return; }
        var container = document.getElementById('graph-container');
        if (!container) { return; }
        graphInstance.width(container.clientWidth);
        graphInstance.height(container.clientHeight);
    }

    function updateGraphColors() {
        if (!graphInstance) { return; }
        graphInstance.backgroundColor(getThemeColors().background);
        /* linkColor and nodeCanvasObject already call getThemeColors() on
         * every render frame, so they will pick up the new theme
         * automatically without any further intervention. */
    }

    /* -------------------------------------------------------------------------
     * Full-screen toggle
     * ---------------------------------------------------------------------- */

    function setupFullscreenToggle() {
        var btn = document.getElementById('graph-fullscreen-btn');
        if (!btn) { return; }

        btn.addEventListener('click', function () {
            var active = document.body.classList.toggle('graph-fullscreen-active');
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
            setTimeout(resizeGraph, 50);
        });

        /* Keyboard shortcut: Escape to exit full-screen. */
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' &&
                    document.body.classList.contains('graph-fullscreen-active')) {
                document.body.classList.remove('graph-fullscreen-active');
                btn.setAttribute('aria-pressed', 'false');
                setTimeout(resizeGraph, 50);
            }
        });
    }

    /* -------------------------------------------------------------------------
     * Script loading / bootstrap
     * ---------------------------------------------------------------------- */

    function loadAndInit() {
        var container = document.getElementById('graph-container');
        if (!container) { return; }

        if (typeof ForceGraph !== 'undefined') {
            initGraph(container);
            return;
        }

        var script = document.createElement('script');
        script.src = FORCE_GRAPH_CDN;
        script.async = true;
        script.onload = function () { initGraph(container); };
        script.onerror = function () {
            container.textContent =
                'Graph could not be loaded. Please check your internet connection.';
        };
        document.head.appendChild(script);
    }

    /* Resize on window resize (debounced). */
    var resizeTimer = null;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(resizeGraph, 150);
    });

    /* Re-apply background colour when the theme toggle fires. */
    if (window.MutationObserver) {
        new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.attributeName === 'data-theme') {
                    updateGraphColors();
                }
            });
        }).observe(document.documentElement, { attributes: true });
    }

    setupFullscreenToggle();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAndInit);
    } else {
        loadAndInit();
    }
})();
