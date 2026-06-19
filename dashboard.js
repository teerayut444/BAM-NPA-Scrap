// BAM NPA Dashboard Logic
let allData = [];
let filteredData = [];
let map = null;
let markerGroup = null;
let currentChart = null;
let currentChartTab = "type"; // "type" | "province" | "discount"

// Pagination State
let currentPage = 1;
const itemsPerPage = 10;

// Fetch and initialize data
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    loadData();
    setupEventListeners();
});

// 1. Initialize Leaflet Map
function initMap() {
    // Center of Thailand
    map = L.map('map').setView([13.736717, 100.523186], 6);
    
    // Use CartoDB Dark Matter map tiles for premium dark aesthetic
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Layer group to hold and easily refresh markers
    markerGroup = L.layerGroup().addTo(map);
}

// 2. Load Properties JSON
function loadData() {
    fetch('properties.json')
        .then(response => {
            if (!response.ok) {
                throw new Error("Cannot fetch properties.json");
            }
            return response.json();
        })
        .then(data => {
            allData = data;
            filteredData = [...allData];
            
            // Populate filters dropdowns
            populateFilters();
            
            // Render Dashboard components
            updateDashboard();
        })
        .catch(err => {
            console.error("Error loading dashboard data:", err);
            document.getElementById("data-count-header").innerHTML = `<span style="color: #ef4444">Error loading data</span>`;
        });
}

// 3. Populate dropdown options from loaded data
function populateFilters() {
    const types = new Set();
    const provinces = new Set();
    
    allData.forEach(item => {
        if (item["ประเภททรัพย์"]) types.add(item["ประเภททรัพย์"]);
        if (item["จังหวัด"]) provinces.add(item["จังหวัด"]);
    });

    // Populate Types Dropdown
    const typeSelect = document.getElementById("filter-type");
    Array.from(types).sort().forEach(type => {
        const opt = document.createElement("option");
        opt.value = type;
        opt.textContent = type;
        typeSelect.appendChild(opt);
    });

    // Populate Provinces Dropdown
    const provSelect = document.getElementById("filter-province");
    Array.from(provinces).sort().forEach(prov => {
        const opt = document.createElement("option");
        opt.value = prov;
        opt.textContent = prov;
        provSelect.appendChild(opt);
    });
}

// Update Districts filter options based on selected Province
function updateDistrictFilter(province) {
    const distSelect = document.getElementById("filter-district");
    distSelect.innerHTML = '<option value="all">ทั้งหมด (All Districts)</option>';
    
    if (province === "all") {
        return;
    }

    const districts = new Set();
    allData.forEach(item => {
        if (item["จังหวัด"] === province && item["อำเภอ"]) {
            districts.add(item["อำเภอ"]);
        }
    });

    Array.from(districts).sort().forEach(dist => {
        const opt = document.createElement("option");
        opt.value = dist;
        opt.textContent = dist;
        distSelect.appendChild(opt);
    });
}

// 4. Filter logic
function applyFilters() {
    const selectedType = document.getElementById("filter-type").value;
    const selectedProvince = document.getElementById("filter-province").value;
    const selectedDistrict = document.getElementById("filter-district").value;
    const minPrice = parseFloat(document.getElementById("filter-price-min").value) || 0;
    const maxPrice = parseFloat(document.getElementById("filter-price-max").value) || Infinity;
    const minArea = parseFloat(document.getElementById("filter-area-min").value) || 0;
    const searchText = document.getElementById("search-input").value.toLowerCase();

    filteredData = allData.filter(item => {
        // Type filter
        if (selectedType !== "all" && item["ประเภททรัพย์"] !== selectedType) return false;
        
        // Province filter
        if (selectedProvince !== "all" && item["จังหวัด"] !== selectedProvince) return false;
        
        // District filter
        if (selectedDistrict !== "all" && item["อำเภอ"] !== selectedDistrict) return false;
        
        // Price filter
        const price = parseFloat(item["ราคา"]) || 0;
        if (price < minPrice || price > maxPrice) return false;
        
        // Usable Area filter
        const area = parseFloat(item["พื้นที่ใช้สอย (ตร.ม.)"]) || 0;
        if (minArea > 0 && area < minArea) return false;

        // Search text
        if (searchText) {
            const title = (item["ชื่อประกาศ"] || "").toLowerCase();
            const code = (item["รหัสทรัพย์"] || "").toLowerCase();
            const location = (item["ทำเล/ที่ตั้ง"] || "").toLowerCase();
            if (!title.includes(searchText) && !code.includes(searchText) && !location.includes(searchText)) return false;
        }

        return true;
    });

    currentPage = 1;
    updateDashboard();
}

