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


  
/* ---------------- Global Search ---------------- */

let activeSearchQuery = "";

const searchInput = document.getElementById("global-search");

if (searchInput) {
  searchInput.addEventListener("input", function () {
    activeSearchQuery = this.value.toLowerCase().trim();
    runSearch(activeSearchQuery);
  });
}
window.updateBin = function(category) {
  

    const map = {
        "Plastic": "plastic",
        "Organic": "organic",
        "Hazardous": "hazard",
        "E-Waste": "ewaste"
    };

    const stream = map[category];

    const bin = bins.find(b => b.stream === stream);

    if (bin) {
        bin.fill = Math.min(bin.fill + 5, 100);

        renderBins();
        renderBinDetails();
    }
};

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