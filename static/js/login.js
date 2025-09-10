const form = document.getElementById("loginForm");
const alertBox = document.getElementById("alertBox");

form.addEventListener("submit", async (e) => {
	e.preventDefault();
	const formData = new FormData(form);
	const btn = e.target.querySelector("button[type=submit]");
  btn.disabled = true;
  btn.textContent = "Logging in...";
	try {
		const res = await fetch("/api/login", {
			method: "POST",
			headers: {
			"Content-Type": "application/x-www-form-urlencoded",
			},
			body: new URLSearchParams({
				username: formData.get("username"),
				password: formData.get("password"),
			}),
		});
		if (!res.ok) {
			throw new Error("Invalid username or password");
		}
		const data = await res.json();
		btn.disabled = false;
    btn.textContent = "✅ Login successful!";
		setTimeout(() => {
			window.location.href = "/manage-capstones";
		}, 500);
	} catch (err) {
		alertBox.innerHTML = `<div class="alert alert-danger">❌ ${err.message}</div>`;
	}
});