// Reset filters to default state
function resetFilters() {
    document.getElementById("filter-type").value = "all";
    document.getElementById("filter-province").value = "all";
    document.getElementById("filter-district").innerHTML = '<option value="all">ทั้งหมด (All Districts)</option>';
    document.getElementById("filter-price-min").value = "";
    document.getElementById("filter-price-max").value = "";
    document.getElementById("filter-area-min").value = "";
    document.getElementById("search-input").value = "";
    
    filteredData = [...allData];
    currentPage = 1;
    updateDashboard();
}

// 5. Update dashboard views
function updateDashboard() {
    document.getElementById("data-count-header").textContent = `ข้อมูล: ${filteredData.length} / ${allData.length} รายการ`;
    
    updateKPIs();
    updateMapMarkers();
    renderChart();
    renderTable();
}

// 6. Calculate KPIs
function updateKPIs() {
    const totalCount = filteredData.length;
    let totalValue = 0;
    let discountCount = 0;
    let maxDiscountPercent = 0;

    filteredData.forEach(item => {
        const price = parseFloat(item["ราคา"]) || 0;
        const originalPrice = parseFloat(item["ราคาตั้งต้น"]) || 0;

        totalValue += price;

        if (originalPrice > price && originalPrice > 0) {
            discountCount++;
            const pct = ((originalPrice - price) / originalPrice) * 100;
            if (pct > maxDiscountPercent) {
                maxDiscountPercent = pct;
            }
        }
    });

    document.getElementById("kpi-total-properties").textContent = totalCount.toLocaleString();
    document.getElementById("kpi-total-value").textContent = totalValue.toLocaleString() + " ฿";
    document.getElementById("kpi-discount-count").textContent = discountCount.toLocaleString();
    document.getElementById("kpi-max-discount").textContent = maxDiscountPercent.toFixed(1) + "%";
}

// 7. Update Map Markers
function updateMapMarkers() {
    markerGroup.clearLayers();
    
    let validCoordsCount = 0;
    const bounds = [];

    filteredData.forEach(item => {
        const lat = parseFloat(item["ละติจูด"]);
        const lng = parseFloat(item["ลองจิจูด"]);

        if (!isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0) {
            validCoordsCount++;
            bounds.push([lat, lng]);

            const price = parseFloat(item["ราคา"]) || 0;
            const originalPrice = parseFloat(item["ราคาตั้งต้น"]) || 0;
            
            let priceHtml = `<div class="map-popup-price">${price.toLocaleString()} ฿</div>`;
            if (originalPrice > price) {
                const discountPct = ((originalPrice - price) / originalPrice) * 100;
                priceHtml = `
                    <div style="font-size: 0.75rem; text-decoration: line-through; color: var(--text-muted)">${originalPrice.toLocaleString()} ฿</div>
                    <div class="map-popup-price">${price.toLocaleString()} ฿ <span style="color: #34d399; font-size: 0.75rem; font-weight:600">-${discountPct.toFixed(0)}%</span></div>
                `;
            }

            const imgUrl = item["รูปภาพ"] || "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=300&q=80";

            const popupContent = `
                <div class="map-popup-card">
                    <img class="map-popup-image" src="${imgUrl}" alt="Property image" onerror="this.src='https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=300&q=80'"/>
                    <div class="map-popup-title">${item["ชื่อประกาศ"] || "ไม่มีชื่อประกาศ"}</div>
                    <div class="map-popup-details">
                        <b>รหัสทรัพย์:</b> ${item["รหัสทรัพย์"] || "-"}<br/>
                        <b>ประเภท:</b> ${item["ประเภททรัพย์"] || "-"}<br/>
                        <b>ที่ตั้ง:</b> ${item["ทำเล/ที่ตั้ง"] || "-"}
                    </div>
                    ${priceHtml}
                    ${item["ลิงก์"] ? `<a class="map-popup-link" href="${item["ลิงก์"]}" target="_blank">ดูรายละเอียดทรัพย์</a>` : ''}
                </div>
            `;

            // Custom colored marker or simple icon
            const marker = L.marker([lat, lng]).bindPopup(popupContent);
            markerGroup.addLayer(marker);
        }
    });

    // Auto fit map boundary if we have valid coordinates plotted
    if (validCoordsCount > 0) {
        map.fitBounds(bounds, { maxZoom: 14, padding: [30, 30] });
    } else {
        // Reset to default center of Thailand if no coordinates
        map.setView([13.736717, 100.523186], 6);
    }
}

