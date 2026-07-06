// ----------------------------------------------------
// 9routerpm Frontend App Logic
// ----------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    // API base URL
    const API_URL = "";

    // App state
    let instances = [];
    let deleteAppName = "";
    
    // Hermes state
    let hermesProfiles = [];
    let hermesDeleteName = "";
    let activeTab = "proxy"; // proxy, hermes
    let hermesInstalled = false;
    let installInterval = null;
    let currentLogAppType = "proxy"; // proxy, hermes

    // Elements
    const proxyListContainer = document.getElementById("proxy-list-container");
    const statTotal = document.getElementById("stat-total");
    const statActive = document.getElementById("stat-active");
    const statCpu = document.getElementById("stat-cpu");
    const statMemory = document.getElementById("stat-memory");
    const searchInput = document.getElementById("search-input");
    const createForm = document.getElementById("create-form");
    const configForm = document.getElementById("config-form");
    const configFieldsContainer = document.getElementById("config-fields-container");
    const logContentContainer = document.getElementById("log-content-container");
    const logAppNameSpan = document.getElementById("log-app-name");
    const configAppNameSpan = document.getElementById("config-app-name");
    const deleteAppNameSpan = document.getElementById("delete-app-name");
    const btnConfirmDelete = document.getElementById("btn-confirm-delete");
    const btnRefreshLogs = document.getElementById("btn-refresh-logs");

    let currentLogApp = "";

    // Tab buttons
    const tabBtnProxy = document.getElementById("tab-btn-proxy");
    const tabBtnHermes = document.getElementById("tab-btn-hermes");
    const tabBtnCleanup = document.getElementById("tab-btn-cleanup");
    const tabBtnAlerts = document.getElementById("tab-btn-alerts");
    const sectionProxy = document.getElementById("section-proxy");
    const sectionHermes = document.getElementById("section-hermes");
    const sectionCleanup = document.getElementById("section-cleanup");
    const sectionAlerts = document.getElementById("section-alerts");
    const btnOpenProxyModal = document.getElementById("btn-open-create-modal");
    const btnOpenHermesModal = document.getElementById("btn-open-hermes-create-modal");

    // Cleanup elements
    const btnScanCleanup = document.getElementById("btn-scan-cleanup");
    const btnPurgeCleanup = document.getElementById("btn-purge-cleanup");
    const badgeTasksCount = document.getElementById("badge-tasks-count");
    const badgePidsCount = document.getElementById("badge-pids-count");
    const tableBodyTasks = document.getElementById("table-body-tasks");
    const tableBodyPids = document.getElementById("table-body-pids");
    const checkAllTasks = document.getElementById("check-all-tasks");
    const checkAllPids = document.getElementById("check-all-pids");

    // Alerts elements
    const btnSaveAlerts = document.getElementById("btn-save-alerts");
    const alertsGlobalEnabled = document.getElementById("alerts-global-enabled");
    const alertsCheckInterval = document.getElementById("alerts-check-interval");
    const alertsProfilesContainer = document.getElementById("alerts-profiles-container");

    // Initialization
    fetchSystemStatus();
    fetchInstances();
    
    // Setup Tab click listeners
    tabBtnProxy.addEventListener("click", () => switchTab("proxy"));
    tabBtnHermes.addEventListener("click", () => switchTab("hermes"));
    tabBtnCleanup.addEventListener("click", () => switchTab("cleanup"));
    tabBtnAlerts.addEventListener("click", () => switchTab("alerts"));

    function switchTab(tab) {
        activeTab = tab;
        // Reset classes
        tabBtnProxy.classList.remove("active");
        tabBtnHermes.classList.remove("active");
        tabBtnCleanup.classList.remove("active");
        tabBtnAlerts.classList.remove("active");
        
        // Hide sections
        sectionProxy.style.display = "none";
        sectionHermes.style.display = "none";
        sectionCleanup.style.display = "none";
        sectionAlerts.style.display = "none";
        
        btnOpenProxyModal.style.display = "none";
        btnOpenHermesModal.style.display = "none";
        
        if (tab === "proxy") {
            tabBtnProxy.classList.add("active");
            sectionProxy.style.display = "block";
            btnOpenProxyModal.style.display = "block";
            fetchInstances();
        } else if (tab === "hermes") {
            tabBtnHermes.classList.add("active");
            sectionHermes.style.display = "block";
            btnOpenHermesModal.style.display = "block";
            checkHermesStatus();
        } else if (tab === "cleanup") {
            tabBtnCleanup.classList.add("active");
            sectionCleanup.style.display = "block";
        } else if (tab === "alerts") {
            tabBtnAlerts.classList.add("active");
            sectionAlerts.style.display = "block";
            loadAlertsConfig();
        }
    }

    // Auto-refresh stats and process status every 5 seconds
    const refreshInterval = setInterval(() => {
        fetchSystemStatus();
        if (activeTab === "proxy") {
            fetchInstances(false); // fetch silently without loading spinner
        } else if (activeTab === "hermes" && hermesInstalled) {
            fetchHermesProfiles(false);
        }
    }, 5000);

    // --- API Calls ---

    async function fetchSystemStatus() {
        try {
            const response = await fetch(`${API_URL}/api/status`);
            const data = await response.json();
            const badge = document.getElementById("pm2-status-badge");
            
            if (data.pm2_installed) {
                badge.className = "status-indicator";
                badge.querySelector(".text").textContent = "PM2: Đang kết nối";
            } else {
                badge.className = "status-indicator offline";
                badge.querySelector(".text").textContent = "PM2: Chưa cài đặt";
                showToast("Cảnh báo: PM2 chưa được cài đặt trên hệ thống Windows của bạn!", "error");
            }
        } catch (error) {
            console.error("Error fetching system status:", error);
            const badge = document.getElementById("pm2-status-badge");
            badge.className = "status-indicator offline";
            badge.querySelector(".text").textContent = "Backend: Lỗi kết nối";
        }
    }

    async function fetchInstances(showLoading = true) {
        if (showLoading && proxyListContainer) {
            proxyListContainer.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Đang tải dữ liệu tiến trình...</p>
                </div>
            `;
        }

        try {
            const response = await fetch(`${API_URL}/api/instances`);
            if (!response.ok) throw new Error("Không thể tải danh sách proxy.");
            instances = await response.json();
            
            renderStats();
            renderInstances();
        } catch (error) {
            console.error("Error fetching instances:", error);
            if (proxyListContainer) {
                proxyListContainer.innerHTML = `
                    <div class="loading-state">
                        <i class="fa-solid fa-circle-exclamation" style="font-size: 2.5rem; color: var(--accent-red);"></i>
                        <p style="margin-top: 1rem;">Không thể kết nối đến API backend.</p>
                        <button class="btn btn-secondary" onclick="window.location.reload()"><i class="fa-solid fa-arrows-rotate"></i> Thử lại</button>
                    </div>
                `;
            }
            showToast("Lỗi: Không thể kết nối đến server quản lý.", "error");
        }
    }

    async function handleAction(name, action, payload = {}) {
        showToast(`Đang thực hiện lệnh ${action.toUpperCase()} cho ${name}...`, "info");
        try {
            const response = await fetch(`${API_URL}/api/instances/${name}/action`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action, ...payload })
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.detail, "success");
                fetchInstances(false);
                fetchSystemStatus();
            } else {
                throw new Error(data.detail || "Thao tác thất bại.");
            }
        } catch (error) {
            console.error(`Error executing action ${action} on ${name}:`, error);
            showToast(error.message, "error");
        }
    }

    // --- Stats & Rendering ---

    function renderStats() {
        statTotal.textContent = instances.length;
        
        const activeCount = instances.filter(i => i.status === "online").length;
        statActive.textContent = activeCount;

        // Tính tổng CPU và RAM sử dụng thực tế
        let totalCpu = 0;
        let totalMemBytes = 0;
        
        instances.forEach(i => {
            if (i.status === "online") {
                totalCpu += i.cpu || 0;
                totalMemBytes += i.memory || 0;
            }
        });

        statCpu.textContent = `${totalCpu.toFixed(1)}%`;
        statMemory.textContent = `${(totalMemBytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function renderInstances() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const filtered = instances.filter(i => {
            return i.name.toLowerCase().includes(searchTerm) || 
                   i.port.toString().includes(searchTerm);
        });

        if (filtered.length === 0) {
            proxyListContainer.innerHTML = `
                <div class="loading-state">
                    <i class="fa-solid fa-box-open" style="font-size: 2.5rem; color: var(--text-dimmed);"></i>
                    <p style="margin-top: 1rem;">Không tìm thấy proxy instance nào.</p>
                </div>
            `;
            return;
        }

        proxyListContainer.innerHTML = filtered.map(i => {
            const statusClass = i.status === "online" ? "online" : (i.status === "errored" ? "errored" : "offline");
            const ramMB = ((i.memory || 0) / (1024 * 1024)).toFixed(1);
            
            // Format CPU và Memory progress bars
            const cpuPercent = Math.min(i.cpu || 0, 100);
            const memPercent = Math.min((i.memory || 0) / (250 * 1024 * 1024) * 100, 100); // 250MB là mốc tối đa hiển thị bar
            
            // Format uptime
            let uptimeText = "N/A";
            if (i.status === "online" && i.uptime) {
                const diffMs = Date.now() - i.uptime;
                const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
                const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
                uptimeText = diffHrs > 0 ? `${diffHrs} giờ ${diffMins} phút` : `${diffMins} phút`;
            }

            return `
                <div class="proxy-card ${statusClass}">
                    <div class="card-header">
                        <div class="card-title-area">
                            <h4>${i.name}</h4>
                            <span class="port-info"><i class="fa-solid fa-ethernet"></i> Cổng: ${i.port}</span>
                        </div>
                        <span class="badge ${statusClass}">
                            <span class="dot"></span>
                            ${i.status}
                        </span>
                    </div>

                    <div class="card-content">
                        <div class="info-row">
                            <span class="label">Đường dẫn:</span>
                            <span class="value" title="${i.path}">${i.path}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">PID tiến trình:</span>
                            <span class="value">${i.pid || "N/A"}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Số lần khởi động lại:</span>
                            <span class="value">${i.restart_count || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Thời gian chạy:</span>
                            <span class="value">${uptimeText}</span>
                        </div>

                        <!-- CPU Bar -->
                        <div class="stat-bar-group" style="margin-top: 0.5rem;">
                            <div class="stat-bar-label">
                                <span>CPU</span>
                                <span>${(i.cpu || 0).toFixed(1)}%</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${cpuPercent}%;"></div>
                            </div>
                        </div>

                        <!-- RAM Bar -->
                        <div class="stat-bar-group">
                            <div class="stat-bar-label">
                                <span>Bộ nhớ RAM</span>
                                <span>${ramMB} MB</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${memPercent}%; background: linear-gradient(to right, var(--accent-orange), var(--accent-purple));"></div>
                            </div>
                        </div>
                    </div>

                    <div class="card-actions">
                        <div class="action-buttons-left">
                            ${i.status === "online" ? 
                                `<button class="btn btn-icon btn-stop" data-action="stop" data-name="${i.name}" title="Dừng hoạt động"><i class="fa-solid fa-stop"></i></button>` :
                                `<button class="btn btn-icon btn-start" data-action="start" data-name="${i.name}" title="Bắt đầu chạy"><i class="fa-solid fa-play"></i></button>`
                            }
                            <button class="btn btn-icon" data-action="restart" data-name="${i.name}" title="Khởi động lại"><i class="fa-solid fa-arrows-rotate"></i></button>
                        </div>
                        <div class="action-buttons-right">
                            <button class="btn btn-icon" data-action="logs" data-name="${i.name}" title="Xem Logs"><i class="fa-solid fa-terminal"></i></button>
                            <button class="btn btn-icon" data-action="config" data-name="${i.name}" title="Sửa file .env"><i class="fa-solid fa-sliders"></i></button>
                            <button class="btn btn-icon" data-action="delete-confirm" data-name="${i.name}" title="Xóa Proxy"><i class="fa-solid fa-trash-can"></i></button>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        // Gắn sự kiện click cho các nút hành động sau khi render
        attachActionListeners();
    }

    function attachActionListeners() {
        document.querySelectorAll("[data-action]").forEach(btn => {
            btn.addEventListener("click", e => {
                // Đảm bảo lấy đúng nút dù click vào icon bên trong
                const targetBtn = e.target.closest("[data-action]");
                const action = targetBtn.getAttribute("data-action");
                const name = targetBtn.getAttribute("data-name");

                if (action === "start" || action === "stop" || action === "restart") {
                    handleAction(name, action);
                } else if (action === "logs") {
                    openLogsModal(name);
                } else if (action === "config") {
                    openConfigModal(name);
                } else if (action === "delete-confirm") {
                    openDeleteModal(name);
                }
            });
        });
    }

    // --- Search ---
    searchInput.addEventListener("input", () => {
        renderInstances();
    });

    // --- Modals Management ---

    // Open/Close Modals using Attributes
    document.querySelectorAll("[data-modal]").forEach(elem => {
        elem.addEventListener("click", e => {
            const modalId = e.target.closest("[data-modal]").getAttribute("data-modal");
            closeModal(modalId);
        });
    });

    const newSrcSelect = document.getElementById("new-src-select");
    const customSrcGroup = document.getElementById("custom-src-group");
    const newSrcDirInput = document.getElementById("new-src-dir");

    if (newSrcSelect) {
        newSrcSelect.addEventListener("change", (e) => {
            const val = e.target.value;
            const scriptInput = document.getElementById("new-script");
            const argsInput = document.getElementById("new-args");

            if (val === "__custom__") {
                customSrcGroup.style.display = "block";
                newSrcDirInput.setAttribute("required", "required");
                newSrcDirInput.focus();
            } else {
                customSrcGroup.style.display = "none";
                newSrcDirInput.removeAttribute("required");
            }

            // Tự động thiết lập script khởi chạy dựa trên nguồn được chọn
            if (val && (val.toLowerCase().endsWith("node_modules\\9router") || val.toLowerCase().endsWith("node_modules/9router"))) {
                if (scriptInput) scriptInput.value = "app/custom-server.js";
                if (argsInput) argsInput.value = "";
            } else {
                if (scriptInput) scriptInput.value = "npm";
                if (argsInput) argsInput.value = "start";
            }
        });
    }

    async function loadDetectedSources() {
        if (!newSrcSelect) return;
        newSrcSelect.innerHTML = `<option value="">-- Đang quét hệ thống... --</option>`;
        
        try {
            const response = await fetch(`${API_URL}/api/detect-sources`);
            if (!response.ok) throw new Error("Lỗi gọi API quét nguồn");
            const sources = await response.json();
            
            let htmlOptions = `<option value="">-- Chọn thư mục 9router nguồn --</option>`;
            sources.forEach(src => {
                htmlOptions += `<option value="${escapeHtml(src.path)}">${escapeHtml(src.name)} (${escapeHtml(src.path)})</option>`;
            });
            htmlOptions += `<option value="__custom__">🔍 Tự nhập đường dẫn khác...</option>`;
            newSrcSelect.innerHTML = htmlOptions;
        } catch (error) {
            console.error("Error loading detected sources:", error);
            newSrcSelect.innerHTML = `
                <option value="">-- Lỗi khi quét nguồn --</option>
                <option value="__custom__">🔍 Tự nhập đường dẫn khác...</option>
            `;
        }
    }

    document.getElementById("btn-open-create-modal").addEventListener("click", () => {
        openModal("create-modal");
        loadDetectedSources();
        customSrcGroup.style.display = "none";
        newSrcDirInput.removeAttribute("required");
    });

    function openModal(id) {
        document.getElementById(id).classList.add("active");
    }

    function closeModal(id) {
        document.getElementById(id).classList.remove("active");
        if (id === "delete-modal") {
            document.getElementById("delete-files-checkbox").checked = false;
        }
    }

    // --- Create Form Submission ---
    createForm.addEventListener("submit", async e => {
        e.preventDefault();

        let srcDir = newSrcSelect.value;
        if (srcDir === "__custom__" || !srcDir) {
            srcDir = newSrcDirInput.value.trim();
        }

        if (!srcDir) {
            showToast("Vui lòng nhập hoặc chọn thư mục 9router nguồn.", "error");
            return;
        }

        const payload = {
            name: document.getElementById("new-name").value.trim(),
            src_dir: srcDir,
            port: document.getElementById("new-port").value ? parseInt(document.getElementById("new-port").value) : null,
            script: document.getElementById("new-script").value.trim(),
            args: document.getElementById("new-args").value.trim(),
            api_key: document.getElementById("new-apikey").value.trim()
        };

        closeModal("create-modal");
        showToast("Đang tạo và cấu hình instance proxy mới (việc này có thể mất 15-30 giây)...", "info");

        try {
            const response = await fetch(`${API_URL}/api/instances`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.detail, "success");
                createForm.reset();
                // Set default values again
                document.getElementById("new-script").value = "npm";
                document.getElementById("new-args").value = "start";
                fetchInstances();
            } else {
                throw new Error(data.detail || "Không thể tạo instance.");
            }
        } catch (error) {
            console.error("Error creating instance:", error);
            showToast(error.message, "error");
        }
    });

    // --- Logs Modal ---
    async function openLogsModal(name) {
        currentLogApp = name;
        logAppNameSpan.textContent = name;
        logContentContainer.innerHTML = "Đang tải dữ liệu logs từ PM2...";
        openModal("logs-modal");
        await fetchLogs(name);
    }

    async function fetchLogs(name) {
        try {
            const response = await fetch(`${API_URL}/api/instances/${name}/logs`);
            const data = await response.json();
            if (response.ok) {
                // Tách các dòng log và thêm style màu sắc cơ bản
                const lines = data.logs.split("\n");
                logContentContainer.innerHTML = lines.map(line => {
                    if (line.includes("[STDERR]")) {
                        return `<span style="color: var(--accent-red);">${escapeHtml(line)}</span>`;
                    }
                    return `<span>${escapeHtml(line)}</span>`;
                }).join("\n");
                
                // Cuộn xuống cuối logs
                logContentContainer.scrollTop = logContentContainer.scrollHeight;
            } else {
                logContentContainer.innerHTML = `Lỗi: ${data.detail || "Không thể đọc log."}`;
            }
        } catch (error) {
            logContentContainer.innerHTML = `Lỗi kết nối API log: ${error.message}`;
        }
    }

    btnRefreshLogs.addEventListener("click", () => {
        if (currentLogApp) {
            fetchLogs(currentLogApp);
            showToast("Đã cập nhật logs mới nhất.", "success");
        }
    });

    // --- Config Modal ---
    async function openConfigModal(name) {
        configAppNameSpan.textContent = name;
        configFieldsContainer.innerHTML = "<p>Đang đọc file cấu hình .env...</p>";
        openModal("config-modal");

        try {
            const response = await fetch(`${API_URL}/api/instances/${name}/config`);
            if (!response.ok) throw new Error("Không thể đọc file cấu hình.");
            const configData = await response.json();

            // Sinh các trường nhập liệu động
            configFieldsContainer.innerHTML = Object.entries(configData).map(([key, val]) => {
                const inputType = key === "API_KEY" ? "password" : (key === "PORT" ? "number" : "text");
                return `
                    <div class="form-group">
                        <label for="cfg-${key}">${key}</label>
                        <input type="${inputType}" id="cfg-${key}" data-key="${key}" value="${escapeHtml(val)}" required>
                    </div>
                `;
            }).join("");

            // Lưu tên ứng dụng hiện tại vào form data
            configForm.setAttribute("data-name", name);
        } catch (error) {
            configFieldsContainer.innerHTML = `<p style="color: var(--accent-red);">Lỗi: ${error.message}</p>`;
        }
    }

    configForm.addEventListener("submit", async e => {
        e.preventDefault();
        const name = configForm.getAttribute("data-name");
        const inputs = configFieldsContainer.querySelectorAll("input");
        const newConfig = {};

        inputs.forEach(input => {
            const key = input.getAttribute("data-key");
            newConfig[key] = input.value.trim();
        });

        closeModal("config-modal");
        showToast(`Đang cập nhật cấu hình cho '${name}' và khởi động lại...`, "info");

        try {
            const response = await fetch(`${API_URL}/api/instances/${name}/config`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(newConfig)
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.detail, "success");
                fetchInstances(false);
            } else {
                throw new Error(data.detail || "Không thể cập nhật cấu hình.");
            }
        } catch (error) {
            showToast(error.message, "error");
        }
    });

    // --- Delete Modal ---
    function openDeleteModal(name) {
        deleteAppName = name;
        deleteAppNameSpan.textContent = name;
        openModal("delete-modal");
    }

    btnConfirmDelete.addEventListener("click", () => {
        if (deleteAppName) {
            const deleteFiles = document.getElementById("delete-files-checkbox").checked;
            closeModal("delete-modal");
            handleAction(deleteAppName, "delete", { delete_files: deleteFiles });
            deleteAppName = "";
        }
    });

    // --- Hermes Agent UI Logic & API Interaction ---

    async function checkHermesStatus() {
        try {
            const response = await fetch(`${API_URL}/api/hermes/status`);
            const data = await response.json();
            
            const notInstalledView = document.getElementById("hermes-not-installed-view");
            const installedView = document.getElementById("hermes-installed-view");
            
            if (data.installed) {
                hermesInstalled = true;
                notInstalledView.style.display = "none";
                installedView.style.display = "block";
                fetchHermesProfiles();
            } else {
                hermesInstalled = false;
                notInstalledView.style.display = "block";
                installedView.style.display = "none";
                
                // Nếu đang cài đặt dở dang (ví dụ load lại trang)
                if (data.install_state && data.install_state.status === "running") {
                    showInstallProgressBox(data.install_state);
                }
            }
        } catch (error) {
            console.error("Error checking hermes status:", error);
            showToast("Không thể kiểm tra trạng thái cài đặt Hermes.", "error");
        }
    }

    const btnInstallHermes = document.getElementById("btn-install-hermes");
    if (btnInstallHermes) {
        btnInstallHermes.addEventListener("click", async () => {
            showToast("Bắt đầu khởi chạy trình cài đặt tự động...", "info");
            try {
                const response = await fetch(`${API_URL}/api/hermes/install`, { method: "POST" });
                const data = await response.json();
                if (response.ok && data.success) {
                    showToast(data.detail, "success");
                    // Bắt đầu poll progress
                    pollInstallProgress();
                } else {
                    throw new Error(data.detail || "Không thể kích hoạt cài đặt.");
                }
            } catch (error) {
                showToast(error.message, "error");
            }
        });
    }

    function showInstallProgressBox(state) {
        const progressBox = document.getElementById("hermes-install-progress-box");
        progressBox.style.display = "block";
        btnInstallHermes.style.display = "none";
        
        document.getElementById("install-progress-text").textContent = "Trạng thái: " + state.status;
        document.getElementById("install-progress-percent").textContent = state.progress + "%";
        document.getElementById("install-progress-bar").style.width = state.progress + "%";
        
        const logsArea = document.getElementById("hermes-install-logs");
        logsArea.textContent = state.log;
        logsArea.scrollTop = logsArea.scrollHeight;
        
        if (!installInterval) {
            pollInstallProgress();
        }
    }

    function pollInstallProgress() {
        if (installInterval) clearInterval(installInterval);
        
        installInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_URL}/api/hermes/install/progress`);
                const state = await response.json();
                
                showInstallProgressBox(state);
                
                if (state.status === "success") {
                    clearInterval(installInterval);
                    installInterval = null;
                    showToast("Cài đặt Hermes Agent thành công!", "success");
                    setTimeout(() => {
                        checkHermesStatus();
                        // Reset lại button
                        btnInstallHermes.style.display = "inline-block";
                        document.getElementById("hermes-install-progress-box").style.display = "none";
                    }, 2000);
                } else if (state.status === "failed") {
                    clearInterval(installInterval);
                    installInterval = null;
                    showToast("Cài đặt thất bại! Vui lòng kiểm tra log.", "error");
                    btnInstallHermes.style.display = "inline-block";
                }
            } catch (error) {
                console.error("Error polling install progress:", error);
            }
        }, 1500);
    }

    async function fetchHermesProfiles(showLoading = true) {
        const container = document.getElementById("hermes-list-container");
        if (showLoading && container) {
            container.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Đang tải danh sách profile...</p>
                </div>
            `;
        }

        try {
            const response = await fetch(`${API_URL}/api/hermes/profiles`);
            if (!response.ok) throw new Error("Không thể tải danh sách profile.");
            hermesProfiles = await response.json();
            
            renderHermesStats();
            renderHermesProfiles();
        } catch (error) {
            console.error("Error fetching hermes profiles:", error);
            if (container) {
                container.innerHTML = `<p style="color: var(--accent-red); text-align: center;">Lỗi tải profile: ${error.message}</p>`;
            }
        }
    }

    function renderHermesStats() {
        document.getElementById("hermes-stat-total").textContent = hermesProfiles.length;
        const activeCount = hermesProfiles.filter(p => p.status === "online").length;
        document.getElementById("hermes-stat-active").textContent = activeCount;

        let totalCpu = 0;
        let totalMemBytes = 0;
        
        hermesProfiles.forEach(p => {
            if (p.status === "online") {
                totalCpu += p.cpu || 0;
                totalMemBytes += p.memory || 0;
            }
        });

        document.getElementById("hermes-stat-cpu").textContent = `${totalCpu.toFixed(1)}%`;
        document.getElementById("hermes-stat-memory").textContent = `${(totalMemBytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function renderHermesProfiles() {
        const container = document.getElementById("hermes-list-container");
        const searchTerm = document.getElementById("hermes-search-input").value.toLowerCase().trim();
        
        const filtered = hermesProfiles.filter(p => p.name.toLowerCase().includes(searchTerm));
        
        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="loading-state">
                    <i class="fa-solid fa-box-open" style="font-size: 2.5rem; color: var(--text-dimmed);"></i>
                    <p style="margin-top: 1rem;">Không tìm thấy profile nào.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(p => {
            const statusClass = p.status === "online" ? "online" : (p.status === "errored" ? "errored" : "offline");
            const ramMB = ((p.memory || 0) / (1024 * 1024)).toFixed(1);
            const cpuPercent = Math.min(p.cpu || 0, 100);
            const memPercent = Math.min((p.memory || 0) / (250 * 1024 * 1024) * 100, 100);
            
            let uptimeText = "N/A";
            if (p.status === "online" && p.uptime) {
                const diffMs = Date.now() - p.uptime;
                const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
                const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
                uptimeText = diffHrs > 0 ? `${diffHrs} giờ ${diffMins} phút` : `${diffMins} phút`;
            }

            return `
                <div class="proxy-card hermes-card ${statusClass}">
                    <div class="card-header">
                        <div class="card-title-area">
                            <h4>${p.name}</h4>
                            <span class="port-info"><i class="fa-solid fa-brain"></i> Model: ${p.model_default || "N/A"}</span>
                        </div>
                        <span class="badge ${statusClass}">
                            <span class="dot"></span>
                            ${p.status}
                        </span>
                    </div>

                    <div class="card-content">
                        <div class="info-row">
                            <span class="label">Base URL:</span>
                            <span class="value" title="${p.base_url}">${p.base_url || "N/A"}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">PID:</span>
                            <span class="value">${p.pid || "N/A"}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Restart Count:</span>
                            <span class="value">${p.restart_count || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Uptime:</span>
                            <span class="value">${uptimeText}</span>
                        </div>

                        <!-- CPU Bar -->
                        <div class="stat-bar-group" style="margin-top: 0.5rem;">
                            <div class="stat-bar-label">
                                <span>CPU</span>
                                <span>${(p.cpu || 0).toFixed(1)}%</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${cpuPercent}%; background: var(--accent-purple);"></div>
                            </div>
                        </div>

                        <!-- RAM Bar -->
                        <div class="stat-bar-group">
                            <div class="stat-bar-label">
                                <span>Bộ nhớ RAM</span>
                                <span>${ramMB} MB</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${memPercent}%; background: linear-gradient(to right, var(--accent-purple), var(--secondary));"></div>
                            </div>
                        </div>
                    </div>

                    <div class="card-actions">
                        <div class="action-buttons-left">
                            ${p.status === "online" ? 
                                `<button class="btn btn-icon btn-stop" data-hermes-action="stop" data-name="${p.name}" title="Dừng hoạt động"><i class="fa-solid fa-stop"></i></button>` :
                                `<button class="btn btn-icon btn-start" data-hermes-action="start" data-name="${p.name}" title="Bắt đầu chạy"><i class="fa-solid fa-play"></i></button>`
                            }
                            <button class="btn btn-icon" data-hermes-action="restart" data-name="${p.name}" title="Khởi động lại"><i class="fa-solid fa-arrows-rotate"></i></button>
                        </div>
                        <div class="action-buttons-right">
                            <button class="btn btn-icon" data-hermes-action="logs" data-name="${p.name}" title="Xem Logs"><i class="fa-solid fa-terminal"></i></button>
                            <button class="btn btn-icon" data-hermes-action="config" data-name="${p.name}" title="Sửa config.yaml"><i class="fa-solid fa-sliders"></i></button>
                            ${p.name !== "default" ? 
                                `<button class="btn btn-icon" data-hermes-action="delete-confirm" data-name="${p.name}" title="Xóa Profile"><i class="fa-solid fa-trash-can"></i></button>` : 
                                ``
                            }
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        attachHermesActionListeners();
    }

    function attachHermesActionListeners() {
        document.querySelectorAll("[data-hermes-action]").forEach(btn => {
            btn.addEventListener("click", e => {
                const targetBtn = e.target.closest("[data-hermes-action]");
                const action = targetBtn.getAttribute("data-hermes-action");
                const name = targetBtn.getAttribute("data-name");

                if (action === "start" || action === "stop" || action === "restart") {
                    handleHermesAction(name, action);
                } else if (action === "logs") {
                    openHermesLogsModal(name);
                } else if (action === "config") {
                    openHermesConfigModal(name);
                } else if (action === "delete-confirm") {
                    openHermesDeleteModal(name);
                }
            });
        });
    }

    async function handleHermesAction(name, action) {
        showToast(`Đang thực hiện lệnh ${action.toUpperCase()} cho Hermes: ${name}...`, "info");
        try {
            const response = await fetch(`${API_URL}/api/hermes/profiles/${name}/action`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action })
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.detail, "success");
                fetchHermesProfiles(false);
            } else {
                throw new Error(data.detail || "Thao tác thất bại.");
            }
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    async function openHermesLogsModal(name) {
        currentLogApp = name;
        currentLogAppType = "hermes";
        document.getElementById("log-app-name").textContent = "Hermes Profile: " + name;
        logContentContainer.innerHTML = "Đang tải dữ liệu logs từ PM2...";
        openModal("logs-modal");
        await fetchHermesLogs(name);
    }

    async function fetchHermesLogs(name) {
        try {
            const response = await fetch(`${API_URL}/api/hermes/profiles/${name}/logs`);
            const data = await response.json();
            if (response.ok) {
                const lines = data.logs.split("\n");
                logContentContainer.innerHTML = lines.map(line => {
                    if (line.includes("[STDERR]")) {
                        return `<span style="color: var(--accent-red);">${escapeHtml(line)}</span>`;
                    }
                    return `<span>${escapeHtml(line)}</span>`;
                }).join("\n");
                logContentContainer.scrollTop = logContentContainer.scrollHeight;
            } else {
                logContentContainer.innerHTML = `Lỗi: ${data.detail || "Không thể đọc log."}`;
            }
        } catch (error) {
            logContentContainer.innerHTML = `Lỗi kết nối API log: ${error.message}`;
        }
    }

    // Gắn thêm sự kiện refresh logs chung cho cả hermes
    btnRefreshLogs.addEventListener("click", () => {
        if (currentLogApp && currentLogAppType === "hermes") {
            fetchHermesLogs(currentLogApp);
            showToast("Đã cập nhật logs Hermes mới nhất.", "success");
        }
    });

    // Thêm Listeners cho Tìm kiếm Hermes
    document.getElementById("hermes-search-input").addEventListener("input", () => {
        renderHermesProfiles();
    });

    // --- Modal Create Hermes Profile ---
    const hOpenCreateBtn = document.getElementById("btn-open-hermes-create-modal");
    const hLinkSelect = document.getElementById("h-new-link-select");
    const hCustomFields = document.getElementById("h-custom-model-fields");
    const hCreateForm = document.getElementById("hermes-create-form");

    if (hOpenCreateBtn) {
        hOpenCreateBtn.addEventListener("click", () => {
            // Fill danh sách proxy
            let optionsHtml = `<option value="">-- Chọn Model Backend liên kết --</option>`;
            instances.forEach(ins => {
                optionsHtml += `<option value="${ins.port}" data-key="${ins.name}">${ins.name} (Cổng ${ins.port})</option>`;
            });
            optionsHtml += `<option value="__custom__">⚙️ Tự nhập cấu hình khác...</option>`;
            hLinkSelect.innerHTML = optionsHtml;
            
            hCustomFields.style.display = "none";
            document.getElementById("h-new-provider").removeAttribute("required");
            document.getElementById("h-new-base-url").removeAttribute("required");
            
            hCreateForm.reset();
            openModal("hermes-create-modal");
        });
    }

    if (hLinkSelect) {
        hLinkSelect.addEventListener("change", (e) => {
            const val = e.target.value;
            const modelInput = document.getElementById("h-new-model");
            
            if (val === "__custom__") {
                hCustomFields.style.display = "block";
                document.getElementById("h-new-provider").setAttribute("required", "required");
                document.getElementById("h-new-base-url").setAttribute("required", "required");
                document.getElementById("h-new-provider").value = "custom";
                document.getElementById("h-new-base-url").value = "http://localhost:20128/v1";
                modelInput.value = "editvideo";
            } else if (val) {
                hCustomFields.style.display = "none";
                document.getElementById("h-new-provider").removeAttribute("required");
                document.getElementById("h-new-base-url").removeAttribute("required");
                
                // Lấy tên proxy để làm tên model default
                const selectedOpt = hLinkSelect.options[hLinkSelect.selectedIndex];
                const insName = selectedOpt.getAttribute("data-key");
                modelInput.value = insName;
            }
        });
    }

    if (hCreateForm) {
        hCreateForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const name = document.getElementById("h-new-name").value.trim();
            const linkVal = hLinkSelect.value;
            
            let provider = "custom";
            let baseUrl = "";
            let model = document.getElementById("h-new-model").value.trim();
            
            if (linkVal === "__custom__") {
                provider = document.getElementById("h-new-provider").value.trim();
                baseUrl = document.getElementById("h-new-base-url").value.trim();
            } else {
                baseUrl = `http://localhost:${linkVal}/v1`;
            }
            
            const payload = {
                name,
                default: model,
                provider,
                base_url: baseUrl,
                api_key: document.getElementById("h-new-apikey").value.trim(),
                context_length: parseInt(document.getElementById("h-new-context").value) || 70000
            };
            
            closeModal("hermes-create-modal");
            showToast(`Đang khởi tạo profile Hermes '${name}' và khởi chạy ngầm...`, "info");
            
            try {
                const response = await fetch(`${API_URL}/api/hermes/profiles`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (response.ok && data.success) {
                    showToast(data.detail, "success");
                    fetchHermesProfiles();
                } else {
                    throw new Error(data.detail || "Không thể tạo profile.");
                }
            } catch (error) {
                showToast(error.message, "error");
            }
        });
    }

    // --- Modal Config Hermes Profile ---
    const hConfigForm = document.getElementById("hermes-config-form");
    
    async function openHermesConfigModal(name) {
        document.getElementById("hermes-config-app-name").textContent = name;
        hConfigForm.setAttribute("data-name", name);
        openModal("hermes-config-modal");
        
        // Load data cũ
        try {
            const response = await fetch(`${API_URL}/api/hermes/profiles`);
            const profiles = await response.json();
            const p = profiles.find(profile => profile.name === name);
            if (p) {
                document.getElementById("h-cfg-default").value = p.model_default || "";
                document.getElementById("h-cfg-provider").value = p.provider || "";
                document.getElementById("h-cfg-base-url").value = p.base_url || "";
                document.getElementById("h-cfg-apikey").value = ""; // Để trống password cho bảo mật
                document.getElementById("h-cfg-context").value = p.context_length || 70000;
            }
        } catch (error) {
            showToast("Lỗi tải thông tin cấu hình profile: " + error.message, "error");
        }
    }

    if (hConfigForm) {
        hConfigForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = hConfigForm.getAttribute("data-name");
            
            const payload = {
                default: document.getElementById("h-cfg-default").value.trim(),
                provider: document.getElementById("h-cfg-provider").value.trim(),
                base_url: document.getElementById("h-cfg-base-url").value.trim(),
                api_key: document.getElementById("h-cfg-apikey").value.trim(),
                context_length: parseInt(document.getElementById("h-cfg-context").value) || 70000
            };
            
            closeModal("hermes-config-modal");
            showToast(`Đang cập nhật cấu hình cho profile '${name}'...`, "info");
            
            try {
                const response = await fetch(`${API_URL}/api/hermes/profiles/${name}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (response.ok && data.success) {
                    showToast(data.detail, "success");
                    fetchHermesProfiles(false);
                } else {
                    throw new Error(data.detail || "Không thể cập nhật cấu hình.");
                }
            } catch (error) {
                showToast(error.message, "error");
            }
        });
    }

    // --- Modal Delete Hermes Profile ---
    const btnHermesConfirmDelete = document.getElementById("btn-hermes-confirm-delete");
    
    function openHermesDeleteModal(name) {
        hermesDeleteName = name;
        document.getElementById("hermes-delete-app-name").textContent = name;
        openModal("hermes-delete-modal");
    }

    if (btnHermesConfirmDelete) {
        btnHermesConfirmDelete.addEventListener("click", async () => {
            if (hermesDeleteName) {
                const name = hermesDeleteName;
                closeModal("hermes-delete-modal");
                showToast(`Đang xóa profile Hermes '${name}'...`, "info");
                
                try {
                    const response = await fetch(`${API_URL}/api/hermes/profiles/${name}`, { method: "DELETE" });
                    const data = await response.json();
                    if (response.ok && data.success) {
                        showToast(data.detail, "success");
                        fetchHermesProfiles();
                    } else {
                        throw new Error(data.detail || "Không thể xóa profile.");
                    }
                } catch (error) {
                    showToast(error.message, "error");
                }
                hermesDeleteName = "";
            }
        });
    }

    // --- Toast Notifications System ---
    function showToast(message, type = "success") {
        const toastContainer = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let iconClass = "fa-circle-check";
        if (type === "error") iconClass = "fa-circle-exclamation";
        if (type === "info") iconClass = "fa-circle-info";

        toast.innerHTML = `
            <i class="fa-solid ${iconClass} toast-icon"></i>
            <div class="toast-message">${message}</div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Show after 100ms (for CSS transition)
        setTimeout(() => toast.classList.add("show"), 100);
        
        // Auto-destroy after 4.5 seconds
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 300);
        }, 4500);
    }

    // --- Logic Dọn Dẹp Xung Đột Hệ Thống ---
    let detectedTasks = [];
    let detectedPids = [];

    btnScanCleanup.addEventListener("click", async () => {
        btnScanCleanup.disabled = true;
        btnScanCleanup.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang quét hệ thống...`;
        tableBodyTasks.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 30px;"><div class="spinner" style="margin: 0 auto 10px;"></div> Đang quét các tác vụ lên lịch cũ...</td></tr>`;
        tableBodyPids.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 30px;"><div class="spinner" style="margin: 0 auto 10px;"></div> Đang quét các tiến trình PM2 cũ...</td></tr>`;
        
        try {
            const response = await fetch(`${API_URL}/api/cleanup/scan`);
            const data = await response.json();
            
            detectedTasks = data.scheduled_tasks || [];
            detectedPids = data.pm2_processes || [];
            
            renderCleanupResults();
            showToast(`Đã quét xong: tìm thấy ${detectedTasks.length} tác vụ và ${detectedPids.length} tiến trình PM2 cũ.`, "info");
        } catch (error) {
            console.error("Lỗi quét hệ thống:", error);
            showToast("Lỗi khi quét hệ thống: " + error.message, "error");
            tableBodyTasks.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--danger); padding: 20px;">Lỗi khi tải dữ liệu.</td></tr>`;
            tableBodyPids.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--danger); padding: 20px;">Lỗi khi tải dữ liệu.</td></tr>`;
        } finally {
            btnScanCleanup.disabled = false;
            btnScanCleanup.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Bắt đầu Quét Hệ Thống`;
        }
    });

    function renderCleanupResults() {
        // Render Tasks
        badgeTasksCount.innerText = detectedTasks.length;
        checkAllTasks.checked = false;
        if (detectedTasks.length === 0) {
            tableBodyTasks.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 40px 10px;"><i class="fa-solid fa-circle-check" style="font-size: 2rem; color: var(--accent-emerald); margin-bottom: 10px; display: block;"></i>Sạch sẽ! Không phát hiện tác vụ Scheduler cũ nào xung đột.</td></tr>`;
        } else {
            tableBodyTasks.innerHTML = detectedTasks.map((task, idx) => `
                <tr style="border-bottom: 1px solid var(--border); transition: background 0.2s;">
                    <td style="text-align: center; padding: 12px 10px;"><input type="checkbox" class="task-checkbox" data-name="${escapeHtml(task.name)}" style="transform: scale(1.1); cursor: pointer;"></td>
                    <td style="padding: 12px 10px; font-weight: 500; color: var(--text-main); font-family: monospace;">${escapeHtml(task.name)}</td>
                    <td style="padding: 12px 10px;"><span class="status-badge" style="background: rgba(239, 68, 68, 0.15); color: var(--danger); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500;">${escapeHtml(task.status)}</span></td>
                </tr>
            `).join("");
        }

        // Render PIDs
        badgePidsCount.innerText = detectedPids.length;
        checkAllPids.checked = false;
        if (detectedPids.length === 0) {
            tableBodyPids.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 40px 10px;"><i class="fa-solid fa-circle-check" style="font-size: 2rem; color: var(--accent-emerald); margin-bottom: 10px; display: block;"></i>Sạch sẽ! Không phát hiện tiến trình PM2 cũ nào chạy nổi ngoài luồng.</td></tr>`;
        } else {
            tableBodyPids.innerHTML = detectedPids.map(proc => `
                <tr style="border-bottom: 1px solid var(--border); transition: background 0.2s; ${proc.is_current ? 'background: rgba(59, 130, 246, 0.08);' : ''}">
                    <td style="text-align: center; padding: 12px 10px;"><input type="checkbox" class="pid-checkbox" data-pid="${proc.pid}" style="transform: scale(1.1); cursor: pointer;" ${proc.is_current ? 'disabled' : ''}></td>
                    <td style="padding: 12px 10px; font-weight: bold; color: ${proc.is_current ? 'var(--primary)' : 'var(--text-main)'};">${proc.pid} ${proc.is_current ? '<span style="font-size:0.75rem; font-weight:normal; background: rgba(59,130,246,0.2); color: var(--primary); padding:1px 5px; border-radius:3px; margin-left:5px;">Hiện tại</span>' : ''}</td>
                    <td style="padding: 12px 10px; font-size: 0.85rem; color: var(--text-muted); word-break: break-all; font-family: monospace;" title="${escapeHtml(proc.command_line)}">${escapeHtml(proc.command_line)}</td>
                </tr>
            `).join("");
        }

        // Setup checkboxes events
        setupCleanupCheckboxes();
        togglePurgeButton();
    }

    function setupCleanupCheckboxes() {
        // Check All Tasks
        checkAllTasks.addEventListener("change", () => {
            const checkboxes = tableBodyTasks.querySelectorAll(".task-checkbox");
            checkboxes.forEach(cb => cb.checked = checkAllTasks.checked);
            togglePurgeButton();
        });

        // Check All PIDs
        checkAllPids.addEventListener("change", () => {
            const checkboxes = tableBodyPids.querySelectorAll(".pid-checkbox");
            checkboxes.forEach(cb => {
                if (!cb.disabled) cb.checked = checkAllPids.checked;
            });
            togglePurgeButton();
        });

        // Individual checkboxes
        const allCbs = document.querySelectorAll(".task-checkbox, .pid-checkbox");
        allCbs.forEach(cb => {
            cb.addEventListener("change", togglePurgeButton);
        });
    }

    function togglePurgeButton() {
        const selectedTasks = getSelectedTasks();
        const selectedPids = getSelectedPids();
        
        if (selectedTasks.length > 0 || selectedPids.length > 0) {
            btnPurgeCleanup.style.display = "inline-flex";
            btnPurgeCleanup.innerHTML = `<i class="fa-solid fa-trash-can"></i> XÓA BỎ CÁC MỤC ĐÃ CHỌN (${selectedTasks.length + selectedPids.length})`;
        } else {
            btnPurgeCleanup.style.display = "none";
        }
    }

    function getSelectedTasks() {
        const checkboxes = tableBodyTasks.querySelectorAll(".task-checkbox:checked");
        return Array.from(checkboxes).map(cb => cb.getAttribute("data-name"));
    }

    function getSelectedPids() {
        const checkboxes = tableBodyPids.querySelectorAll(".pid-checkbox:checked");
        return Array.from(checkboxes).map(cb => parseInt(cb.getAttribute("data-pid")));
    }

    btnPurgeCleanup.addEventListener("click", async () => {
        const tasks = getSelectedTasks();
        const pids = getSelectedPids();
        
        if (!confirm(`Bạn có chắc chắn muốn xóa sạch ${tasks.length} tác vụ Scheduler và tiêu diệt ${pids.length} tiến trình PM2 cũ được chọn? Thao tác này không thể hoàn tác!`)) {
            return;
        }
        
        btnPurgeCleanup.disabled = true;
        btnPurgeCleanup.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang dọn dẹp hệ thống...`;
        
        try {
            const response = await fetch(`${API_URL}/api/cleanup/purge`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ tasks, pids })
            });
            const data = await response.json();
            
            const deletedTasksCount = data.tasks_deleted ? data.tasks_deleted.length : 0;
            const killedPidsCount = data.pids_killed ? data.pids_killed.length : 0;
            
            showToast(`Đã dọn dẹp xong: Xóa ${deletedTasksCount} tác vụ Scheduler, tiêu diệt ${killedPidsCount} tiến trình PM2 cũ.`, "success");
            
            if (data.errors && data.errors.length > 0) {
                console.warn("Một số lỗi xảy ra khi dọn dẹp:", data.errors);
                showToast("Có lỗi xảy ra với một vài mục, hãy kiểm tra log console.", "error");
            }
            
            // Tự động quét lại để cập nhật bảng
            btnScanCleanup.click();
        } catch (error) {
            console.error("Lỗi dọn dẹp hệ thống:", error);
            showToast("Lỗi khi dọn dẹp hệ thống: " + error.message, "error");
            btnPurgeCleanup.disabled = false;
            togglePurgeButton();
        }
    });

    // --- Logic Cảnh Báo Tự Động ---
    let currentAlertsConfig = { global_enabled: true, check_interval_seconds: 30, profiles: {} };

    async function loadAlertsConfig() {
        alertsProfilesContainer.innerHTML = `<div style="text-align: center; padding: 40px;"><div class="spinner" style="margin: 0 auto 10px;"></div> Đang tải cấu hình cảnh báo...</div>`;
        try {
            // 1. Tải danh sách profile thực tế từ backend để đồng bộ
            let actualProfiles = ["default"];
            try {
                const pRes = await fetch(`${API_URL}/api/hermes/profiles`);
                if (pRes.ok) {
                    const pData = await pRes.json();
                    if (Array.isArray(pData)) {
                        actualProfiles = pData.map(p => p.name || p);
                    } else if (pData && pData.profiles) {
                        actualProfiles = pData.profiles;
                    }
                }
            } catch (err) {
                console.warn("Không thể lấy danh sách profile thực tế, fallback về ['default']:", err);
            }
            
            // 2. Tải cấu hình alerts hiện tại
            const response = await fetch(`${API_URL}/api/alerts/config`);
            currentAlertsConfig = await response.json();
            
            // Đồng bộ hóa các profile mới nếu config chưa có
            if (!currentAlertsConfig.profiles) {
                currentAlertsConfig.profiles = {};
            }
            
            // Đảm bảo tất cả profile thực tế đều có mặt trong config
            actualProfiles.forEach(p => {
                if (!currentAlertsConfig.profiles[p]) {
                    currentAlertsConfig.profiles[p] = {
                        enabled: false,
                        bot_type: "telegram",
                        telegram_token: "",
                        telegram_chat_id: "",
                        zalo_url: "http://localhost:3000/send",
                        zalo_params: '{"message": "{message}"}',
                        last_status: "unknown"
                    };
                }
            });
            
            // Cập nhật trạng thái switch toàn cục và interval
            alertsGlobalEnabled.checked = currentAlertsConfig.global_enabled;
            alertsCheckInterval.value = currentAlertsConfig.check_interval_seconds;
            
            // Render danh sách profiles cấu hình
            renderAlertsProfiles();
        } catch (error) {
            console.error("Lỗi khi tải cấu hình alerts:", error);
            showToast("Lỗi tải cấu hình cảnh báo: " + error.message, "error");
            alertsProfilesContainer.innerHTML = `<div style="text-align: center; color: var(--danger); padding: 20px;">Lỗi tải dữ liệu cấu hình cảnh báo.</div>`;
        }
    }

    function renderAlertsProfiles() {
        const profiles = currentAlertsConfig.profiles;
        const keys = Object.keys(profiles);
        
        if (keys.length === 0) {
            alertsProfilesContainer.innerHTML = `<div class="card" style="padding: 30px; text-align: center; color: var(--text-muted);">Không phát hiện profile Hermes nào để cấu hình. Hãy tạo một profile trước.</div>`;
            return;
        }
        
        alertsProfilesContainer.innerHTML = keys.map(pName => {
            const cfg = profiles[pName];
            const isTelegram = cfg.bot_type === "telegram";
            const isZalo = cfg.bot_type === "zalo";
            const isEnabled = cfg.enabled;
            
            return `
            <div class="card alerts-profile-card" data-profile="${escapeHtml(pName)}" style="padding: 24px; border-radius: var(--border-radius); background: var(--bg-card); border: 1px solid var(--border); box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: border-color 0.3s; margin-bottom: 10px;">
                <!-- Header Profile Card -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 15px; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <h3 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-robot text-primary"></i> Profile: ${escapeHtml(pName)}
                        </h3>
                        <span class="status-badge status-indicator-badge-${escapeHtml(pName)}" style="background: rgba(156,163,175,0.15); color: var(--text-muted); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500;">Đang kiểm tra...</span>
                    </div>
                    
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 0.9rem; color: var(--text-muted);">Kích hoạt cảnh báo:</span>
                        <label class="switch-toggle" style="position: relative; display: inline-block; width: 50px; height: 26px;">
                            <input type="checkbox" class="profile-alert-toggle" data-profile="${escapeHtml(pName)}" style="opacity: 0; width: 0; height: 0; cursor: pointer;" ${isEnabled ? 'checked' : ''}>
                            <span class="slider-toggle" style="position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--border); transition: .4s; border-radius: 34px;"></span>
                        </label>
                    </div>
                </div>
                
                <!-- Config Form -->
                <div class="profile-config-form-body-${escapeHtml(pName)}" style="transition: opacity 0.3s; ${isEnabled ? '' : 'opacity: 0.5; pointer-events: none;'}">
                    <!-- Chọn loại Bot -->
                    <div class="form-group" style="margin-bottom: 15px;">
                        <label style="display: block; font-weight: 600; color: var(--text-main); margin-bottom: 8px; font-size: 0.95rem;">Loại Bot Cảnh Báo:</label>
                        <div style="display: flex; gap: 20px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--text-main); font-weight: 500;">
                                <input type="radio" name="bot_type_${escapeHtml(pName)}" value="telegram" class="radio-bot-type" data-profile="${escapeHtml(pName)}" ${isTelegram ? 'checked' : ''} style="transform: scale(1.1);"> 
                                <i class="fa-brands fa-telegram" style="color: #3b82f6; font-size: 1.1rem;"></i> Telegram Bot
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: var(--text-main); font-weight: 500;">
                                <input type="radio" name="bot_type_${escapeHtml(pName)}" value="zalo" class="radio-bot-type" data-profile="${escapeHtml(pName)}" ${isZalo ? 'checked' : ''} style="transform: scale(1.1);"> 
                                <i class="fa-solid fa-message" style="color: #0068ff; font-size: 1rem;"></i> Zalo Webhook
                            </label>
                        </div>
                    </div>
                    
                    <!-- Inputs Telegram -->
                    <div class="telegram-fields-${escapeHtml(pName)}" style="display: ${isTelegram ? 'grid' : 'none'}; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                        <div class="form-group">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 5px;">Telegram Bot Token:</label>
                            <input type="password" class="form-control tg-token-input" data-profile="${escapeHtml(pName)}" value="${escapeHtml(cfg.telegram_token || '')}" placeholder="Nhập Token của Bot Telegram" style="width: 100%; padding: 8px 12px; background: var(--bg-body); border: 1px solid var(--border); color: var(--text-main); border-radius: 6px;">
                        </div>
                        <div class="form-group">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 5px;">Chat ID Telegram:</label>
                            <input type="text" class="form-control tg-chat-input" data-profile="${escapeHtml(pName)}" value="${escapeHtml(cfg.telegram_chat_id || '')}" placeholder="Nhập ID Chat hoặc ID Group" style="width: 100%; padding: 8px 12px; background: var(--bg-body); border: 1px solid var(--border); color: var(--text-main); border-radius: 6px;">
                        </div>
                    </div>
                    
                    <!-- Inputs Zalo -->
                    <div class="zalo-fields-${escapeHtml(pName)}" style="display: ${isZalo ? 'grid' : 'none'}; grid-template-columns: 1.2fr 0.8fr; gap: 15px; margin-bottom: 15px;">
                        <div class="form-group">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 5px;">Zalo Webhook URL:</label>
                            <input type="text" class="form-control zalo-url-input" data-profile="${escapeHtml(pName)}" value="${escapeHtml(cfg.zalo_url || 'http://localhost:3000/send')}" placeholder="Ví dụ: http://localhost:3000/send" style="width: 100%; padding: 8px 12px; background: var(--bg-body); border: 1px solid var(--border); color: var(--text-main); border-radius: 6px;">
                        </div>
                        <div class="form-group">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 5px;">JSON Payload Template:</label>
                            <input type="text" class="form-control zalo-params-input" data-profile="${escapeHtml(pName)}" value="${escapeHtml(cfg.zalo_params || '{"message": "{message}"}')}" placeholder='{"message": "{message}"}' style="width: 100%; padding: 8px 12px; background: var(--bg-body); border: 1px solid var(--border); color: var(--text-main); border-radius: 6px; font-family: monospace;">
                        </div>
                    </div>
                    
                    <!-- Test Button -->
                    <div style="display: flex; justify-content: flex-start; margin-top: 10px;">
                        <button class="btn btn-test-bot" data-profile="${escapeHtml(pName)}" style="background: rgba(59, 130, 246, 0.1); color: var(--primary); border: 1px solid rgba(59,130,246,0.3); padding: 8px 15px; border-radius: var(--border-radius); font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 0.85rem; transition: all 0.2s;">
                            <i class="fa-solid fa-paper-plane"></i> Gửi thử tin nhắn (Test Bot)
                        </button>
                    </div>
                </div>
            </div>
            `;
        }).join("");
        
        // Setup events
        setupAlertsEvents();
        fetchAlertsProfilesStatus();
    }

    function setupAlertsEvents() {
        // Toggle kích hoạt
        document.querySelectorAll(".profile-alert-toggle").forEach(toggle => {
            toggle.addEventListener("change", (e) => {
                const pName = e.target.getAttribute("data-profile");
                const formBody = document.querySelector(`.profile-config-form-body-${pName}`);
                
                if (e.target.checked) {
                    formBody.style.opacity = "1";
                    formBody.style.pointerEvents = "auto";
                } else {
                    formBody.style.opacity = "0.5";
                    formBody.style.pointerEvents = "none";
                }
                currentAlertsConfig.profiles[pName].enabled = e.target.checked;
            });
        });

        // Radio bot type
        document.querySelectorAll(".radio-bot-type").forEach(radio => {
            radio.addEventListener("change", (e) => {
                const pName = e.target.getAttribute("data-profile");
                const botType = e.target.value;
                
                const tgFields = document.querySelector(`.telegram-fields-${pName}`);
                const zaloFields = document.querySelector(`.zalo-fields-${pName}`);
                
                if (botType === "telegram") {
                    tgFields.style.display = "grid";
                    zaloFields.style.display = "none";
                } else {
                    tgFields.style.display = "none";
                    zaloFields.style.display = "grid";
                }
                currentAlertsConfig.profiles[pName].bot_type = botType;
            });
        });

        // Test Bot
        document.querySelectorAll(".btn-test-bot").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const pName = btn.getAttribute("data-profile");
                const card = btn.closest(".alerts-profile-card");
                const p_cfg = currentAlertsConfig.profiles[pName];
                
                p_cfg.telegram_token = card.querySelector(".tg-token-input").value.trim();
                p_cfg.telegram_chat_id = card.querySelector(".tg-chat-input").value.trim();
                p_cfg.zalo_url = card.querySelector(".zalo-url-input").value.trim();
                p_cfg.zalo_params = card.querySelector(".zalo-params-input").value.trim();
                
                btn.disabled = true;
                btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi...`;
                
                try {
                    await fetch(`${API_URL}/api/alerts/config`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(currentAlertsConfig)
                    });
                    
                    const res = await fetch(`${API_URL}/api/alerts/test`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ profile_name: pName })
                    });
                    const data = await res.json();
                    
                    if (res.ok && data.success) {
                        showToast(`Gửi tin nhắn kiểm tra cho '${pName}' thành công!`, "success");
                    } else {
                        showToast(`Lỗi test bot: ${data.detail || "Không rõ nguyên nhân"}`, "error");
                    }
                } catch (error) {
                    console.error("Lỗi test bot:", error);
                    showToast("Lỗi test bot: " + error.message, "error");
                } finally {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Gửi thử tin nhắn (Test Bot)`;
                }
            });
        });
    }

    async function fetchAlertsProfilesStatus() {
        try {
            const pRes = await fetch(`${API_URL}/api/hermes/profiles`);
            const pData = await pRes.json();
            const actualProfiles = pData.profiles_status || {};
            
            Object.keys(currentAlertsConfig.profiles).forEach(pName => {
                const statusBadge = document.querySelector(`.status-indicator-badge-${pName}`);
                if (statusBadge) {
                    const status = actualProfiles[pName] || "offline";
                    if (status === "online") {
                        statusBadge.innerText = "ONLINE";
                        statusBadge.style.background = "rgba(16, 185, 129, 0.15)";
                        statusBadge.style.color = "#10b981";
                    } else {
                        statusBadge.innerText = "OFFLINE";
                        statusBadge.style.background = "rgba(239, 68, 68, 0.15)";
                        statusBadge.style.color = "#ef4444";
                    }
                }
            });
        } catch (e) {
            console.warn("Lỗi đồng bộ trạng thái:", e);
        }
    }

    btnSaveAlerts.addEventListener("click", async () => {
        btnSaveAlerts.disabled = true;
        btnSaveAlerts.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...`;
        
        currentAlertsConfig.global_enabled = alertsGlobalEnabled.checked;
        currentAlertsConfig.check_interval_seconds = parseInt(alertsCheckInterval.value);
        
        const cards = document.querySelectorAll(".alerts-profile-card");
        cards.forEach(card => {
            const pName = card.getAttribute("data-profile");
            const p_cfg = currentAlertsConfig.profiles[pName];
            
            p_cfg.telegram_token = card.querySelector(".tg-token-input").value.trim();
            p_cfg.telegram_chat_id = card.querySelector(".tg-chat-input").value.trim();
            p_cfg.zalo_url = card.querySelector(".zalo-url-input").value.trim();
            p_cfg.zalo_params = card.querySelector(".zalo-params-input").value.trim();
        });
        
        try {
            const response = await fetch(`${API_URL}/api/alerts/config`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(currentAlertsConfig)
            });
            const data = await response.json();
            
            if (response.ok && data.success) {
                showToast("Đã lưu cấu hình cảnh báo thành công!", "success");
                loadAlertsConfig();
            } else {
                showToast("Lỗi lưu cấu hình: " + (data.detail || "Không rõ nguyên nhân"), "error");
            }
        } catch (error) {
            console.error("Lỗi lưu cấu hình alerts:", error);
            showToast("Lỗi lưu cấu hình: " + error.message, "error");
        } finally {
            btnSaveAlerts.disabled = false;
            btnSaveAlerts.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Lưu cấu hình cảnh báo`;
        }
    });

    // Helper: Escape HTML strings to prevent XSS
    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
