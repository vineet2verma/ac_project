function showLoader(text = "Processing… Please wait") {
    document.getElementById("erpLoaderText").innerText = text;
    document.getElementById("erpLoader").classList.remove("d-none");
}

function hideLoader() {
    document.getElementById("erpLoader").classList.add("d-none");
}

/* 🔒 AUTO FORM SUBMIT HANDLER */
document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll("form").forEach(form => {

        form.addEventListener("submit", function () {

            const msg = form.dataset.loaderText || "Saving data… Please wait";
            showLoader(msg);

            // Prevent double submit
            form.querySelectorAll("button[type='submit']")
                .forEach(btn => btn.disabled = true);
        });
    });
});
