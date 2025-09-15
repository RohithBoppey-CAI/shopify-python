(function () {
    'use strict';
    const API_URL = 'https://d768bf47be7c.ngrok-free.app/api/reco/autosuggest/results';
    let ui = {}; // UI elements cache

    const debounce = (func, delay) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), delay);
        };
    };

    /**
     * Finds search triggers, clones them to remove theme event listeners, 
     * and attaches our own click handler.
     */
    const hijackSearchTriggers = () => {
        const selectors = 'a[href*="/search"], button[aria-label*="search" i], .search-action, summary[aria-label*="search" i]';
        document.querySelectorAll(selectors).forEach(trigger => {
            if (trigger.dataset.coutureHijacked) return;

            const clone = trigger.cloneNode(true);
            trigger.parentNode.replaceChild(clone, trigger);
            clone.dataset.coutureHijacked = true;

            clone.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                
                // CRITICAL FIX: Aggressively and persistently unlock page scrolling.
                const unlockScroll = () => {
                    document.body.style.overflow = '';
                    document.documentElement.style.overflow = '';
                    document.body.classList.remove('overflow-hidden', 'scroll-lock', 'modal-open');
                    document.documentElement.classList.remove('overflow-hidden', 'scroll-lock', 'modal-open');
                };

                unlockScroll(); // Run immediately
                setTimeout(unlockScroll, 10); // Run again after a delay to override theme scripts

                showCustomSearch(clone);
            }, true);
        });
    };

    /**
     * Creates our custom search UI elements once.
     */
    const createCustomSearchUI = () => {
        if (ui.container) return;
        
        ui.container = document.createElement('div');
        ui.container.className = 'couture-custom-search-container';
        
        ui.input = document.createElement('input');
        ui.input.type = 'search';
        ui.input.placeholder = 'Search...';
        ui.input.className = 'couture-custom-input';

        ui.resultsPopup = document.createElement('div');
        ui.resultsPopup.className = 'couture-autocomplete-popup';

        ui.container.append(ui.input, ui.resultsPopup);
        document.body.appendChild(ui.container);
        
        setupEventListeners();
    };

    /**
     * Shows and positions the custom search UI below the clicked element.
     */
    const showCustomSearch = (clickedEl) => {
        const rect = clickedEl.getBoundingClientRect();
        ui.container.style.left = `${rect.left}px`;
        ui.container.style.top = `${rect.bottom + 8}px`; 
        ui.container.style.display = 'block';
        ui.input.focus();
        ui.input.value = '';
        ui.resultsPopup.style.display = 'none';
    };

    const hideCustomSearch = () => {
        if (ui.container) ui.container.style.display = 'none';
    };
    
    /**
     * Sets up all event listeners for our custom search input.
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
        
        ui.input.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = ui.input.value.trim();
                if (query) window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
            if (e.key === 'Escape') hideCustomSearch();
        });

        document.addEventListener('click', e => {
            const isTrigger = e.target.closest('[data-couture-hijacked]');
            if (ui.container && !ui.container.contains(e.target) && !isTrigger) {
                hideCustomSearch();
            }
        });
    };
    
    /**
     * API call and rendering logic.
     */
    const callSearchApi = async (query) => {
        ui.resultsPopup.style.display = 'block';
        ui.resultsPopup.innerHTML = '<div class="couture-loading">Searching...</div>';
        try {
            const response = await fetch(`${API_URL}?q=${encodeURIComponent(query)}`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            renderAutocomplete(data);
        } catch (error) {
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
                <div class="left-panel"><div class="suggestions-container"></div><div class="categories-container"></div></div>
                <div class="right-panel"><div class="products-container"></div></div>
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
     * Main initialization logic.
     */
    const initialize = () => {
        hijackSearchTriggers();
        createCustomSearchUI();
        document.querySelectorAll('.search-modal, [id*="search-modal"], dialog[class*="search"]').forEach(m => {
            m.style.display = 'none';
            m.style.visibility = 'hidden';
        });
    };

    // Run on load and observe for changes.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
    
    new MutationObserver(hijackSearchTriggers).observe(document.body, { childList: true, subtree: true });

})();

