function isLoggedIn() {
  return Boolean(localStorage.getItem("access"));
}

function requireLogin() {
  if (!isLoggedIn()) {
    window.location.href = "login.html";
  }
}

function logout() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
  clearAllState();
  window.location.href = "login.html";
}

async function tryRefreshToken() {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) return false;

  const response = await fetch(BASE_URL + ENDPOINTS.refresh, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) return false;

  const data = await response.json();
  localStorage.setItem("access", data.access);
  return true;
}

function sendRequest(endpoint, method, body) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("access");
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return fetch(BASE_URL + endpoint, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function apiRequest(endpoint, method = "GET", body = null) {
  let response = await sendRequest(endpoint, method, body);

  if (response.status === 401) {
    const refreshed = await tryRefreshToken();
    if (!refreshed) {
      logout();
      throw new Error("logged out");
    }
    response = await sendRequest(endpoint, method, body);
  }

  const data = await response.json();
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}
