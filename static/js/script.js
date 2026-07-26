// ============================================================
// EcoSort AI — Dashboard Logic
// Frontend-only simulation: mock IoT data + real AI classification
// (AI Scanner is handled by scanner.js, which calls the real /api/upload
// endpoint - the mock scanner block has been removed from this file).
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  initDate();
  initBins();
  initCountUp();
  initCharts();
  // initScanner() removed — scanner.js now owns the AI Scanner section
});

/* ---------------- Date ---------------- */
function initDate() {
  const el = document.getElementById("today-date");
  const today = new Date();
  el.textContent = today.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/* ---------------- Count-up numbers ---------------- */
function initCountUp() {
  document.querySelectorAll(".stat-value[data-count]").forEach((el) => {
    const target = parseInt(el.dataset.count, 10);
    const duration = 900;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = `${Math.round(eased * target).toLocaleString()} kg`;
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
}

/* ---------------- Smart Bins ---------------- */
const STREAM_META = {
  plastic: {
    label: "Plastic",
    image: "/static/images/plastic.png"
  },
  organic: {
    label: "Organic",
    image: "/static/images/organic.png"
  },
  hazard: {
    label: "Hazardous",
    image: "/static/images/hazard.png"
  },
  ewaste: {
    label: "E-Waste",
    image: "/static/images/ewaste.png"
  }
};

// Simulated IoT state — replace with live sensor/API data later.
let bins = [
  { id: 1, name: "Bin 1", stream: "plastic", fill: 80, temp: 29, humidity: 44, gas: "Normal", collected: "2 hrs ago" },
  { id: 2, name: "Bin 2", stream: "organic", fill: 54, temp: 24, humidity: 61, gas: "Normal", collected: "5 hrs ago" },
  { id: 3, name: "Bin 3", stream: "hazard", fill: 96, temp: 22, humidity: 38, gas: "Elevated", collected: "9 hrs ago" },
  { id: 4, name: "Bin 4", stream: "ewaste", fill: 21, temp: 23, humidity: 40, gas: "Normal", collected: "1 hr ago" },
];

let selectedBinId = bins[0].id;

function statusForFill(fill) {
  if (fill >= 90) return { text: "Full", color: "red" };
  if (fill >= 70) return { text: "Nearly Full", color: "orange" };
  if (fill >= 40) return { text: "Half Full", color: "yellow" };
  return { text: "Normal", color: "green" };
}

function initBins() {
  renderBins();
  renderBinDetails();

  // Simulate live sensor drift every few seconds.
  setInterval(() => {
    bins = bins.map((b) => {
      const drift = Math.round((Math.random() - 0.3) * 4);
      const fill = Math.max(5, Math.min(100, b.fill + drift));
      const temp = Math.max(18, Math.min(34, b.temp + (Math.random() - 0.5) * 1.2));
      return { ...b, fill, temp: Math.round(temp) };
    });
    runSearch(activeSearchQuery); // respects whatever's currently typed in search
    renderBinDetails();
  }, 6000);
}

function renderBins() {
  const grid = document.getElementById("bins-grid");
  grid.innerHTML = bins
    .map((b) => {
      const meta = STREAM_META[b.stream];
      const status = statusForFill(b.fill);
      const selected = b.id === selectedBinId ? "selected" : "";
      return `
        <div class="bin-card ${selected}" data-id="${b.id}" tabindex="0" role="button" aria-pressed="${b.id === selectedBinId}">
          <div class="bin-card-top">
<span class="bin-card-name">
  <img src="/static/images/${b.stream}.png" class="bin-icon">
  ${b.name}
</span>
            <span class="status-dot ${status.color}" title="${status.text}"></span>
          </div>
          <div class="bin-card-type">${meta.label}</div>
          <div class="bin-progress-track">
            <div class="bin-progress-fill" style="width:${b.fill}%; background:${statusColorHex(status.color)}"></div>
          </div>
          <div class="bin-card-footer">
            <span><strong>${b.fill}%</strong> full</span>
            <span>${status.text}</span>
          </div>
        </div>
      `;
    })
    .join("");

  grid.querySelectorAll(".bin-card").forEach((card) => {
    card.addEventListener("click", () => selectBin(Number(card.dataset.id)));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectBin(Number(card.dataset.id));
      }
    });
  });
}
function renderFilteredBins(filteredBins) {
  const grid = document.getElementById("bins-grid");

  grid.innerHTML = filteredBins
    .map((b) => {
      const meta = STREAM_META[b.stream];
      const status = statusForFill(b.fill);
      const selected = b.id === selectedBinId ? "selected" : "";

      return `
        <div class="bin-card ${selected}" data-id="${b.id}" tabindex="0" role="button">
          <div class="bin-card-top">
            <span class="bin-card-name">
              <img src="${meta.image}" class="bin-icon" alt="${meta.label}">
              ${b.name}
            </span>

            <span class="status-dot ${status.color}" title="${status.text}"></span>
          </div>

          <div class="bin-card-type">${meta.label}</div>

          <div class="bin-progress-track">
            <div
              class="bin-progress-fill"
              style="width:${b.fill}%; background:${statusColorHex(status.color)}">
            </div>
          </div>

          <div class="bin-card-footer">
            <span><strong>${b.fill}%</strong> full</span>
            <span>${status.text}</span>
          </div>
        </div>
      `;
    })
    .join("");

  // Re-enable clicking on the filtered cards
  document.querySelectorAll(".bin-card").forEach((card) => {
    card.addEventListener("click", () => {
      selectedBinId = Number(card.dataset.id);
      renderBins();
      renderBinDetails();
    });
  });
}

