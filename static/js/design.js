async function loadMetrics() {
    const response = await fetch("/api/metrics");
    const data = await response.json();

    const status = document.getElementById("system-status");

    if (status) {
        status.innerText = data.system_status || "N/A";
        document.getElementById("cpu").innerText = data.cpu_percent ?? 0;
        document.getElementById("memory").innerText = data.memory_percent ?? 0;
        document.getElementById("disk").innerText = data.disk_percent ?? 0;
        document.getElementById("last-updated").innerText =
            "Last updated: " + (data.timestamp || "N/A");
    }
}

async function loadContainers() {
    const response = await fetch("/api/containers");
    const data = await response.json();

    const table = document.getElementById("containers-table");

    if (table) {
        table.innerHTML = "";

        data.forEach(container => {
            table.innerHTML += `
                <tr>
                    <td>${container.name}</td>
                    <td>${container.status}</td>
                    <td>${container.cpu_percent ?? 0}%</td>
                    <td>${container.memory_usage || "N/A"}</td>
                    <td>${container.uptime || "N/A"}</td>
                </tr>
            `;
        });
    }
}

async function loadAlerts() {
    const response = await fetch("/api/alerts");
    const data = await response.json();

    const table = document.getElementById("alerts-table");

    if (table) {
        table.innerHTML = "";

        data.forEach(alert => {
            table.innerHTML += `
                <tr>
                    <td>${alert.severity}</td>
                    <td>${alert.message}</td>
                    <td>${alert.source}</td>
                    <td>${alert.status}</td>
                </tr>
            `;
        });
    }
}

if (document.getElementById("system-status")) {
    loadMetrics();
}

if (document.getElementById("containers-table")) {
    loadContainers();
}

if (document.getElementById("alerts-table")) {
    loadAlerts();
}

setInterval(loadMetrics, 5000);