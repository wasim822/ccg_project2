const API = window.location.origin;
// backend API URL
let barChart;
let scatterChart;
let heatmapChart;
let pieChart;

// Pagination state for the recipes table
let currentPage  = 1;
const LIMIT      = 20;   // rows per page

document.getElementById("getClusters").addEventListener("click", loadClusters);
document.getElementById("getInsights").addEventListener("click", loadInsights);
document.getElementById("getRecipes").addEventListener("click", function () {
    currentPage = 1;
    loadRecipes();
});

// Re-fetch page 1 whenever the diet-type dropdown changes
document.getElementById("dietType").addEventListener("change", function () {
    currentPage = 1;
    // Only auto-refresh if the recipe section is already visible
    if (!document.getElementById("recipeSection").classList.contains("hidden")) {
        loadRecipes();
    }
});

// Helper – build query string from current filter state
function buildRecipeParams(page) {
    const dietType = document.getElementById("dietType").value;
    const search   = document.getElementById("searchInput").value.trim();

    const params = new URLSearchParams();
    params.set("page",  page);
    params.set("limit", LIMIT);
    if (dietType) params.set("dietType", dietType);
    if (search)   params.set("search",   search);
    return params.toString();
}

// Load & render recipes with pagination
function loadRecipes() {
    const qs = buildRecipeParams(currentPage);

    fetch(`${API}/recipes?${qs}`)
        .then(res => res.json())
        .then(json => {
            if (json.error) {
                alert("Error loading recipes: " + json.error);
                return;
            }

            renderRecipeTable(json.data);
            renderPagination(json.page, json.total_pages, json.total_count);

            // Show the recipe section now that we have data
            document.getElementById("recipeSection").classList.remove("hidden");
        })
        .catch(err => console.error("Failed to fetch recipes:", err));
}

// Populate the <tbody> with one row per recipe
function renderRecipeTable(rows) {
    const tbody = document.getElementById("recipeBody");
    tbody.innerHTML = "";

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">No recipes found.</td></tr>';
        return;
    }

    rows.forEach(r => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${r["Recipe_name"]}</td>
            <td>${r["Diet_type"]}</td>
            <td>${r["Cuisine_type"]}</td>
            <td>${r["Protein(g)"].toFixed(1)}</td>
            <td>${r["Carbs(g)"].toFixed(1)}</td>
            <td>${r["Fat(g)"].toFixed(1)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Build Previous / numbered pages / Next buttons
function renderPagination(page, totalPages, totalCount) {
    const container = document.getElementById("pagination");
    container.innerHTML = "";

    // Info line
    document.getElementById("recipeInfo").textContent =
        `Showing page ${page} of ${totalPages} (${totalCount} recipes total)`;

    // Previous
    const prev = document.createElement("button");
    prev.textContent = "Previous";
    prev.disabled = (page <= 1);
    prev.addEventListener("click", () => {
        currentPage--;
        loadRecipes();
    });
    container.appendChild(prev);

    // Page number buttons – show a window of up to 7 pages around the current page
    const windowSize = 7;
    let startPage = Math.max(1, page - Math.floor(windowSize / 2));
    let endPage   = Math.min(totalPages, startPage + windowSize - 1);
    // Adjust start if we're near the end
    startPage = Math.max(1, endPage - windowSize + 1);

    for (let p = startPage; p <= endPage; p++) {
        const btn = document.createElement("button");
        btn.textContent = p;
        if (p === page) btn.classList.add("active");
        btn.addEventListener("click", (function (pg) {
            return function () {
                currentPage = pg;
                loadRecipes();
            };
        })(p));
        container.appendChild(btn);
    }

    // Next
    const next = document.createElement("button");
    next.textContent = "Next";
    next.disabled = (page >= totalPages);
    next.addEventListener("click", () => {
        currentPage++;
        loadRecipes();
    });
    container.appendChild(next);
}

// Bar chart – average macronutrients by diet type (from /clusters)
function loadClusters() {
    fetch(`${API}/clusters`)
        .then(res => res.json())
        .then(data => {
            if (data.error) { alert("Error: " + data.error); return; }

            const diets   = Object.keys(data);
            const protein = diets.map(d => +data[d]["Protein(g)"].toFixed(2));
            const carbs   = diets.map(d => +data[d]["Carbs(g)"].toFixed(2));
            const fat     = diets.map(d => +data[d]["Fat(g)"].toFixed(2));

            // Bar chart
            const barCtx = document.getElementById("barChart").getContext("2d");
            if (barChart) barChart.destroy();
            barChart = new Chart(barCtx, {
                type: "bar",
                data: {
                    labels: diets,
                    datasets: [
                        { label: "Protein (g)", data: protein, backgroundColor: "rgba(59,130,246,0.7)" },
                        { label: "Carbs (g)",   data: carbs,   backgroundColor: "rgba(16,185,129,0.7)" },
                        { label: "Fat (g)",     data: fat,     backgroundColor: "rgba(245,158,11,0.7)" },
                    ],
                },
                options: { responsive: true, plugins: { legend: { position: "bottom" } } },
            });

            //Heatmap
            const allValues = [...protein, ...carbs, ...fat];
            const maxVal    = Math.max(...allValues);

            // one dataset per nutrient so the legend is clear
            const heatCtx = document.getElementById("heatmapChart").getContext("2d");
            if (heatmapChart) heatmapChart.destroy();
            heatmapChart = new Chart(heatCtx, {
                type: "bar",
                data: {
                    labels: diets,
                    datasets: [
                        {
                            label: "Protein",
                            data: protein,
                            backgroundColor: protein.map(v => heatColour(v, maxVal)),
                        },
                        {
                            label: "Carbs",
                            data: carbs,
                            backgroundColor: carbs.map(v => heatColour(v, maxVal)),
                        },
                        {
                            label: "Fat",
                            data: fat,
                            backgroundColor: fat.map(v => heatColour(v, maxVal)),
                        },
                    ],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: "bottom" } },
                    scales: { y: { beginAtZero: true } },
                },
            });

            // Pie chart
            const pieCtx = document.getElementById("pieChart").getContext("2d");
            if (pieChart) pieChart.destroy();
            pieChart = new Chart(pieCtx, {
                type: "pie",
                data: {
                    labels: diets,
                    datasets: [{
                        data: protein,
                        backgroundColor: [
                            "rgba(59,130,246,0.8)",
                            "rgba(16,185,129,0.8)",
                            "rgba(245,158,11,0.8)",
                            "rgba(239,68,68,0.8)",
                            "rgba(139,92,246,0.8)",
                        ],
                    }],
                },
                options: { responsive: true, plugins: { legend: { position: "bottom" } } },
            });
        })
        .catch(err => console.error("Failed to fetch clusters:", err));
}

