document.addEventListener("DOMContentLoaded", function() {
    let dropDownMenuButton1 = document.getElementById("dropdownMenuButton1");
    let periodType = document.getElementById("period-type");
    dropDownMenuButton1.addEventListener("click", function() {
        if (periodType.style.display === "none") {
            periodType.style.display = "block";
        }
        else {
            periodType.style.display = "none";
        }
    })
})