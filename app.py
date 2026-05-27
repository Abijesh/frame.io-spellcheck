import streamlit as st
import os
import time
import json
import requests
from google import genai
from google.genai import types

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Little Unusual | AI Copyeditor", 
    page_icon="🎬", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- LITTLE UNUSUAL BRAND CSS ---
brand_css = """
<style>
    /* Import Premium Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500&display=swap');

    /* Force Warm Brand Background & Hide Streamlit UI */
    .stApp {
        background-color: #FAF6ED !important; /* Warm Sand/Cream */
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Typography Overrides */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #121212 !important;
        letter-spacing: -0.02em;
    }
    
    p, span, label, div {
        font-family: 'Inter', sans-serif !important;
        color: #333333 !important;
    }

    /* Custom Input Box styling */
    .stTextInput > div > div > input {
        background-color: #FFFFFF !important;
        border: 1px solid #EAE3D5 !important;
        border-radius: 8px !important;
        color: #121212 !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Match the 'Book a Call' Pill Button */
    .stButton>button {
        background-color: #F8C33D !important; /* Golden Accent */
        color: #121212 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 50px !important; /* Pill shape */
        padding: 10px 24px !important;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 15px rgba(248, 195, 61, 0.4);
        color: #121212 !important;
        border: none !important;
    }

    /* Style the Status Expander to match */
    .stStatusWidget {
        background-color: #FFFFFF !important;
        border: 1px solid #EAE3D5 !important;
        border-radius: 12px !important;
    }
</style>
"""
st.markdown(brand_css, unsafe_allow_html=True)

# ==========================================
# 2. HERO SECTION
# ==========================================
# IMPORTANT: Put your logo image file in the same folder as this script 
# and change "logo.png" to your actual file name (e.g., "lu_logo.svg")
try:
    st.image("logo.png", width=120) 
except:
    pass # If no logo is found, it just skips it without throwing an error

st.title("AI Copyeditor")
st.markdown("**Automatically scan Frame.io timelines for typos and grammar errors.**")
st.divider()

# ==========================================
# 3. SECRETS MANAGEMENT
# ==========================================
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
    if "f.io" in url:
        try:
            response = requests.head(url, allow_redirects=True)
            url = response.url
        except Exception:
            return None

    parts = url.replace("?", "/").split("/")
    for part in reversed(parts):
        if len(part) == 36 and part.count("-") == 4:
            return part
            
    return None

# ==========================================
# 4. UI FRONTEND
# ==========================================
video_link = st.text_input("Target Video", placeholder="Paste Frame.io Internal Link here...", label_visibility="collapsed")

st.write("") 

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    start_scan = st.button("Scan Video Now", type="primary", use_container_width=True)

if start_scan:
    if not video_link:
        st.warning("Please paste a valid Frame.io link first.")
        st.stop()

    file_id = extract_file_id(video_link)
    if not file_id:
        st.error("❌ Could not extract a valid video ID from that link.")
        st.stop()

    # ==========================================
    # 5. PROCESSING PIPELINE
    # ==========================================
    with st.status("Connecting to Little Unusual Backend...", expanded=True) as status:
        try:
            status.update(label="Sending video ID to server...")
            
            # YOUR MAKE.COM WEBHOOK URL
            MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/s55i8p8t8cy3gfqk40jpn45f2oizx6u7"
            
            payload = {
                "file_id": file_id,
                "action": "extract_video"
            }
            
            response = requests.post(MAKE_WEBHOOK_URL, json=payload)

            if response.status_code == 200:
                status.update(label="Signal sent successfully.", state="complete")
                st.success("✅ Frame.io link caught!")
                st.write("The AI is now processing the video. Check Frame.io shortly for the markers!")
                st.balloons() 
            else:
                st.error(f"🚨 Connection Error: {response.text}")
                status.update(label="❌ Failed to reach the server", state="error")
                
            st.stop()

        except Exception as e:
            status.update(label="❌ An error occurred during processing.", state="error")
            st.error(str(e))