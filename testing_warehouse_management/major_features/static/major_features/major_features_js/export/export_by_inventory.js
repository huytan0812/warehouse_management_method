document.addEventListener("DOMContentLoaded", function() {
    const toggleFilterBarBtn = document.getElementById("toggle-filter-bar");
    const filterFormContainer = document.getElementById("filter-form-container");
    toggleFilterBarBtn.onclick = function() {
        if (filterFormContainer.style.display == 'none') {
            toggleFilterBarBtn.textContent = "Tắt bộ lọc";
            filterFormContainer.style.display = 'block';
            return;
        }
        toggleFilterBarBtn.textContent = "Bật bộ lọc";
        filterFormContainer.style.display = 'none';
        return;
    }
})