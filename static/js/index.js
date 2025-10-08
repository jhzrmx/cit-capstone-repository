const urlParams = new URLSearchParams(window.location.search);
const searchParameter = urlParams.get("search");

document.getElementById("searchForm").addEventListener("submit", async (e) => {
	e.preventDefault();
	loadSearch();    
});

setTimeout(()=>{
    document.getElementById("nav-smart-search").classList.add("active");
}, 250);

function truncateText(text, maxWords=30) {
	const words = text.split(" ");
	if (words.length > maxWords) {
	return words.slice(0, maxWords).join(" ") + "...";
	}
	return text;
}

async function loadSearch(page=1) {
	const searchQuery = document.getElementById("searchInput").value;
	if (searchQuery === "") return;
	document.title = `Search results for "${searchQuery}"`;
	history.pushState(null, null, `/?search=${encodeURIComponent(searchQuery)}`);
	const resultsDiv = document.getElementById("results");
	resultsDiv.innerHTML = "Fetching...";
	const pagination = document.getElementById("pagination");
	pagination.innerHTML = "";
	
	const res = await fetch(`/api/search?page=${page}&per_page=5`, {
		method: "POST",
		headers: {"Content-Type": "application/json"},
		body: JSON.stringify({ text: searchQuery })
	});
	
	const data = await res.json();
	resultsDiv.innerHTML = "";
	if (data.results.length === 0) {
		resultsDiv.innerHTML = "No results found.";
		return;
	}
	data.results.forEach(r => {
		const div = document.createElement("div");
		div.classList.add("card", "mb-2", "p-2");
		div.innerHTML = `
			<h5><a href="/capstone?id=${r.id}">${r.title}</a></h5>
			<p>${truncateText(r.abstract)}</p>
			<small>Similarity: ${(r.similarity*100).toFixed(0)}%</small>
		`;
		resultsDiv.appendChild(div);
	});
	
	const totalPages = Math.ceil(data.total / data.per_page);
	pagination.innerHTML = "";
	
	for (let i = 1; i <= totalPages; i++) {
	pagination.innerHTML += `
		<li class="page-item ${i === data.page ? "active" : ""}">
		<button class="page-link" onclick="loadSearch(${i})">${i}</button>
		</li>`;
	}
}

if (searchParameter) {
	document.getElementById("searchInput").value = searchParameter;
	loadSearch();
}