// 8. Render Charts using ApexCharts
function renderChart() {
    if (currentChart) {
        currentChart.destroy();
    }

    const chartEl = document.querySelector("#chart");
    chartEl.innerHTML = ""; // Clear canvas

    let options = {};

    if (currentChartTab === "type") {
        // Average Price by Property Type
        const typeData = {};
        filteredData.forEach(item => {
            const type = item["ประเภททรัพย์"] || "อื่นๆ";
            const price = parseFloat(item["ราคา"]) || 0;
            if (price > 0) {
                if (!typeData[type]) typeData[type] = { total: 0, count: 0 };
                typeData[type].total += price;
                typeData[type].count++;
            }
        });

        const categories = Object.keys(typeData);
        const dataValues = categories.map(cat => Math.round(typeData[cat].total / typeData[cat].count));

        options = {
            series: [{
                name: 'ราคาเฉลี่ย (บาท)',
                data: dataValues
            }],
            chart: {
                type: 'bar',
                height: '100%',
                background: 'transparent',
                foreColor: '#9ca3af',
                toolbar: { show: false }
            },
            colors: ['#6366f1'],
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    horizontal: true,
                    dataLabels: { position: 'top' }
                }
            },
            dataLabels: {
                enabled: true,
                formatter: function (val) {
                    return (val / 1000000).toFixed(2) + "M";
                },
                style: { colors: ['#f3f4f6'], fontSize: '10px' }
            },
            xaxis: {
                categories: categories,
                labels: {
                    formatter: function (val) {
                        return (val / 1000000).toFixed(1) + "M ฿";
                    }
                }
            },
            tooltip: {
                theme: 'dark',
                y: {
                    formatter: function (val) {
                        return val.toLocaleString() + " บาท";
                    }
                }
            },
            grid: { borderColor: '#1f2937' }
        };

    } else if (currentChartTab === "province") {
        // Property Count by Province
        const provCounts = {};
        filteredData.forEach(item => {
            const prov = item["จังหวัด"] || "ไม่ระบุ";
            provCounts[prov] = (provCounts[prov] || 0) + 1;
        });

        // Get top 8 provinces and group remaining into 'อื่นๆ'
        const sortedProvs = Object.entries(provCounts).sort((a, b) => b[1] - a[1]);
        const topProvs = sortedProvs.slice(0, 8);
        const remainingCount = sortedProvs.slice(8).reduce((acc, curr) => acc + curr[1], 0);
        
        if (remainingCount > 0) {
            topProvs.push(["อื่นๆ (Others)", remainingCount]);
        }

        const labels = topProvs.map(item => item[0]);
        const series = topProvs.map(item => item[1]);

        options = {
            series: series,
            chart: {
                type: 'donut',
                height: '100%',
                background: 'transparent',
                foreColor: '#9ca3af'
            },
            labels: labels,
            stroke: { show: false },
            colors: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#3b82f6', '#14b8a6', '#6b7280'],
            legend: {
                position: 'right',
                fontSize: '11px',
                labels: { colors: '#9ca3af' }
            },
            dataLabels: { enabled: true, style: { fontSize: '10px' } },
            tooltip: { theme: 'dark' },
            plotOptions: {
                pie: {
                    donut: {
                        size: '65%',
                        labels: {
                            show: true,
                            name: { show: true, fontSize: '11px', color: '#9ca3af' },
                            value: { show: true, fontSize: '14px', fontWeight: '700', color: '#f3f4f6', formatter: v => v + " ทรัพย์" },
                            total: {
                                show: true,
                                label: 'รวมผลตัวกรอง',
                                color: '#9ca3af',
                                formatter: function (w) {
                                    return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                }
                            }
                        }
                    }
                }
            }
        };

    } else if (currentChartTab === "discount") {
        // Average Price vs Original Price for Properties that are Discounted
        const discounted = filteredData.filter(item => {
            const price = parseFloat(item["ราคา"]) || 0;
            const originalPrice = parseFloat(item["ราคาตั้งต้น"]) || 0;
            return originalPrice > price && originalPrice > 0;
        });

        const typeData = {};
        discounted.forEach(item => {
            const type = item["ประเภททรัพย์"] || "อื่นๆ";
            const price = parseFloat(item["ราคา"]) || 0;
            const originalPrice = parseFloat(item["ราคาตั้งต้น"]) || 0;
            
            if (!typeData[type]) typeData[type] = { total_price: 0, total_orig: 0, count: 0 };
            typeData[type].total_price += price;
            typeData[type].total_orig += originalPrice;
            typeData[type].count++;
        });

        const categories = Object.keys(typeData);
        const avgPrices = categories.map(cat => Math.round(typeData[cat].total_price / typeData[cat].count));
        const avgOriginals = categories.map(cat => Math.round(typeData[cat].total_orig / typeData[cat].count));

        options = {
            series: [
                { name: 'ราคาเฉลี่ยพิเศษ (บาท)', data: avgPrices },
                { name: 'ราคาตั้งต้นเฉลี่ย (บาท)', data: avgOriginals }
            ],
            chart: {
                type: 'bar',
                height: '100%',
                background: 'transparent',
                foreColor: '#9ca3af',
                toolbar: { show: false }
            },
            colors: ['#10b981', '#ef4444'], // Emerald green vs Rose red
            plotOptions: {
                bar: {
                    borderRadius: 4,
                    columnWidth: '55%',
                    endingShape: 'rounded'
                }
            },
            dataLabels: { enabled: false },
            xaxis: {
                categories: categories
            },
            yaxis: {
                labels: {
                    formatter: function (val) {
                        return (val / 1000000).toFixed(1) + "M ฿";
                    }
                }
            },
            tooltip: {
                theme: 'dark',
                y: {
                    formatter: function (val) {
                        return val.toLocaleString() + " บาท";
                    }
                }
            },
            grid: { borderColor: '#1f2937' }
        };
    }

    currentChart = new ApexCharts(chartEl, options);
    currentChart.render();
}

