/**
 * Theme switching functionality for BlogMore
 * Handles dark/light mode toggle with cookie-based persistence
 * Respects system preference by default
 */

(function() {
    'use strict';

    const THEME_COOKIE_NAME = 'blogmore-theme';
    const THEME_COOKIE_DAYS = 365;
    
    /**
     * Get a cookie value by name
     * @param {string} name - Cookie name
     * @returns {string|null} Cookie value or null if not found
     */
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }
    
    /**
     * Set a cookie
     * @param {string} name - Cookie name
     * @param {string} value - Cookie value
     * @param {number} days - Expiration in days
     */
    function setCookie(name, value, days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = `expires=${date.toUTCString()}`;
        // Add Secure attribute if site is served over HTTPS
        const secure = window.location.protocol === 'https:' ? ';Secure' : '';
        document.cookie = `${name}=${value};${expires};path=/;SameSite=Lax${secure}`;
    }
    
    /**
     * Get the system's preferred color scheme
     * @returns {string} 'dark' or 'light'
     */
    function getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    /**
     * Get the current theme (from cookie or system preference)
     * @returns {string} 'dark' or 'light'
     */
    function getCurrentTheme() {
        const savedTheme = getCookie(THEME_COOKIE_NAME);
        if (savedTheme) {
            return savedTheme;
        }
        return getSystemTheme();
    }
    
    /**
     * Apply the theme to the document
     * @param {string} theme - 'dark' or 'light'
     */
    function applyTheme(theme) {
        const html = document.documentElement;
        if (theme === 'dark' || theme === 'light') {
            html.setAttribute('data-theme', theme);
        } else {
            html.removeAttribute('data-theme');
        }
    }
    
    /**
     * Toggle between dark and light themes
     */
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setCookie(THEME_COOKIE_NAME, newTheme, THEME_COOKIE_DAYS);
        applyTheme(newTheme);
    }
    
    /**
     * Initialize theme on page load
     */
    function initTheme() {
        const savedTheme = getCookie(THEME_COOKIE_NAME);
        if (savedTheme) {
            // User has manually selected a theme
            applyTheme(savedTheme);
        } else {
            // No saved preference, apply system preference
            applyTheme(getSystemTheme());
        }
    }
    
    /**
     * Set up theme toggle button
     */
    function setupThemeToggle() {
        const toggleButton = document.querySelector('.theme-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', toggleTheme);
        }
    }
    
    // Initialize theme immediately to prevent flash
    initTheme();
    
    // Set up toggle button after DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupThemeToggle);
    } else {
        setupThemeToggle();
    }
    
    // Listen for system theme changes when no manual preference is set
    // Note: Event listener persists for the lifetime of the page, which is acceptable
    // for a static site where pages are regenerated on each navigation
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            const savedTheme = getCookie(THEME_COOKIE_NAME);
            if (!savedTheme) {
                // Only update if user hasn't manually set a preference
                const newTheme = e.matches ? 'dark' : 'light';
                applyTheme(newTheme);
            }
        });
    }
})();