function statusColorHex(color) {
  return {
    green: "var(--status-green)",
    yellow: "var(--status-yellow)",
    orange: "var(--status-orange)",
    red: "var(--status-red)",
  }[color];
}

function selectBin(id) {
  selectedBinId = id;
  renderBins();
  renderBinDetails();
}

function renderBinDetails() {
  const bin = bins.find((b) => b.id === selectedBinId);
  if (!bin) return;
  const meta = STREAM_META[bin.stream];
  const status = statusForFill(bin.fill);

  document.getElementById("detail-name").textContent = bin.name;
  document.getElementById("detail-fill").textContent = `${bin.fill}%`;
  document.getElementById("detail-type").textContent = meta.label;
  document.getElementById("detail-temp").textContent = `${bin.temp}°C`;
  document.getElementById("detail-humidity").textContent = `${bin.humidity}%`;
  document.getElementById("detail-gas").textContent = bin.gas;
  document.getElementById("detail-collected").textContent = bin.collected;

  const statusEl = document.getElementById("detail-status");
  statusEl.textContent = status.text;
  statusEl.style.color = statusColorHex(status.color);

  // Animate the ring: circumference = 2 * π * 52 ≈ 327
  const circumference = 327;
  const offset = circumference - (bin.fill / 100) * circumference;
  const fillCircle = document.getElementById("gauge-fill");
  fillCircle.style.stroke = statusColorHex(status.color);
  requestAnimationFrame(() => {
    fillCircle.style.strokeDashoffset = offset;
  });
}

/* ---------------- Charts ---------------- */
function initCharts() {
  const green = ["#1B5E20", "#2E7D32", "#4CAF50", "#81C784"];

  new Chart(document.getElementById("chart-bar"), {
    type: "bar",
    data: {
      labels: ["Plastic", "Organic", "E-Waste", "Hazardous"],
      datasets: [
        {
          label: "kg this week",
          data: [420, 280, 90, 40],
          backgroundColor: green,
          borderRadius: 8,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "#E1EFE2" } },
        x: { grid: { display: false } },
      },
    },
  });

  new Chart(document.getElementById("chart-doughnut"), {
    type: "doughnut",
    data: {
      labels: ["Plastic", "Organic", "E-Waste", "Hazardous"],
      datasets: [{ data: [420, 280, 90, 40], backgroundColor: green, borderWidth: 0 }],
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { family: "Poppins", size: 11 } } } },
      cutout: "65%",
    },
  });

  new Chart(document.getElementById("chart-line"), {
    type: "line",
    data: {
      labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
      datasets: [
        {
          label: "Total collected (kg)",
          data: [150, 190, 170, 210, 260, 175, 200],
          borderColor: "#2E7D32",
          backgroundColor: "rgba(46,125,50,0.12)",
          tension: 0.35,
          fill: true,
          pointBackgroundColor: "#2E7D32",
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "#E1EFE2" } },
        x: { grid: { display: false } },
      },
    },
  });
}

HEAD
// AI Scanner mock block removed — static/js/scanner.js now owns
// #upload-area / #file-input / #choose-file-btn / #analyze-btn and calls
// the real POST /api/upload (Flask + Groq) endpoint instead of faking it.

