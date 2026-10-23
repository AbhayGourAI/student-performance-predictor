// Set this to your deployed Render URL, with no trailing slash.
const API_BASE_URL = "https://student-performance-predictor-api-ws5h.onrender.com";

const form = document.querySelector("#predict-form");
const button = document.querySelector("#submit-button");
const message = document.querySelector("#message");

function apiUrl(path) {
  return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
}

function setMessage(text, isError = true) {
  message.textContent = text;
  message.style.color = isError ? "#b42318" : "#147d64";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (API_BASE_URL.includes("YOUR-RENDER-SERVICE")) {
    setMessage("Deployment setup needed: replace API_BASE_URL in script.js with your Render URL.");
    return;
  }

  const payload = Object.fromEntries(new FormData(form).entries());
  for (const key of Object.keys(payload)) payload[key] = Number(payload[key]);

  button.disabled = true;
  button.textContent = "Predicting…";
  setMessage("");

  try {
    const response = await fetch(apiUrl("/api/predict"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The prediction request failed.");

    document.querySelector("#score-value").textContent = data.predicted_score.toFixed(1);
    document.querySelector("#score-meter").style.width = `${data.predicted_score}%`;
    document.querySelector("#interpretation").textContent = data.interpretation;
    document.querySelector("#notice").textContent = data.notice;
    setMessage("Prediction complete.", false);
    await loadHistory();
  } catch (error) {
    setMessage(`${error.message} Check that the Render backend is deployed and reachable.`);
  } finally {
    button.disabled = false;
    button.innerHTML = 'Predict performance <span aria-hidden="true">→</span>';
  }
});

async function loadHistory() {
  const body = document.querySelector("#history-body");
  if (API_BASE_URL.includes("YOUR-RENDER-SERVICE")) {
    body.innerHTML = '<tr><td colspan="5">Set API_BASE_URL in script.js to enable history.</td></tr>';
    return;
  }
  try {
    const response = await fetch(apiUrl("/api/history"));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load history.");
    if (!data.history.length) {
      body.innerHTML = '<tr><td colspan="5">No predictions yet. Submit the form to create one.</td></tr>';
      return;
    }
    body.replaceChildren();
    for (const item of data.history) {
      const tr = document.createElement("tr");
      const values = [
        new Date(item.created_at).toLocaleString(),
        item.study_hours,
        `${item.attendance}%`,
        item.previous_score,
        `${Number(item.predicted_score).toFixed(1)} / 100`
      ];
      for (const value of values) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.appendChild(td);
      }
      body.appendChild(tr);
    }
  } catch (error) {
    body.innerHTML = "";
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.textContent = `Could not load history: ${error.message}`;
    tr.appendChild(td);
    body.appendChild(tr);
  }
}

document.querySelector("#refresh-history").addEventListener("click", loadHistory);
loadHistory();
