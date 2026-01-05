function showLoader(text = "Processing… Please wait") {
    const loader = document.getElementById("erpLoader");
    const loaderText = document.getElementById("erpLoaderText");

    if (loaderText) loaderText.innerText = text;
    if (loader) loader.classList.add("show");
}

function hideLoader() {
    const loader = document.getElementById("erpLoader");
    if (loader) loader.classList.remove("show");
}

document.addEventListener("DOMContentLoaded", function () {

    const loader = document.getElementById("erpLoader");
    const form = document.querySelector("form");
    const btn = document.getElementById("loginBtn");

    // 🔥 FORCE HIDE ON PAGE LOAD
    if (loader) loader.classList.remove("show");

    if (!form || !loader) return;

    // SHOW ONLY ON SUBMIT
    form.addEventListener("submit", function () {
        showLoader(
            form.getAttribute("data-loader-text") ||
            "Processing… Please wait"
        );

        if (btn) btn.disabled = true;
    });
});