/* ---------------- AI Scanner (mock — swap for real API call) ---------------- */
const MOCK_RESULTS = [
  { name: "Plastic Bottle", category: "Plastic", bin: "♻️ Plastic Bin", confidence: 98, tip: "Remove the cap before recycling — it's sorted separately." },
  { name: "Banana Peel", category: "Organic", bin: "🍌 Organic Bin", confidence: 95, tip: "Compostable — keep it out of the plastic stream to avoid contamination." },
  { name: "AA Battery", category: "E-Waste", bin: "🔋 E-Waste Bin", confidence: 91, tip: "Never bin with organics — batteries need a dedicated e-waste drop point." },
  { name: "Cleaning Solvent", category: "Hazardous", bin: "🧪 Hazardous Bin", confidence: 88, tip: "Seal the container and flag it for manual pickup." },
];

function initScanner() {
  const uploadArea = document.getElementById("upload-area");
  const fileInput = document.getElementById("file-input");
  const chooseBtn = document.getElementById("choose-file-btn");
  const previewImg = document.getElementById("preview-img");
  const analyzeBtn = document.getElementById("analyze-btn");
  const newImageBtn = document.getElementById("new-image-btn");

  chooseBtn.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) showPreview(fileInput.files[0]);
  });

  ["dragover", "dragenter"].forEach((evt) =>
    uploadArea.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadArea.classList.add("drag-over");
    })
  );
  ["dragleave", "dragend"].forEach((evt) =>
    uploadArea.addEventListener(evt, () => uploadArea.classList.remove("drag-over"))
  );
  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) showPreview(file);
  });

 function showPreview(file) {
  const url = URL.createObjectURL(file);

  previewImg.src = url;
  previewImg.hidden = false;

  // Hide the camera image after a file is selected
  document.getElementById("camera-image").hidden = true;
}

  analyzeBtn.addEventListener("click", () => {
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing…";

    const placeholder = document.getElementById("result-placeholder");
    const content = document.getElementById("result-content");

    // --- MOCK: replace this block with a real fetch() to the Flask/Gemini
    //     backend once it's ready, e.g.:
    //     const res = await fetch('/api/classify', { method: 'POST', body: formData });
    //     const data = await res.json();
    setTimeout(() => {
      const result = MOCK_RESULTS[Math.floor(Math.random() * MOCK_RESULTS.length)];

      document.getElementById("result-name").textContent = result.name;
      document.getElementById("result-confidence").textContent = `${result.confidence}%`;
      document.getElementById("result-category").textContent = result.category;
      document.getElementById("result-bin").textContent = result.bin;
      document.getElementById("result-tip").textContent = result.tip;

      placeholder.hidden = true;
      content.hidden = false;

      analyzeBtn.disabled = false;
      analyzeBtn.textContent = "Analyze Image";
    }, 1200);
    // --- END MOCK
  });
  newImageBtn.addEventListener("click", () => {
  fileInput.value = "";
  previewImg.src = "";
  previewImg.hidden = true;

  document.getElementById("result-placeholder").hidden = false;
  document.getElementById("result-content").hidden = true;

  analyzeBtn.disabled = true;
});
}
/* ---------------- Global Search ---------------- */

let activeSearchQuery = "";

const searchInput = document.getElementById("global-search");

if (searchInput) {
  searchInput.addEventListener("input", function () {
    activeSearchQuery = this.value.toLowerCase().trim();
    runSearch(activeSearchQuery);
  });
}

function runSearch(query) {
  const grid = document.getElementById("bins-grid");

  if (!query) {
    renderBins();
    return;
  }

  const filtered = bins.filter((bin) => {
    const meta = STREAM_META[bin.stream];
    const status = statusForFill(bin.fill);
    return (
      bin.name.toLowerCase().includes(query) ||
      meta.label.toLowerCase().includes(query) ||
      bin.stream.toLowerCase().includes(query) ||
      status.text.toLowerCase().includes(query)
    );
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<p class="no-results">No bins match "${query}"</p>`;
    return;
  }

  renderFilteredBins(filtered);

  // Keep the details panel in sync with what's visible
  if (!filtered.some((b) => b.id === selectedBinId)) {
    selectedBinId = filtered[0].id;
    renderBinDetails();
  }

  document.getElementById("bins").scrollIntoView({ behavior: "smooth", block: "start" });
}