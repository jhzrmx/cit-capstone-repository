const urlParams = new URLSearchParams(window.location.search);
const searchParameter = urlParams.get("search");

const searchState = {
	pollingInterval: null,
	queryId: null,
	lastQuery: null
};

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

function showSummaryLoading() {
	const container = document.getElementById("aiSummaryContainer");
	const loading = document.getElementById("summaryLoading");
	const content = document.getElementById("summaryContent");
	const error = document.getElementById("summaryError");
	
	if (container) container.style.display = "block";
	if (loading) loading.style.display = "block";
	if (content) content.style.display = "none";
	if (error) error.style.display = "none";
}

function showSummaryContent(summary) {
	const loading = document.getElementById("summaryLoading");
	const content = document.getElementById("summaryContent");
	const error = document.getElementById("summaryError");
	const summaryText = document.getElementById("summaryText");
	const referenceList = document.getElementById("referenceList");
	
	if (loading) loading.style.display = "none";
	if (content) content.style.display = "block";
	if (error) error.style.display = "none";
	
	if (summaryText) {
		summaryText.textContent = summary.summary_text;
	}
	
	if (referenceList) {
		referenceList.innerHTML = "";
		
		summary.references.forEach(ref => {
			const li = document.createElement("li");
			li.classList.add("mb-2");
			li.innerHTML = `
				• <a href="/capstone?id=${ref.capstone_id}" target="_blank" class="text-decoration-none">${ref.title}</a><br>
				<small class="text-muted">${ref.authors} (${ref.year})</small>
			`;
			referenceList.appendChild(li);
		});
	}
	
	if (summaryText && summary.summary_text) {
		let linkedText = summary.summary_text;
		
		const indexToId = {};
		summary.references.forEach(ref => {
			indexToId[ref.index] = ref.capstone_id;
		});
		
		linkedText = linkedText.replace(/\[(\d+)\]/g, (match, index) => {
			const capstoneId = indexToId[parseInt(index)];
			if (capstoneId) {
				return `<a href="/capstone?id=${capstoneId}" target="_blank" class="text-decoration-none">[${index}]</a>`;
			}
			return match;
		});
		
		summaryText.innerHTML = linkedText;
	}
}

function showSummaryError() {
	const loading = document.getElementById("summaryLoading");
	const content = document.getElementById("summaryContent");
	const error = document.getElementById("summaryError");
	
	if (loading) loading.style.display = "none";
	if (content) content.style.display = "none";
	if (error) error.style.display = "block";
}

function hideSummary() {
	const container = document.getElementById("aiSummaryContainer");
	if (container) {
		container.style.display = "none";
	}
	stopPolling();
}

function stopPolling() {
	if (searchState.pollingInterval) {
		clearInterval(searchState.pollingInterval);
		searchState.pollingInterval = null;
	}
	searchState.queryId = null;
}

async function pollSummary(queryId) {
	try {
		const res = await fetch(`/api/capstones/summary/${queryId}`);
		
		if (res.ok) {
			const summary = await res.json();
			
			if (summary) {
				showSummaryContent(summary);
				stopPolling();
			}
		} else {
			showSummaryError();
			stopPolling();
		}
	} catch (error) {
		console.error("Polling error:", error);
		showSummaryError();
		stopPolling();
	}
}

function startPolling(queryId) {
	stopPolling();
	searchState.queryId = queryId;
	
	pollSummary(queryId);
	searchState.pollingInterval = setInterval(() => pollSummary(queryId), 2000);
	
	setTimeout(() => {
		if (searchState.queryId === queryId) {
			stopPolling();
			showSummaryError();
		}
	}, 30000);
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
	
	const isNewSearch = (searchQuery !== searchState.lastQuery);
	
	if (isNewSearch) {
		hideSummary();
		searchState.lastQuery = searchQuery;
		searchState.queryId = null;
	}
	
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
	
	if (isNewSearch && data.query_id) {
		showSummaryLoading();
		startPolling(data.query_id);
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

