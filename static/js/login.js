const form = document.getElementById("loginForm");
const alertBox = document.getElementById("alertBox");

form.addEventListener("submit", async (e) => {
	e.preventDefault();
	const formData = new FormData(form);
	try {
		const res = await fetch("/api/login", {
			method: "POST",
			body: formData
		});
		if (!res.ok) {
			throw new Error("Invalid email or password");
		}
		const data = await res.json();
		localStorage.setItem("token", data.access_token);
		alertBox.innerHTML = `<div class="alert alert-success">✅ Login successful! Redirecting...</div>`;
		setTimeout(() => {
			window.location.href = "/manage";
		}, 1000);
	} catch (err) {
		alertBox.innerHTML = `<div class="alert alert-danger">❌ ${err.message}</div>`;
	}
});
