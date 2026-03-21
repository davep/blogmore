/**
 * Code block enhancements for BlogMore.
 *
 * For every `.highlight` element produced by the Pygments code-hilite
 * Markdown extension this module:
 *
 *  - Inserts a header bar containing a language label (top-left) and a
 *    copy-to-clipboard button (top-right).
 *  - The language label is populated from the ``data-lang`` attribute on the
 *    wrapper ``<div>``, which is set by the custom Pygments formatter when a
 *    fenced code block specifies a language.
 *  - Clicking the copy button copies the plain-text content of the code
 *    block to the clipboard and briefly shows a check-mark icon to confirm.
 */

(function () {
    'use strict';

    /** SVG clipboard icon shown on the copy button in its default state. */
    var COPY_ICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>';

    /** SVG check-mark icon shown briefly after a successful copy. */
    var CHECK_ICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>';

    /**
     * Extract the programming language from a `.highlight` wrapper element.
     *
     * The custom Pygments formatter adds a ``data-lang`` attribute to the
     * wrapper ``<div>`` when a fenced code block specifies a language.
     * Returns an empty string when no language is recorded, or when the
     * language is ``text`` (the Pygments fallback for unspecified languages).
     *
     * @param {Element} highlightDiv - The `.highlight` wrapper element.
     * @returns {string} Language name, or empty string if not found or generic.
     */
    function getLanguage(highlightDiv) {
        const lang = highlightDiv.dataset.lang || '';
        // 'text' is the Pygments fallback when no language is specified; treat
        // it the same as no language so no label is shown.
        return lang === 'text' ? '' : lang;
    }

    /**
     * Copy a string to the clipboard.
     *
     * Uses the modern Clipboard API when available, with a `<textarea>`
     * select-and-copy fallback for older browsers.
     *
     * @param {string} text - The text to copy.
     * @param {function} onSuccess - Callback invoked on success.
     */
    function copyToClipboard(text, onSuccess) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(onSuccess).catch(function () {
                fallbackCopy(text, onSuccess);
            });
        } else {
            fallbackCopy(text, onSuccess);
        }
    }

    /**
     * Clipboard fallback using a temporary `<textarea>` element.
     *
     * @param {string} text - The text to copy.
     * @param {function} onSuccess - Callback invoked on success.
     */
    function fallbackCopy(text, onSuccess) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            onSuccess();
        } catch (_err) {
            // Copy failed — do nothing.
        }
        document.body.removeChild(textarea);
    }

    /**
     * Attach the header bar (language label + copy button) to one code block.
     *
     * @param {Element} highlightDiv - The `.highlight` wrapper element.
     */
    function setupCodeBlock(highlightDiv) {
        const pre = highlightDiv.querySelector('pre');
        if (!pre) {
            return;
        }

        const language = getLanguage(highlightDiv);

        const header = document.createElement('div');
        header.className = 'code-block-header';

        // Language label (top-left).
        const langLabel = document.createElement('span');
        langLabel.className = 'code-block-lang';
        langLabel.textContent = language;
        langLabel.setAttribute('aria-hidden', 'true');
        header.appendChild(langLabel);

        // Copy-to-clipboard button (top-right).
        const copyButton = document.createElement('button');
        copyButton.className = 'code-block-copy';
        copyButton.setAttribute('type', 'button');
        copyButton.setAttribute('aria-label', 'Copy code to clipboard');
        copyButton.innerHTML = COPY_ICON_SVG;

        copyButton.addEventListener('click', function () {
            const text = pre.textContent || '';
            copyToClipboard(text, function () {
                copyButton.innerHTML = CHECK_ICON_SVG;
                copyButton.classList.add('copied');
                setTimeout(function () {
                    copyButton.innerHTML = COPY_ICON_SVG;
                    copyButton.classList.remove('copied');
                }, 2000);
            });
        });

        header.appendChild(copyButton);

        // Insert the header before the <pre> element.
        highlightDiv.insertBefore(header, pre);
    }

    /**
     * Set up copy buttons and language labels on all code blocks in the page.
     */
    function setupAllCodeBlocks() {
        document.querySelectorAll('.highlight').forEach(setupCodeBlock);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupAllCodeBlocks);
    } else {
        setupAllCodeBlocks();
    }
})();
