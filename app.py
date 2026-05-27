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
    with st.status("Bypassing V4 Architecture...", expanded=True) as status:
        try:
            status.update(label="🔍 Finding your Workspace Account ID...")
            
            # 1. Fetch Account ID automatically
            acc_res = requests.get("https://api.frame.io/v4/accounts", headers=FIO_HEADERS)
            if acc_res.status_code != 200:
                st.error(f"🚨 Account Auth Error [{acc_res.status_code}]: {acc_res.text}")
                st.stop()
                
            # Parse the account ID
            acc_data = acc_res.json()
            accounts = acc_data.get("data", [acc_data]) 
            account_id = accounts[0].get("id")
            
            # 2. Fetch File from the strict V4 Endpoint
            status.update(label=f"🔍 Fetching video data from Account: {account_id}...")
            file_url = f"https://api.frame.io/v4/accounts/{account_id}/files/{file_id}"
            response = requests.get(file_url, headers=FIO_HEADERS)

            if response.status_code != 200:
                st.error(f"🚨 Frame.io API Error [{response.status_code}]: {response.text}")
                st.warning(f"🔍 Debug Info - File ID: {file_id} | Account ID: {account_id}")
                status.update(label="❌ Failed to access Frame.io", state="error")
                st.stop()

            file_data = response.json()
            
            # 3. DUMP THE JSON DATA
            st.success("✅ V4 Connection Successful! Frame.io accepted the token.")
            st.write("We just bypassed the firewall! To finish the app, we need to see exactly where Adobe hides the .mp4 link in their new V4 database layout.")
            st.json(file_data)
            
            status.update(label="Paused for mapping...", state="complete")
            st.stop()

        except Exception as e:
            status.update(label="❌ An error occurred during processing.", state="error")
            st.error(str(e))