let debounceTimer;
const tableBody = document.getElementById("capstoneTable");
const csvfileInput = document.getElementById("csvFile");
const uploadResultDiv = document.getElementById("upload-result");

function importModal() {
    new bootstrap.Modal(document.getElementById("importModal")).show();
    uploadResultDiv.innerHTML = "";
}

document.getElementById("uploadBtn").addEventListener("click", () => {
    csvfileInput.click();
});

csvfileInput.addEventListener("change", async () => {
    if (!csvfileInput.files.length) return;
    const formData = new FormData();
    formData.append("file", csvfileInput.files[0]);
    uploadResultDiv.innerHTML = `<div class="text-info">⏳ Uploading...</div>`;
    try {
        const res = await fetch("/capstones/import-csv", {
            method: "POST",
            body: formData,
        });
        if (!res.ok) {
            const errorData = await res.json();
            alert("Upload failed: " + errorData.detail);
            throw new Error(errorData.detail || "Upload failed");
        }
        
        const data = await res.json();
        let html = `
            <div class="alert alert-success">✅ Inserted: ${data.inserted.length}</div>
            <div class="alert alert-warning">⚠️ Skipped: ${data.skipped.length}</div>
        `;
        if (data.skipped.length > 0) {
            html += `<ul class="list-group text-start">`;
            data.skipped.forEach((s) => {
                html += `<li class="list-group-item">${s.title || "(No Title)"} – ${s.reason}</li>`;
            });
            html += `</ul>`;
        }
        uploadResultDiv.innerHTML = html;
        loadCapstones();
    } catch (err) {
        uploadResultDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${err.message}</div>`;
    } finally {
        csvfileInput.value = ""; 
    }
});

function debounce(callback, delay=500) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(callback, delay);
}

function addCapModal() {
    new bootstrap.Modal(document.getElementById("addModal")).show();
}

document.getElementById("addCapstone").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Adding...";
    const res = await fetch("/capstones", {
        method: "POST",
        body: formData
    });
    if (res.ok) {
        form.reset();
        bootstrap.Modal.getInstance(document.getElementById("addModal")).hide();
        loadCapstones();
    } else {
        alert("Failed to add capstone!");
    }
    btn.disabled = false;
    btn.textContent = "Add Capstone";
});

async function loadCapstones(page=1,currentSearch="") {
    const pagination = document.getElementById("pagination");
    pagination.innerHTML = "";
    
    const res = await fetch(`/capstones?page=${page}&per_page=10&search=${encodeURIComponent(currentSearch)}`);
    const data = await res.json();
    
    tableBody.innerHTML = "";
    
    if (data.results.length === 0) {
        tableBody.innerHTML = `<td colspan="4">No results found<td>`;
        return;
    }
    data.results.forEach(c => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${c.title}</td>
            <td>${c.authors}</td>
            <td>${c.year}</td>
            <td>
            ${c.pdf_file ? `<a href="/uploads/${c.pdf_file}" target="_blank">View PDF</a><br/>` : ""}
            ${c.external_link ? `<a href="${c.external_link}" target="_blank">Link</a>` : ""}
            </td>
            <td>
            <button class="btn btn-warning btn-sm mb-1" onclick="openEdit(${c.id})" title="Edit Capstone">
                <img src="/static/icons/pencil.svg">
            </button>
            <button class="btn btn-danger btn-sm mb-1" onclick="deleteCapstone(${c.id})" title="Delete Capstone">
                <img src="/static/icons/trash-can.svg">
            </button>
            </td>
        `;
        tableBody.appendChild(row);
        pagination.innerHTML = "";
        const totalPages = Math.ceil(data.total / data.per_page);
        for (let i = 1; i <= totalPages; i++) {
            pagination.innerHTML += `
            <li class="page-item ${i === data.page ? "active" : ""}">
                <button class="page-link" onclick="loadCapstones(${i},${encodeURIComponent(currentSearch)})">${i}</button>
            </li>`;
        }
    });
}

function doSearch() {
    const currentSearch = document.getElementById("searchBox").value;
    loadCapstones(1, currentSearch)
}

async function openEdit(id) {
    const res = await fetch(`/capstones/${id}`);
    const c = await res.json();
    document.getElementById("editId").value = c.id;
    document.getElementById("editTitle").value = c.title;
    document.getElementById("editAbstract").value = c.abstract;
    document.getElementById("editAuthors").value = c.authors;
    document.getElementById("editYear").value = c.year;
    document.getElementById("editLink").value = c.external_link || "";
    new bootstrap.Modal(document.getElementById("editModal")).show();
}

document.getElementById("editForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("editId").value;
    const editForm = document.getElementById("editForm");
    const formData = new FormData(editForm);
    const btn = e.target.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving...";
    
    const res = await fetch(`/capstones/${id}`, {
        method: "PUT",
        body: formData
    });
    if (res.ok) {
        loadCapstones();
        bootstrap.Modal.getInstance(document.getElementById("editModal")).hide();
    } else {
        alert("Failed to update capstone!");
    }
    btn.disabled = false;
    btn.textContent = "Save Changes";
});

async function deleteCapstone(id) {
    new bootstrap.Modal(document.getElementById("deleteModal")).show();
    // if (!confirm("Are you sure you want to delete this capstone?")) return;
    async function callback(id) {
        await fetch(`/capstones/${id}`, { method: "DELETE" });
        bootstrap.Modal.getInstance(document.getElementById("deleteModal")).hide();
        loadCapstones();
    }
    document.getElementById("confirm-delete").addEventListener("click", callback.bind(null, id));
}

loadCapstones();
