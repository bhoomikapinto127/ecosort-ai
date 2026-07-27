document.addEventListener("DOMContentLoaded", () => {
    const chooseBtn = document.getElementById("choose-file-btn");
    const cameraBtn = document.getElementById("camera-btn");
    const fileInput = document.getElementById("file-input");
    const previewImg = document.getElementById("preview-img");

    const resultPlaceholder = document.getElementById("result-placeholder");
    const resultContent = document.getElementById("result-content");

    const resultName = document.getElementById("result-name");
    const resultCategory = document.getElementById("result-category");
    const resultConfidence = document.getElementById("result-confidence");
    const resultTip = document.getElementById("result-tip");
    const resultBin = document.getElementById("result-bin");

    const addToBinBtn = document.getElementById("add-to-bin-btn");

    const uploadArea = document.getElementById("upload-area");
    const cameraBtn = document.getElementById("camera-btn");
const captureBtn = document.getElementById("capture-btn");
const closeCameraBtn = document.getElementById("close-camera-btn");
const cameraPreview = document.getElementById("camera-preview");
const cameraCanvas = document.getElementById("camera-canvas");

<<<<<<< HEAD
    // Keep track of the most recent classification so the
    // "Add to Bin" button knows what category to log.
    let currentCategory = null;

=======
let cameraStream = null;
>>>>>>> 4b88401b01953b342eaef901dba88a5474a780cb
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
    fileInput.removeAttribute("capture"); // Open gallery/file picker
    fileInput.click();
});

cameraBtn.addEventListener("click", (e) => {
    e.preventDefault();
    fileInput.setAttribute("capture", "environment"); // Open camera
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

        // A new image was chosen — reset the Add to Bin button
        // so the user can't re-log a stale result.
        if (addToBinBtn) {
            addToBinBtn.disabled = false;
            addToBinBtn.innerText = "Add to Bin";
        }
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

// Remember the category and re-arm the Add to Bin button
// for this new result.
currentCategory = data.category;
if (addToBinBtn) {
    addToBinBtn.disabled = false;
    addToBinBtn.innerText = "Add to Bin";
}
        
        } catch (err) {
            console.error(err);
            alert("Server connection failed.");
        }

        analyzeBtn.disabled = false;
        analyzeBtn.innerText = "Analyze Image";

    });
<<<<<<< HEAD

    // "Add to Bin" — confirms the disposal and logs the item
    // into the matching smart bin (bumps its fill level via
    // window.updateBin, defined in script.js).
    if (addToBinBtn) {
        addToBinBtn.addEventListener("click", () => {
            if (!currentCategory) {
                alert("Analyze an image first.");
                return;
            }
window.updateBin(currentCategory);


            addToBinBtn.disabled = true;
            addToBinBtn.innerText = "✓ Added";

            setTimeout(() => {
                addToBinBtn.innerText = "Add to Bin";
                // Stays disabled until a new image is analyzed,
                // so the same item can't be double-logged.
            }, 1500);
        });
    }
=======
});
// Open webcam
cameraBtn.addEventListener("click", async () => {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: true
        });

        cameraPreview.srcObject = cameraStream;

        cameraPreview.hidden = false;
        captureBtn.hidden = false;
        closeCameraBtn.hidden = false;

        document.getElementById("camera-image").style.display = "none";
        previewImg.hidden = true;

    } catch (err) {
        alert("Unable to access camera.");
        console.error(err);
    }
});

// Capture image
captureBtn.addEventListener("click", () => {

    const ctx = cameraCanvas.getContext("2d");

    cameraCanvas.width = cameraPreview.videoWidth;
    cameraCanvas.height = cameraPreview.videoHeight;

    ctx.drawImage(
        cameraPreview,
        0,
        0,
        cameraCanvas.width,
        cameraCanvas.height
    );

    previewImg.src = cameraCanvas.toDataURL("image/png");
    previewImg.hidden = false;

    cameraPreview.hidden = true;
    captureBtn.hidden = true;
    closeCameraBtn.hidden = true;

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }
});

// Close camera
closeCameraBtn.addEventListener("click", () => {

    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }

    cameraPreview.hidden = true;
    captureBtn.hidden = true;
    closeCameraBtn.hidden = true;

    document.getElementById("camera-image").style.display = "block";
>>>>>>> 4b88401b01953b342eaef901dba88a5474a780cb
});