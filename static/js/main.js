/**
 * PublicRSS Vanilla JS Helpers
 * Handles 1-click clipboard copying, toast alerts, and fast URL insertion.
 */

function copyToClipboard(text, label = "RSS URL") {
    if (!text) return;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied ${label} to clipboard!`);
    }).catch(err => {
        // Fallback for non-secure contexts
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand("copy");
            showToast(`Copied ${label} to clipboard!`);
        } catch (e) {
            console.error("Copy failed", e);
        }
        document.body.removeChild(textarea);
    });
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm shadow-2xl transition-all duration-300 transform translate-y-2 opacity-0";
    
    const icon = document.createElement("span");
    icon.className = "text-emerald-400 font-bold";
    icon.innerHTML = "✓";
    
    const text = document.createElement("span");
    text.textContent = message;

    toast.appendChild(icon);
    toast.appendChild(text);
    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    });

    // Auto-remove after 2.8s
    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => toast.remove(), 300);
    }, 2800);
}

function insertFeedUrl(url) {
    const input = document.getElementById("feed_url_input");
    if (input) {
        input.value = url;
        input.focus();
        showToast("Inserted feed URL into input!");
    }
}

function filterPresets(category) {
    const items = document.querySelectorAll(".preset-item");
    const buttons = document.querySelectorAll(".preset-btn");

    buttons.forEach(btn => {
        if (btn.dataset.cat === category) {
            btn.className = "preset-btn px-2 py-0.5 rounded-md bg-orange-500/20 text-orange-400 font-semibold border border-orange-500/30";
        } else {
            btn.className = "preset-btn px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 hover:text-white";
        }
    });

    items.forEach(item => {
        if (category === "all" || item.dataset.category === category) {
            item.style.display = "inline-flex";
        } else {
            item.style.display = "none";
        }
    });
}

