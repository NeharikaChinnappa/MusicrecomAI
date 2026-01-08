# app.py
import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "bytedance-seed/seed-1.6-flash"

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"


def call_openrouter(prompt: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "AI Song Recommender",
    }

    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system",
             "content": "You are a music recommendation engine that ONLY outputs valid JSON, nothing else."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "stream":False,
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return json.loads(text)


def get_similar_tracks(artist: str, track: str, limit: int = 5) -> list:
    """Get similar tracks from Last.fm"""
    if not LASTFM_API_KEY:
        return []
    
    try:
        resp = requests.get(
            LASTFM_URL,
            params={
                "method": "track.getSimilar",
                "artist": artist,
                "track": track,
                "api_key": LASTFM_API_KEY,
                "format": "json",
                "limit": limit
            },
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        
        tracks = []
        if "similartracks" in data and "track" in data["similartracks"]:
            for t in data["similartracks"]["track"][:limit]:
                tracks.append({
                    "title": t.get("name"),
                    "artist": t.get("artist", {}).get("name"),
                })
        return tracks
    except Exception as e:
        print(f"Last.fm error: {e}")
        return []


def get_top_tracks(country: str = "US", limit: int = 5) -> list:
    """Get trending tracks from Last.fm"""
    if not LASTFM_API_KEY:
        return []
    
    try:
        resp = requests.get(
            LASTFM_URL,
            params={
                "method": "geo.getTopTracks",
                "country": country,
                "api_key": LASTFM_API_KEY,
                "format": "json",
                "limit": limit
            },
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        
        tracks = []
        if "tracks" in data and "track" in data["tracks"]:
            for t in data["tracks"]["track"][:limit]:
                tracks.append({
                    "title": t.get("name"),
                    "artist": t.get("artist", {}).get("name") if isinstance(t.get("artist"), dict) else t.get("artist"),
                })
        return tracks
    except Exception as e:
        print(f"Last.fm error: {e}")
        return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    interests = data.get("interests", "")
    genres = data.get("genres", "")
    mood = data.get("mood", "")
    artists = data.get("artists", "")

    trending = get_top_tracks(limit=3)
    trending_str = ""
    if trending:
        trending_str = "\n\nTrending songs to consider: " + ", ".join([f"{t['title']} by {t['artist']}" for t in trending])

    prompt = f"""
User profile:
- Interests: {interests}
- Preferred genres: {genres}
- Current mood: {mood}
- Favorite artists: {artists}
{trending_str}

Recommend 10 songs that match this profile. For each song, include a Spotify search URL.

Return ONLY valid JSON, nothing else:
{{
  "recommendations": [
    {{
      "title": "Song Title",
      "artist": "Artist Name",
      "reason": "Why this song matches",
      "suggested_genre": "genre",
      "spotify_url": "https://open.spotify.com/search/{{URL encoded title and artist}}"
    }}
  ]
}}
"""

    try:
        payload = call_openrouter(prompt)
    except Exception as e:
        print("OpenRouter error:", e)
        return jsonify({"error": "Failed to generate recommendations"}), 500

    return jsonify(payload)


@app.route("/api/similar", methods=["POST"])
def find_similar():
    """Find similar tracks using Last.fm"""
    data = request.get_json()
    artist = data.get("artist", "")
    track = data.get("track", "")

    if not artist or not track:
        return jsonify({"error": "Artist and track name required"}), 400

    similar = get_similar_tracks(artist, track, limit=8)
    
    if not similar:
        return jsonify({"error": "No similar tracks found"}), 404

    # Feed similar tracks to AI for better recommendations
    similar_str = ", ".join([f"{t['title']} by {t['artist']}" for t in similar])
    prompt = f"""
Based on these similar tracks: {similar_str}

Generate 10 new song recommendations that fit this vibe.

Return ONLY valid JSON:
{{
  "recommendations": [
    {{
      "title": "Song Title",
      "artist": "Artist Name",
      "reason": "Why this fits",
      "suggested_genre": "genre",
      "spotify_url": "https://open.spotify.com/search/{{encoded}}"
    }}
  ]
}}
"""

    try:
        payload = call_openrouter(prompt)
    except Exception as e:
        print("OpenRouter error:", e)
        return jsonify({"error": "Failed to generate recommendations"}), 500

    return jsonify(payload)


if __name__ == "__main__":
    app.run(debug=True)
