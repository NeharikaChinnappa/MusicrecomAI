

async function postJSON(url, body) {
    const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    let data;
    try {
        data = await resp.json();
    } catch (e) {
        throw new Error("Server error: invalid response");
    }

    if (!resp.ok) {
        throw new Error(data.error || `Server error: ${resp.status}`);
    }

    return data;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function renderRecommendations(recommendations) {
    const resultsList = document.getElementById("recommendations-list");
    resultsList.innerHTML = "";
    
    (recommendations || []).forEach((rec) => {
        const li = document.createElement("li");
        li.innerHTML = `
            <div class="song-title">🎵 ${escapeHtml(rec.title)}</div>
            <div class="song-artist">by ${escapeHtml(rec.artist)}</div>
            <div class="song-reason">${escapeHtml(rec.reason)}</div>
            <div>
                <span class="song-genre">${escapeHtml(rec.suggested_genre)}</span>
                <a href="${escapeHtml(rec.spotify_url || '#')}" target="_blank" class="spotify-link">🎧 Find on Spotify</a>
            </div>
        `;
        resultsList.appendChild(li);
    });
}

function showLoading() {
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("error").classList.add("hidden");
    document.getElementById("recommendations-list").innerHTML = "";
}

function hideLoading() {
    document.getElementById("loading").classList.add("hidden");
}

function showError(message) {
    document.getElementById("error-message").textContent = message;
    document.getElementById("error").classList.remove("hidden");
    document.getElementById("loading").classList.add("hidden");
}


document.getElementById("recommend-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const form = e.target;
    const body = {
        interests: form.interests.value.trim(),
        genres: form.genres.value.trim(),
        mood: form.mood.value.trim(),
        artists: form.artists.value.trim(),
    };

    showLoading();

    try {
        const data = await postJSON("/api/recommend", body);
        hideLoading();
        renderRecommendations(data.recommendations);
    } catch (err) {
        console.error(err);
        showError(err.message || "Failed to get recommendations");
    }
});


document.getElementById("similar-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const form = e.target;
    const body = {
        artist: form.artist.value.trim(),
        track: form.track.value.trim(),
    };

    if (!body.artist || !body.track) {
        showError("Please enter both artist and track name");
        return;
    }

    showLoading();

    try {
        const data = await postJSON("/api/similar", body);
        hideLoading();
        renderRecommendations(data.recommendations);
    } catch (err) {
        console.error(err);
        showError(err.message || "Failed to find similar songs");
    }
});

document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
        const tabName = e.target.dataset.tab;

        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

        e.target.classList.add("active");
        document.getElementById(tabName + "-tab").classList.add("active");
    });
});
