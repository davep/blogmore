/**
 * Client-side search for BlogMore static sites.
 *
 * Loads /search_index.json on page load and performs in-browser
 * full-text search across post titles and content.  No external
 * services or server-side processing are required.
 */

(function () {
    'use strict';

    /** @type {Array<{title: string, url: string, date: string, content: string}>|null} */
    let searchIndex = null;

    /**
     * Fetch and cache the search index JSON.
     * @returns {Promise<Array>} Resolves with the search index array.
     */
    function loadIndex() {
        if (searchIndex !== null) {
            return Promise.resolve(searchIndex);
        }
        return fetch('/search_index.json')
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Could not load search index');
                }
                return response.json();
            })
            .then(function (data) {
                searchIndex = data;
                return data;
            });
    }

    /**
     * Escape a string for safe use inside a RegExp.
     * @param {string} str
     * @returns {string}
     */
    function escapeRegExp(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Wrap all occurrences of a query term inside a text string with
     * <mark> tags.  The search is case-insensitive.
     * @param {string} text - The plain text to highlight.
     * @param {string} query - The search term.
     * @returns {string} HTML string with matches wrapped in <mark>.
     */
    function highlight(text, query) {
        if (!query) {
            return escapeHtml(text);
        }
        return escapeHtml(text).replace(
            new RegExp('(' + escapeRegExp(escapeHtml(query)) + ')', 'gi'),
            '<mark>$1</mark>'
        );
    }

    /**
     * Escape HTML special characters.
     * @param {string} str
     * @returns {string}
     */
    function escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * Extract a short snippet of text around the first occurrence of the
     * query term.
     * @param {string} content - Full plain-text content of the post.
     * @param {string} query - Search term.
     * @param {number} [radius=120] - Characters of context on each side.
     * @returns {string} A short context snippet.
     */
    function snippet(content, query, radius) {
        radius = radius || 120;
        const lower = content.toLowerCase();
        const pos = lower.indexOf(query.toLowerCase());
        if (pos === -1) {
            return content.slice(0, radius * 2);
        }
        const start = Math.max(0, pos - radius);
        const end = Math.min(content.length, pos + query.length + radius);
        let text = content.slice(start, end);
        if (start > 0) {
            text = '\u2026' + text;
        }
        if (end < content.length) {
            text = text + '\u2026';
        }
        return text;
    }

    /**
     * Search the index for the given query string.
     * @param {Array} index - The search index array.
     * @param {string} query - The search term (case-insensitive).
     * @returns {Array} Matching entries.
     */
    function search(index, query) {
        const lower = query.toLowerCase().trim();
        if (!lower) {
            return [];
        }
        return index.filter(function (entry) {
            return (
                entry.title.toLowerCase().includes(lower) ||
                entry.content.toLowerCase().includes(lower)
            );
        });
    }

    /**
     * Render search results into the results container.
     * @param {Array} results - Array of matching index entries.
     * @param {string} query - The original search term (for highlighting).
     * @param {HTMLElement} container - The DOM element to render into.
     */
    function renderResults(results, query, container) {
        if (results.length === 0) {
            container.innerHTML =
                '<p class="search-no-results">No results found.</p>';
            return;
        }

        const items = results.map(function (entry) {
            const titleHtml = highlight(entry.title, query);
            const contentSnippet = snippet(entry.content, query);
            const snippetHtml = highlight(contentSnippet, query);
            const dateHtml = entry.date
                ? '<span class="search-result-date">' +
                  escapeHtml(entry.date) +
                  '</span>'
                : '';
            return (
                '<li class="search-result">' +
                '<h3 class="search-result-title">' +
                '<a href="' +
                escapeHtml(entry.url) +
                '">' +
                titleHtml +
                '</a>' +
                '</h3>' +
                dateHtml +
                '<p class="search-result-snippet">' +
                snippetHtml +
                '</p>' +
                '</li>'
            );
        });

        container.innerHTML =
            '<p class="search-result-count">' +
            results.length +
            ' result' +
            (results.length === 1 ? '' : 's') +
            ' found</p>' +
            '<ul class="search-results-list">' +
            items.join('') +
            '</ul>';
    }

    /**
     * Initialise search on the page.
     */
    function init() {
        const form = document.getElementById('search-form');
        const input = document.getElementById('search-input');
        const resultsContainer = document.getElementById('search-results');

        if (!form || !input || !resultsContainer) {
            return;
        }

        // Pre-load the index as soon as the page is ready so the first
        // search feels instant.
        loadIndex().catch(function () {
            resultsContainer.innerHTML =
                '<p class="search-error">Search index could not be loaded.</p>';
        });

        // Run a search whenever the input changes.
        function runSearch() {
            const query = input.value;
            if (!query.trim()) {
                resultsContainer.innerHTML = '';
                return;
            }
            loadIndex()
                .then(function (index) {
                    const results = search(index, query);
                    renderResults(results, query, resultsContainer);
                })
                .catch(function () {
                    resultsContainer.innerHTML =
                        '<p class="search-error">Search index could not be loaded.</p>';
                });
        }

        input.addEventListener('input', runSearch);

        // Also handle form submission to prevent page reload.
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            runSearch();
        });

        // If there is a pre-filled query (e.g. from a ?q= URL parameter),
        // run the search immediately.
        const params = new URLSearchParams(window.location.search);
        const initialQuery = params.get('q');
        if (initialQuery) {
            input.value = initialQuery;
            runSearch();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
