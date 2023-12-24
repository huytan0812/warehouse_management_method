document.addEventListener("DOMContentLoaded", function(){
    const exportToExcelBtn = document.getElementById("export-to-excel-btn");
    const filenameExcelForm = document.getElementById("filename-excel-form");
    exportToExcelBtn.onclick = function() {
        if (filenameExcelForm.style.display == 'none') {
            filenameExcelForm.style.display = 'flex';
            return;
        }
        filenameExcelForm.style.display = 'none';
        return;
    }
})