(function () {
    'use strict';
    const API_URL = 'https://d768bf47be7c.ngrok-free.app/api/reco/autosuggest/results';
    let ui = {}; // A cache for our UI elements

    /**
     * A simple utility to delay function execution.
     */
    const debounce = (func, delay) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), delay);
        };
    };

    /**
     * Forcefully removes all common scroll-locking classes from the body and html tags.
     * This is the key to preventing the page freeze on themes like Horizon.
     */
    const unlockScroll = () => {
        const lockClasses = ['overflow-hidden', 'scroll-lock', 'modal-open', 'no-scroll', 'noscroll', 'fixed-position'];
        document.body.classList.remove(...lockClasses);
        document.documentElement.classList.remove(...lockClasses);
        
        // Force override any inline styles that might lock scroll
        document.body.style.overflow = 'visible !important';
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.left = '';
        document.body.style.right = '';
        document.body.style.bottom = '';
        document.body.style.height = '';
        document.body.style.maxHeight = '';
        document.documentElement.style.overflow = 'visible !important';
        
        // Remove any modal backdrop overlays that might be preventing interaction
        const overlays = document.querySelectorAll('.modal-backdrop, .search-modal-backdrop, [class*="backdrop"], .overlay');
        overlays.forEach(overlay => {
            overlay.style.display = 'none';
            overlay.remove();
        });
        
        // Enable pointer events on body
        document.body.style.pointerEvents = '';
        document.documentElement.style.pointerEvents = '';
    };

    /**
     * Closes any existing search modals that might be open
     */
    const closeExistingSearchModals = () => {
        // Close dialog-component modals
        const searchModals = document.querySelectorAll('dialog-component dialog[open], .search-modal dialog[open]');
        searchModals.forEach(modal => {
            modal.removeAttribute('open');
            modal.close && modal.close();
        });

        // Hide any search modal containers
        const modalContainers = document.querySelectorAll('.search-modal, dialog-component');
        modalContainers.forEach(container => {
            container.style.display = 'none';
            container.hidden = true;
        });

        // Trigger close events on predictive search components
        const predictiveSearches = document.querySelectorAll('predictive-search-component');
        predictiveSearches.forEach(search => {
            // Try to find and trigger close buttons
            const closeButtons = search.querySelectorAll('[aria-label*="close" i], .predictive-search__close-modal-button');
            closeButtons.forEach(btn => {
                if (btn.click) btn.click();
            });
        });
    };

    /**
     * Finds all potential search triggers on the page, clones them to strip
     * existing event listeners, and attaches our own handler.
     */
    const hijackSearchTriggers = () => {
        const selectors = 'a[href*="/search"], button[aria-label*="search" i], .search-action, summary[aria-label*="search" i]';
        document.querySelectorAll(selectors).forEach(trigger => {
            // Skip elements we've already processed
            if (trigger.dataset.coutureHijacked) return;

            const clone = trigger.cloneNode(true);
            trigger.parentNode.replaceChild(clone, trigger);
            clone.dataset.coutureHijacked = true;

            // Attach our master click handler
            clone.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();

                // First close any existing search modals
                closeExistingSearchModals();
                
                // Then unlock scroll
                unlockScroll();
                
                // Show our custom search
                showCustomSearch(clone);
            }, true);
        });
    };

    /**
     * Creates our custom search bar and results popup ONCE and keeps them hidden.
     */
    const createCustomSearchUI = () => {
        if (ui.container) return; // Only create the UI once

        ui.container = document.createElement('div');
        ui.container.className = 'couture-custom-search-container';
        ui.container.style.display = 'none'; // Hidden by default
        ui.container.style.position = 'fixed';
        ui.container.style.zIndex = '99999'; // Even higher z-index
        ui.container.style.backgroundColor = 'white';
        ui.container.style.border = '1px solid #ccc';
        ui.container.style.borderRadius = '8px';
        ui.container.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        ui.container.style.minWidth = '300px';
        ui.container.style.maxWidth = '600px';
        ui.container.style.pointerEvents = 'auto'; // Ensure pointer events work

        ui.input = document.createElement('input');
        ui.input.type = 'search';
        ui.input.placeholder = 'Search...';
        ui.input.className = 'couture-custom-input';
        ui.input.style.width = '100%';
        ui.input.style.padding = '12px';
        ui.input.style.border = 'none';
        ui.input.style.outline = 'none';
        ui.input.style.fontSize = '16px';
        ui.input.style.borderRadius = '8px 8px 0 0';

        ui.resultsPopup = document.createElement('div');
        ui.resultsPopup.className = 'couture-autocomplete-popup';
        ui.resultsPopup.style.display = 'none';
        ui.resultsPopup.style.maxHeight = '400px';
        ui.resultsPopup.style.overflowY = 'auto';
        ui.resultsPopup.style.borderTop = '1px solid #eee';

        ui.container.append(ui.input, ui.resultsPopup);
        document.body.appendChild(ui.container);

        setupEventListeners();
        addCustomStyles();
    };

    /**
     * Add custom styles for the search UI
     */
    const addCustomStyles = () => {
        if (document.getElementById('couture-search-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'couture-search-styles';
        styles.textContent = `
            .couture-autocomplete-wrapper {
                display: flex;
                min-height: 200px;
            }
            .couture-autocomplete-wrapper .left-panel {
                flex: 1;
                padding: 15px;
                border-right: 1px solid #eee;
            }
            .couture-autocomplete-wrapper .right-panel {
                flex: 2;
                padding: 15px;
            }
            .couture-autocomplete-wrapper h5 {
                margin: 0 0 10px 0;
                font-size: 14px;
                font-weight: 600;
                color: #333;
            }
            .couture-autocomplete-wrapper ul {
                list-style: none;
                margin: 0;
                padding: 0;
            }
            .couture-autocomplete-wrapper li {
                padding: 8px 0;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
            }
            .couture-autocomplete-wrapper li:hover {
                background-color: #f8f8f8;
            }
            .suggestion-icon {
                width: 14px;
                height: 14px;
                margin-right: 8px;
                vertical-align: middle;
            }
            .couture-product-list {
                display: grid;
                grid-template-columns: 1fr;
                gap: 10px;
            }
            .couture-product-card {
                border: 1px solid #eee;
                border-radius: 4px;
                overflow: hidden;
            }
            .couture-product-card a {
                display: flex;
                text-decoration: none;
                color: inherit;
            }
            .couture-product-image {
                width: 60px;
                height: 60px;
                object-fit: cover;
                flex-shrink: 0;
            }
            .couture-product-details {
                padding: 10px;
                flex: 1;
            }
            .couture-product-title {
                font-size: 14px;
                margin-bottom: 4px;
                display: block;
            }
            .couture-product-price {
                font-weight: 600;
                color: #333;
            }
            .couture-loading {
                padding: 20px;
                text-align: center;
                color: #666;
            }
        `;
        document.head.appendChild(styles);
    };

    /**
     * Positions and displays our custom search UI right below the clicked icon.
     */
    const showCustomSearch = (clickedEl) => {
        const rect = clickedEl.getBoundingClientRect();
        ui.container.style.left = `${rect.left}px`;
        ui.container.style.top = `${rect.bottom + 8}px`;
        ui.container.style.display = 'block';
        ui.container.style.pointerEvents = 'auto';
        ui.input.value = '';
        ui.resultsPopup.style.display = 'none';
        
        // Ensure scroll is unlocked immediately and repeatedly
        unlockScroll();
        
        // Focus the input with a slight delay to ensure it's rendered
        setTimeout(() => {
            ui.input.focus();
            ui.input.click(); // Sometimes click is needed for themes that hijack focus
            unlockScroll(); // Unlock again after focus
        }, 50);
        
        // Continue unlocking scroll for a bit to combat theme interference
        const unlockInterval = setInterval(() => {
            unlockScroll();
        }, 100);
        
        setTimeout(() => {
            clearInterval(unlockInterval);
        }, 2000);
    };

    const hideCustomSearch = () => {
        if (ui.container) {
            ui.container.style.display = 'none';
            ui.input.blur(); // Remove focus from input
        }
        
        // Aggressively unlock scroll when hiding
        unlockScroll();
        
        // Continue unlocking for a bit to ensure it sticks
        const unlockInterval = setInterval(() => {
            unlockScroll();
        }, 100);
        
        setTimeout(() => {
            clearInterval(unlockInterval);
            // Final unlock after theme has settled
            unlockScroll();
        }, 1000);
    };

    /**
     * Sets up all the necessary event listeners for our custom search input.
     */
    const setupEventListeners = () => {
        const debouncedSearch = debounce(query => callSearchApi(query), 300);

        ui.input.addEventListener('input', () => {
            const query = ui.input.value.trim();
            if (query.length < 3) {
                ui.resultsPopup.style.display = 'none';
                return;
            }
            debouncedSearch(query);
        });

        // Prevent input from losing focus due to theme interference
        ui.input.addEventListener('focus', (e) => {
            e.stopPropagation();
            // Keep the search container visible when input is focused
            if (ui.container) {
                ui.container.style.display = 'block';
            }
        }, true);

        ui.input.addEventListener('blur', (e) => {
            // Don't hide immediately on blur, let click handlers decide
            setTimeout(() => {
                if (ui.input !== document.activeElement && !ui.container.contains(document.activeElement)) {
                    // Only hide if focus moved completely outside our container
                    const relatedTarget = e.relatedTarget;
                    if (!relatedTarget || !ui.container.contains(relatedTarget)) {
                        // hideCustomSearch(); // Commented out to prevent premature hiding
                    }
                }
            }, 150);
        });

        // Prevent theme from interfering with input events
        ui.input.addEventListener('keydown', (e) => {
            e.stopPropagation(); // Prevent theme handlers from interfering
            
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = ui.input.value.trim();
                if (query) window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
            if (e.key === 'Escape') {
                hideCustomSearch();
            }
        }, true);

        ui.input.addEventListener('keyup', (e) => {
            e.stopPropagation(); // Prevent theme handlers from interfering
        }, true);

        // Hide the search bar if the user clicks anywhere else on the page
        document.addEventListener('click', e => {
            const isTrigger = e.target.closest('[data-couture-hijacked]');
            const isSearchContainer = ui.container && ui.container.contains(e.target);
            const isSearchInput = e.target === ui.input;
            
            if (ui.container && ui.container.style.display === 'block' && !isSearchContainer && !isTrigger && !isSearchInput) {
                hideCustomSearch();
            }
        }, true); // Use capture phase to prevent theme interference

        // Prevent any scroll locking when our search is active
        document.addEventListener('keydown', (e) => {
            if (ui.container && ui.container.style.display === 'block') {
                unlockScroll();
            }
        });

        // Prevent theme from locking scroll through various mechanisms
        document.addEventListener('scroll', unlockScroll, { passive: true });
        document.addEventListener('touchmove', unlockScroll, { passive: true });
        
        // Override any body style changes that might lock scroll
        const bodyObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    if (ui.container && ui.container.style.display === 'block') {
                        setTimeout(unlockScroll, 0);
                    }
                }
            });
        });
        
        bodyObserver.observe(document.body, {
            attributes: true,
            attributeFilter: ['style', 'class']
        });
        
        bodyObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['style', 'class']
        });
    };

    // --- API and Rendering Functions (Largely Unchanged) ---

    const callSearchApi = async (query) => {
        ui.resultsPopup.style.display = 'block';
        ui.resultsPopup.innerHTML = '<div class="couture-loading">Searching...</div>';
        try {
            const response = await fetch(`${API_URL}?q=${encodeURIComponent(query)}`, { 
                headers: { 'ngrok-skip-browser-warning': 'true' } 
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            renderAutocomplete(data);
        } catch (error) {
            console.error("Couture Search API Error:", error);
            ui.resultsPopup.style.display = 'none';
        }
    };

    const renderAutocomplete = (data) => {
        if (!data || (!data.suggestions?.length && !data.categories?.length && !data.product_ids?.length)) {
            ui.resultsPopup.style.display = 'none';
            return;
        }

        const layoutHtml = `
            <div class="couture-autocomplete-wrapper">
                <div class="left-panel">
                    <div class="suggestions-container"></div>
                    <div class="categories-container"></div>
                </div>
                <div class="right-panel">
                    <div class="products-container"></div>
                </div>
            </div>`;
        ui.resultsPopup.innerHTML = layoutHtml;

        const suggestionsContainer = ui.resultsPopup.querySelector('.suggestions-container');
        if (data.suggestions?.length) {
            const searchIconSvg = `<svg class="suggestion-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>`;
            suggestionsContainer.innerHTML = `<h5>Suggestions</h5><ul>${data.suggestions.map(s => `<li>${searchIconSvg}<span>${s}</span></li>`).join('')}</ul>`;
            suggestionsContainer.addEventListener('click', e => {
                const li = e.target.closest('li');
                if (li) window.location.href = `/search?q=${encodeURIComponent(li.textContent.trim())}`;
            });
        }

        const categoriesContainer = ui.resultsPopup.querySelector('.categories-container');
        if (data.categories?.length) {
            categoriesContainer.innerHTML = `<h5>Categories</h5><ul>${data.categories.map(c => `<li>${c.name} (${c.count})</li>`).join('')}</ul>`;
        }

        const productsContainer = ui.resultsPopup.querySelector('.products-container');
        if (data.product_ids?.length) {
            fetchProductData(data.product_ids, productsContainer);
        } else {
            productsContainer.innerHTML = '<h5>Products</h5><div class="couture-no-products">No products found.</div>';
        }
    };

    const fetchProductData = async (handles, container) => {
        container.innerHTML = '<h5>Products</h5><div class="couture-products-loading">Loading...</div>';
        try {
            const requests = handles.slice(0, 5).map(handle => fetch(`/products/${handle}.js`));
            const products = await Promise.all((await Promise.all(requests)).map(res => res.json()));

            const productHtml = products.map(p => {
                const imgUrl = p.featured_image ? p.featured_image.replace(/(\.[\w\?]+)$/, '_100x100$1') : 'https://placehold.co/100x100/EEE/31343C?text=N/A';
                const price = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(p.price / 100);
                return `
                    <li class="couture-product-card">
                        <a href="${p.url}">
                            <img src="${imgUrl}" alt="${p.title}" class="couture-product-image"/>
                            <div class="couture-product-details">
                                <span class="couture-product-title">${p.title}</span>
                                <span class="couture-product-price">${price}</span>
                            </div>
                        </a>
                    </li>`;
            }).join('');
            container.innerHTML = `<h5>Products</h5><ul class="couture-product-list">${productHtml}</ul>`;
        } catch (error) {
            container.innerHTML = '<h5>Products</h5><div class="couture-products-error">Error loading products.</div>';
        }
    };

    /**
     * Continuously monitor and prevent theme search modals from opening
     */
    const preventThemeSearchModals = () => {
        // Monitor for any dialogs that get opened
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        // Check if it's a search modal
                        if (node.matches && (node.matches('.search-modal') || node.matches('dialog-component'))) {
                            node.style.display = 'none';
                            node.hidden = true;
                        }
                        // Check for nested search modals
                        const searchModals = node.querySelectorAll && node.querySelectorAll('.search-modal, dialog-component');
                        if (searchModals) {
                            searchModals.forEach(modal => {
                                modal.style.display = 'none';
                                modal.hidden = true;
                            });
                        }
                    }
                });

                // Check for attribute changes that might show modals
                if (mutation.type === 'attributes' && mutation.attributeName === 'open') {
                    const target = mutation.target;
                    if (target.matches && target.matches('dialog')) {
                        target.removeAttribute('open');
                        if (target.close) target.close();
                    }
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['open', 'style', 'class']
        });
    };

    /**
     * Main initialization function that kicks everything off.
     */
    const initialize = () => {
        hijackSearchTriggers();
        createCustomSearchUI();
        preventThemeSearchModals();
        
        // Ensure scroll is always unlocked
        unlockScroll();
        
        // Periodically check and unlock scroll
        setInterval(() => {
            if (ui.container && ui.container.style.display === 'block') {
                unlockScroll();
            }
        }, 1000);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Use an observer to catch any search icons that are added to the page late.
    new MutationObserver(hijackSearchTriggers).observe(document.body, { childList: true, subtree: true });

})();