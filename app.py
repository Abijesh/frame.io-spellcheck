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
    with st.status("Connecting to Make.com Backend...", expanded=True) as status:
        try:
            status.update(label="🚀 Sending video ID to Make.com...")
            
            # PASTE YOUR MAKE.COM WEBHOOK URL HERE
            MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/79v6ja5tbksfrufghjncc18jgcvrlpw6"
            
            payload = {
                "file_id": file_id,
                "action": "extract_video"
            }
            
            # Send the request to Make
            response = requests.post(MAKE_WEBHOOK_URL, json=payload)

            if response.status_code == 200:
                st.success("✅ Successfully connected to the Webhook!")
                st.write("Make.com received the signal. Check your Make dashboard to see the data!")
                status.update(label="Signal sent.", state="complete")
            else:
                st.error(f"🚨 Webhook Error: {response.text}")
                status.update(label="❌ Failed to reach Make.com", state="error")
                
            st.stop()

        except Exception as e:
            status.update(label="❌ An error occurred during processing.", state="error")
            st.error(str(e))