// assets/couture-search-redirect.js
(function() {
  function hijackSearchForms() {
    // Find all search forms on the page that point to the default search page
    const searchForms = document.querySelectorAll('form[action="/search"]');
    
    searchForms.forEach(form => {
      form.addEventListener('submit', function(event) {
        // Stop the form from submitting normally
        event.preventDefault();
        
        // Find the search input field within this form
        const searchInput = form.querySelector('input[name="q"]');
        if (searchInput) {
          const query = searchInput.value.trim();
          if (query) {
            // Redirect the user to our new custom search page with the query
            window.location.href = `/pages/couture-search?q=${encodeURIComponent(query)}`;
          }
        }
      });
    });
  }
  
  // Run the function on the initial page load
  hijackSearchForms();
  
  // Shopify themes sometimes re-render sections, so we'll re-run our function
  // when Shopify signals that a section has been loaded or changed.
  document.addEventListener('shopify:section:load', hijackSearchForms);
})();