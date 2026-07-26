document.addEventListener("DOMContentLoaded", () => {
    const chooseBtn = document.getElementById("choose-file-btn");
    const fileInput = document.getElementById("file-input");
    const previewImg = document.getElementById("preview-img");

    const resultPlaceholder = document.getElementById("result-placeholder");
    const resultContent = document.getElementById("result-content");

    const resultName = document.getElementById("result-name");
    const resultCategory = document.getElementById("result-category");
    const resultConfidence = document.getElementById("result-confidence");
    const resultTip = document.getElementById("result-tip");
    const resultBin = document.getElementById("result-bin");

    const uploadArea = document.getElementById("upload-area");

    // Create Analyze button if it doesn't exist
    let analyzeBtn = document.getElementById("analyze-btn");

    if (!analyzeBtn) {
        analyzeBtn = document.createElement("button");
        analyzeBtn.id = "analyze-btn";
        analyzeBtn.innerText = "Analyze Image";
        analyzeBtn.style.marginTop = "15px";
        uploadArea.appendChild(analyzeBtn);
    }

    // Open file picker
    chooseBtn.addEventListener("click", (e) => {
        e.preventDefault();
        fileInput.click();
    });

    // Preview image
    fileInput.addEventListener("change", () => {
        if (!fileInput.files.length) return;

        const file = fileInput.files[0];

        const reader = new FileReader();

        reader.onload = function (e) {
    previewImg.src = e.target.result;
    previewImg.hidden = false;

    // Hide file1.png after an image is selected
    document.getElementById("camera-image").style.display = "none";
    };

        reader.readAsDataURL(file);
    });

    // Upload image
    analyzeBtn.addEventListener("click", async () => {

        if (!fileInput.files.length) {
            alert("Please choose an image first.");
            return;
        }

        analyzeBtn.disabled = true;
        analyzeBtn.innerText = "Analyzing...";

        const formData = new FormData();
        formData.append("image", fileInput.files[0]);

        try {

            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            console.log("API RESPONSE:",data);


            if (!response.ok) {
                alert(data.error || "Upload failed");
                analyzeBtn.disabled = false;
                analyzeBtn.innerText = "Analyze Image";
                return;
            }

            resultPlaceholder.hidden = true;
            resultContent.hidden = false;

            resultName.textContent = data.item;
resultCategory.textContent = data.category;
resultConfidence.textContent =
    Math.round(data.confidence * 100) + "%";
resultTip.textContent = data.tip;

const CATEGORY_TO_BIN = {
    "Plastic": "♻️ Plastic Bin",
    "Organic": "🍌 Organic Bin",
    "Hazardous": "🧪 Hazardous Bin",
    "E-Waste": "🔋 E-Waste Bin",
    "Others": "🗑️ General Waste (no smart bin)"
};

resultBin.textContent = CATEGORY_TO_BIN[data.category];
        
        } catch (err) {
            console.error(err);
            alert("Server connection failed.");
        }

        analyzeBtn.disabled = false;
        analyzeBtn.innerText = "Analyze Image";

    });
});