// Map a value 0..max to a blue→red heat colour
function heatColour(value, max) {
    const ratio = max > 0 ? value / max : 0;
    const r = Math.round(255 * ratio);
    const b = Math.round(255 * (1 - ratio));
    return `rgba(${r}, 80, ${b}, 0.8)`;
}

// Scatter plot – protein-to-carbs vs carbs-to-fat ratios (from /insights)
function loadInsights() {
    const dietType = document.getElementById("dietType").value;
    const qs = dietType ? `?dietType=${encodeURIComponent(dietType)}` : "";

    fetch(`${API}/insights${qs}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) { alert("Error: " + data.error); return; }

            // Cap outliers at the 99th percentile so the chart is readable
            const ratios = data.map(item => ({
                x: item["Protein_to_Carbs_ratio"],
                y: item["Carbs_to_Fat_ratio"],
            }));

            const cap = percentile(ratios.flatMap(p => [p.x, p.y]), 99);
            const points = ratios.map(p => ({
                x: Math.min(p.x, cap),
                y: Math.min(p.y, cap),
            }));

            const ctx = document.getElementById("scatterChart").getContext("2d");
            if (scatterChart) scatterChart.destroy();
            scatterChart = new Chart(ctx, {
                type: "scatter",
                data: {
                    datasets: [{
                        label: "Protein:Carbs vs Carbs:Fat",
                        data: points,
                        backgroundColor: "rgba(59,130,246,0.5)",
                        pointRadius: 3,
                    }],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: "bottom" } },
                    scales: {
                        x: { title: { display: true, text: "Protein / Carbs ratio" } },
                        y: { title: { display: true, text: "Carbs / Fat ratio" } },
                    },
                },
            });
        })
        .catch(err => console.error("Failed to fetch insights:", err));
}

// percentile helper
function percentile(arr, p) {
    const sorted = [...arr].sort((a, b) => a - b);
    const idx    = Math.floor((p / 100) * sorted.length);
    return sorted[Math.min(idx, sorted.length - 1)];
}
