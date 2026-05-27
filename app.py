import streamlit as st
import os
import time
import json
import requests
from google import genai
from google.genai import types

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Little Unusual Spellcheck", page_icon="🎬", layout="centered")
st.title("🎬 Little Unusual AI Spellchecker")
st.markdown("Paste a Frame.io review link below to automatically scan the video for spelling and grammar errors. The AI will drop markers directly onto the timeline.")

# --- SECRETS MANAGEMENT ---
# The cloud server will pull your keys from a secure vault so they aren't exposed to the team.
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    FRAMEIO_TOKEN = st.secrets["FRAMEIO_TOKEN"]
except KeyError:
    st.error("⚠️ App secrets are not configured. Please add keys in the Streamlit Cloud settings.")
    st.stop()

ai_client = genai.Client(api_key=GEMINI_API_KEY)
FIO_HEADERS = {
    "Authorization": f"Bearer {FRAMEIO_TOKEN}",
    "x-frameio-legacy-token-auth": "true",
    "Content-Type": "application/json"
}

def extract_file_id(url):
    """Extracts the core File ID from ANY Frame.io link."""
    # If someone pastes a short link (f.io), unroll it first
    if "f.io" in url:
        try:
            response = requests.head(url, allow_redirects=True)
            url = response.url
        except Exception:
            return None

    # Chop the URL into pieces and hunt for the 36-character ID
    parts = url.replace("?", "/").split("/")
    for part in reversed(parts):
        if len(part) == 36 and part.count("-") == 4:
            return part
            
    return None

# --- UI FRONTEND ---
video_link = st.text_input("Frame.io Video Link:", placeholder="https://next.frame.io/project/.../view/48055c11...")

if st.button("🚀 Scan Video Now", type="primary"):
    if not video_link:
        st.warning("Please paste a valid Frame.io link first.")
        st.stop()

    file_id = extract_file_id(video_link)
    if not file_id:
        st.error("❌ Could not extract a valid video ID from that link.")
        st.stop()

    # --- PROCESSING PIPELINE ---
    with st.status("Initializing AI Pipeline...", expanded=True) as status:
        try:
            status.update(label="🔍 Fetching video data from Frame.io (V2 API)...")
            
            # FIX 1: Downgrade to V2 Asset Endpoint
            file_url = f"https://api.frame.io/v2/assets/{file_id}"
            response = requests.get(file_url, headers=FIO_HEADERS)

            if response.status_code != 200:
                st.error(f"🚨 Frame.io API Error [{response.status_code}]: {response.text}")
                st.warning(f"🔍 Debug Info - The ID we extracted was: {file_id}")
                status.update(label="❌ Failed to access Frame.io", state="error")
                st.stop()

            file_data = response.json()
            
            # FIX 2: V2 Proxy Extraction Format
            downloads = file_data.get('downloads', {})
            proxy_url = downloads.get('h264_1080') or downloads.get('h264_720') or file_data.get('cover_asset', {}).get('proxy_url')

            if not proxy_url:
                status.update(label="❌ No playable video stream found.", state="error")
                st.stop()

            status.update(label="📥 Downloading video to the secure cloud...")
            local_filename = f"temp_{file_id}.mp4"
            with requests.get(proxy_url, stream=True) as r:
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            status.update(label="🎬 Uploading to Gemini Free Tier...")
            video_file = ai_client.files.upload(file=local_filename)

            status.update(label="⏳ AI is watching the video (this takes about 30-60 seconds)...")
            while video_file.state.name == "PROCESSING":
                time.sleep(5)
                video_file = ai_client.files.get(name=video_file.name)

            status.update(label="👁️ Finding spelling and typography mistakes...")
            prompt = """
            Analyze this video frame-by-frame. Look at text titles, captions, and lower-thirds.
            Find any misspelled words. Output a JSON array where each object has:
            "timestamp_ms" (the time in milliseconds), "typo", and "correction".
            """

            ai_response = ai_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[video_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[dict],
                ),
            )

            typos = json.loads(ai_response.text)
            st.write(f"**Found {len(typos)} potential issues.**")

            status.update(label="✍️ Dropping correction markers on the timeline...")
            success_count = 0
            for item in typos:
                ms = item.get("timestamp_ms", 0)
                target_frame = max(1, int((ms / 1000) * 24))
                
                comment_text = f"🤖 AI Spellcheck: Found '{item.get('typo')}'. Did you mean '{item.get('correction')}'?"
                
                # FIX 3: Downgrade Comment Endpoint to V2 & use 'text' payload
                comment_url = f"https://api.frame.io/v2/assets/{file_id}/comments"
                payload = {"text": comment_text, "timestamp": target_frame}
                
                c_res = requests.post(comment_url, json=payload, headers=FIO_HEADERS)
                if c_res.status_code in [200, 201]:
                    success_count += 1

            # Cleanup Cloud Storage
            os.remove(local_filename)
            ai_client.files.delete(name=video_file.name)

            status.update(label=f"🎉 Done! Placed {success_count} comments on the timeline.", state="complete")
            st.balloons()

        except Exception as e:
            status.update(label="❌ An error occurred during processing.", state="error")
            st.error(str(e))