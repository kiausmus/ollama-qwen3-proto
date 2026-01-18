async function doLogin() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();
  const err = document.getElementById("err");
  err.textContent = "";

  if (!username || !password) {
    err.textContent = "아이디/비밀번호를 입력해줘.";
    return;
  }

  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.detail || `HTTP ${res.status}`);
    }

    // ✅ 성공하면 대시보드로
    window.location.href = "/market";
  } catch (e) {
    err.textContent = "로그인 실패: " + (e.message || String(e));
  }
}

document.getElementById("btnLogin").addEventListener("click", doLogin);
document.getElementById("password").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doLogin();
});