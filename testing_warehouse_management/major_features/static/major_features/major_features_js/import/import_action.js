document.addEventListener("DOMContentLoaded", function() {
    console.log("Hello World");
    let importPurchaseFormsContainer = document.getElementById("import-purchase-forms-container");
    let lastImportPurchaseForm = document.getElementById("new-import-purchase-row");
    const addPurchaseForm = document.getElementById("add-purchase-form");

    addPurchaseForm.addEventListener("click", () => {
        const newImportPurchaseForm = document.createElement("tr");
        newImportPurchaseForm.innerHTML = lastImportPurchaseForm.innerHTML;
        lastImportPurchaseForm.removeAttribute("id");
        newImportPurchaseForm.setAttribute("class", "import-purchase-form");
        newImportPurchaseForm.setAttribute("id", "new-import-purchase-row");

        importPurchaseFormsContainer.append(newImportPurchaseForm);
    })
})