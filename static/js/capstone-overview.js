const urlParams = new URLSearchParams(window.location.search);
const capstoneId = urlParams.get("id");
const content = document.getElementById("content");

if (capstoneId == null) {
    window.location.href = "/";
}

async function loadCapstoneById(id) {
	const res = await fetch(`/api/capstones/${id}`);
    const data = await res.json();

    if (!res.ok) {
        content.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <h3>An error occured</h3>
                <p>Capstone can't be found at this moment.</p>
            </div>
        `;
        return;
    }
    
    content.innerHTML = `
        <h1 class="mt-5">${data.title}</h1>
        <p class="mt-5">Author(s): ${data.authors}</p>
        <p>Year: ${data.year}</p>
        <p class="mt-5">${data.abstract}</p>
        ${data.pdf_file ? `<a href="/uploads/${data.pdf_file}" target="_blank">View PDF</a><br/>` : ""}
        ${data.external_link ? `<a href="${data.external_link}" target="_blank">Link</a>` : ""}
    `;
}

loadCapstoneById(capstoneId);

async function getUser() {
    const res = await fetch(`/api/users/current`, {
        credentials: "include",
    });
    if (!res.ok) {
        return null;
    }
    const data = await res.json();
    return data;
}