// 9. Render Table Data
function renderTable() {
    const tableBody = document.getElementById("table-body");
    tableBody.innerHTML = ""; // Clear existing rows

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredData.length);
    const paginatedItems = filteredData.slice(startIndex, endIndex);

    if (paginatedItems.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 40px;">ไม่พบรายการทรัพย์สินที่ตรงตามตัวกรอง</td></tr>`;
        document.getElementById("pagination-info").textContent = `แสดงรายการ 0 - 0 จาก 0 รายการ`;
        document.getElementById("btn-page-prev").disabled = true;
        document.getElementById("btn-page-next").disabled = true;
        return;
    }

    paginatedItems.forEach(item => {
        const row = document.createElement("tr");

        const price = parseFloat(item["ราคา"]) || 0;
        const originalPrice = parseFloat(item["ราคาตั้งต้น"]) || 0;
        
        let priceHtml = `<span class="price-text">${price.toLocaleString()} ฿</span>`;
        if (originalPrice > price) {
            const pct = ((originalPrice - price) / originalPrice) * 100;
            priceHtml = `
                <div style="display: flex; flex-direction: column;">
                    <div><span class="price-text">${price.toLocaleString()} ฿</span><span class="discount-badge">-${pct.toFixed(0)}%</span></div>
                    <span class="original-price-text" style="margin-left: 0;">${originalPrice.toLocaleString()} ฿</span>
                </div>
            `;
        }

        // Land Area formatting: rai-ngan-sqWa
        const rai = item["พื้นที่ดิน (ไร่)"];
        const ngan = item["พื้นที่ดิน (งาน)"];
        const sqWa = item["พื้นที่ดิน (ตร.ว.)"];
        let landAreaStr = "-";
        
        if (rai || ngan || sqWa) {
            const raiText = rai ? rai + " ไร่ " : "";
            const nganText = ngan ? ngan + " งาน " : "";
            const sqWaText = sqWa ? sqWa + " ตร.ว." : "";
            landAreaStr = (raiText + nganText + sqWaText).trim() || "-";
        }

        const usableArea = item["พื้นที่ใช้สอย (ตร.ม.)"];
        const usableAreaStr = (usableArea && usableArea !== "undefined") ? usableArea + " ตร.ม." : "-";

        row.innerHTML = `
            <td style="font-weight: 700;">${item["รหัสทรัพย์"] || "-"}</td>
            <td title="${item["ชื่อประกาศ"]}">${item["ชื่อประกาศ"] || "-"}</td>
            <td><span class="badge-type">${item["ประเภททรัพย์"] || "-"}</span></td>
            <td>${landAreaStr}</td>
            <td>${usableAreaStr}</td>
            <td>${priceHtml}</td>
            <td>${item["จังหวัด"] || "-"}</td>
            <td>
                ${item["ลิงก์"] ? `<a class="table-link" href="${item["ลิงก์"]}" target="_blank"><i class="fa-solid fa-up-right-from-square"></i> ดูของจริง</a>` : "-"}
            </td>
        `;

        tableBody.appendChild(row);
    });

    // Update pagination labels
    document.getElementById("pagination-info").textContent = `แสดงรายการ ${startIndex + 1} - ${endIndex} จาก ${filteredData.length} รายการ`;

    // Disable / Enable pagination buttons
    document.getElementById("btn-page-prev").disabled = (currentPage === 1);
    document.getElementById("btn-page-next").disabled = (currentPage * itemsPerPage >= filteredData.length);
}

