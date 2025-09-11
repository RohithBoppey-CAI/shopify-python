(function () {
    'use strict';

    const API_URL = 'https://d768bf47be7c.ngrok-free.app/api/reco/autosuggest/results';

    // This renders the main layout (suggestions, categories)
    function renderAutocomplete(data, popup) {
        if (!data || (!data.suggestions?.length && !data.categories?.length && !data.product_ids?.length)) {
            popup.style.display = 'none';
            return;
        }

        // This HTML structure is taken directly from your Magento logic
        let html = `<div class="couture-autocomplete-wrapper">
                    <div class="left-panel">
                        <div class="suggestions-container"></div>
                        <div class="categories-container" style="margin-top: 20px;"></div>
                    </div>
                    <div class="right-panel">
                        <div class="products-container"></div>
                    </div>
                </div>`;
        popup.innerHTML = html;

        // Render suggestions
        const suggestionsContainer = popup.querySelector('.suggestions-container');
        if (data.suggestions && data.suggestions.length) {
            const searchIconSvg = `<svg class="suggestion-icon" ... ></svg>`; // Your SVG code here
            suggestionsContainer.innerHTML = `<h5>Suggestions</h5><ul>${data.suggestions.map(s => `<li>${searchIconSvg}<span>${s}</span></li>`).join('')}</ul>`;


            suggestionsContainer.addEventListener('click', event => {
                const listItem = event.target.closest('li');
                if (listItem) {
                    const query = listItem.textContent.trim();
                    if (query) {
                        // Redirect to the custom search page with the clicked query
                        window.location.href = `/pages/couture-search?q=${encodeURIComponent(query)}`;
                    }
                }
            });


        }

        // Render categories
        const categoriesContainer = popup.querySelector('.categories-container');
        if (data.categories && data.categories.length) {
            categoriesContainer.innerHTML = `<h5>Categories</h5><ul>${data.categories.map(c => `<li>${c.name} (${c.count})</li>`).join('')}</ul>`;
        }

        // Fetch and render products
        const productsContainer = popup.querySelector('.products-container');
        if (data.product_ids && data.product_ids.length) {
            callProductApi(data.product_ids, productsContainer);
        } else {
            productsContainer.innerHTML = '<h5>Products</h5><div>No products to display.</div>';
        }
    }

    // This fetches Shopify product data and renders the products
    // This new version uses the theme-scraping method
    async function callProductApi(handles, container) {
        container.innerHTML = '<h5>Products</h5><div>Loading products...</div>';
        try {
            // A list of common selectors to try
            const autoSelectors = ['.grid__item', '.product-grid__item', '.card-wrapper'];

            // 1. Construct a single search URL with all the product handles
            const searchQuery = handles.map(handle => `handle:${handle}`).join(' OR ');
            const searchUrl = `/search?q=${encodeURIComponent(searchQuery)}&type=product&options[prefix]=last`;

            // 2. Fetch the pre-rendered HTML from the default search page
            const response = await fetch(searchUrl);
            if (!response.ok) throw new Error('Scraping request failed');
            const html = await response.text();
            const doc = new DOMParser().parseFromString(html, 'text/html');

            // 3. Find the product cards using our auto-detection logic
            let productElements = [];
            for (const selector of autoSelectors) {
                productElements = doc.querySelectorAll(selector);
                if (productElements.length > 0) break;
            }

            if (productElements.length === 0) throw new Error('Could not find product cards on search page.');

            // 4. Extract and inject the perfect HTML
            const productHtml = Array.from(productElements).map(el => `<li>${el.innerHTML}</li>`).join('');
            container.innerHTML = `<h5>Products</h5><ul class="couture-autocomplete-product-list">${productHtml}</ul>`;

        } catch (error) {
            console.error('Error fetching product data:', error);
            container.innerHTML = '<h5>Products</h5><div>Error loading products.</div>';
        }
    }

    // A simple debounce utility
    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // This function will contain all the logic
    // Replace the existing initializeAutocomplete function with this one
    function initializeAutocomplete(searchInput) {
        const searchForm = searchInput.closest('form');
        if (!searchForm) return;

        // 1. Create the popup and attach it to the document body
        const popup = document.createElement('div');
        popup.className = 'couture-autocomplete-popup';
        popup.style.display = 'none';
        document.body.appendChild(popup); // Attach to body, not the form

        // 2. Create a function to show and position the popup
        function showAndPositionPopup() {
            const rect = searchInput.getBoundingClientRect();
            popup.style.left = `${rect.left + window.scrollX}px`;
            popup.style.top = `${rect.bottom + window.scrollY}px`;
            popup.style.width = `${rect.width}px`; // Match the width of the search input
            popup.style.display = 'block';
        }

        const debouncedSearch = debounce(query => {
            callSearchApi(query, popup, showAndPositionPopup); // Pass the positioning function
        }, 300);

        // 3. Attach event listeners
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.trim();
            if (query.length < 3) {
                popup.style.display = 'none';
                return;
            }
            debouncedSearch(query);
        });

        // (Your form submit and document click listeners remain the same)
        searchForm.addEventListener('submit', event => { /* ... */ });
        document.addEventListener('click', event => { /* ... */ });

        // Reposition on window resize
        window.addEventListener('resize', () => {
            if (popup.style.display === 'block') {
                showAndPositionPopup();
            }
        });
    }

    // Also, make a small update to the callSearchApi function to use the new positioning function
    async function callSearchApi(query, popup, positioningFunction) {
        positioningFunction(); // Position the popup first
        popup.innerHTML = '<div>Loading...</div>';

        try {
            const response = await fetch(`${API_URL}?q=${encodeURIComponent(query)}`, {
                headers: { 'ngrok-skip-browser-warning': 'true' }
            });
            if (!response.ok) throw new Error('API request failed');
            const data = await response.json();
            renderAutocomplete(data, popup);
        } catch (error) {
            console.error('Error fetching search results:', error);
            popup.style.display = 'none';
        }
    }

    // Find all search inputs on the page and initialize them
    document.querySelectorAll('form[action="/search"] input[name="q"]').forEach(initializeAutocomplete);
})();