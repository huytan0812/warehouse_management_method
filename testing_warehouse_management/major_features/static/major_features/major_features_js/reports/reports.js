document.addEventListener("DOMContentLoaded", function() {
    let dropDownMenuButton1 = document.getElementById("dropdownMenuButton1");
    let periodType = document.getElementById("period-type");
    dropDownMenuButton1.addEventListener("click", function() {
        if (periodType.classList.contains("dropdown-menu")) {
            periodType.classList.add("dropdown-active");
            periodType.classList.remove("dropdown-menu");
        }
        else {
            periodType.classList.add("dropdown-menu");
            periodType.classList.remove("dropdown-active");
        }
        console.log(periodType.classList);
    })
})