// 10. Wire up all DOM event listeners
function setupEventListeners() {
    // Dropdowns filter events
    document.getElementById("filter-type").addEventListener("change", applyFilters);
    document.getElementById("filter-province").addEventListener("change", e => {
        updateDistrictFilter(e.target.value);
        applyFilters();
    });
    document.getElementById("filter-district").addEventListener("change", applyFilters);
    
    // Range/Price filter events
    document.getElementById("filter-price-min").addEventListener("input", applyFilters);
    document.getElementById("filter-price-max").addEventListener("input", applyFilters);
    document.getElementById("filter-area-min").addEventListener("input", applyFilters);
    document.getElementById("search-input").addEventListener("input", applyFilters);

    // Reset button clicked
    document.getElementById("btn-reset-filters").addEventListener("click", resetFilters);

    // Chart Tabs Clicked
    const tabBtns = document.querySelectorAll(".chart-tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", e => {
            tabBtns.forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            currentChartTab = e.target.getAttribute("data-chart");
            renderChart();
        });
    });

    // Pagination Clicked
    document.getElementById("btn-page-prev").addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });

    document.getElementById("btn-page-next").addEventListener("click", () => {
        if (currentPage * itemsPerPage < filteredData.length) {
            currentPage++;
            renderTable();
        }
    });
}
