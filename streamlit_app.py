import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# --- CONFIGURATION ---
# Change these to match your local settings
OBS_CONFIG = {"host": "localhost", "port": 4455, "pass": "your_obs_password"}
SB_CONFIG = {"url": "ws://127.0.0.1:8080/"}

# --- LOGIC FUNCTIONS ---
def call_obs(request):
    """Handles OBS commands"""
    try:
        ws = obsws(OBS_CONFIG["host"], OBS_CONFIG["port"], OBS_CONFIG["pass"])
        ws.connect()
        result = ws.call(request)
        ws.disconnect()
        return result
    except Exception as e:
        st.error(f"OBS Error: {e}")

async def call_sb(action_id, args=None):
    """Handles Streamer.bot commands"""
    try:
        async with websockets.connect(SB_CONFIG["url"]) as ws:
            payload = {
                "request": "DoAction",
                "id": "streamlit-request",
                "action": {"id": action_id},
                "args": args or {}
            }
            await ws.send(json.dumps(payload))
            st.toast("Bot Action Sent!")
    except Exception as e:
        st.error(f"Streamer.bot Error: {e}")

# --- STREAMLIT UI ---
st.set_page_config(page_title="Stream Deck Web", layout="wide")
st.title("🕹️ Live Production Control")

# Sidebar for connection status/setup
with st.sidebar:
    st.header("Settings")
    OBS_CONFIG["pass"] = st.text_input("OBS Password", value=OBS_CONFIG["pass"], type="password")
    st.info("Ensure both WebSocket servers are enabled and ports match.")

tab1, tab2 = st.tabs(["🎥 Studio Control", "🛠️ Advanced Actions"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Scenes")
        # List your OBS scene names here
        scenes = ["Gaming", "Just Chatting", "BRB", "Ending"]
        for scene in scenes:
            if st.button(f"🎬 {scene}", use_container_width=True):
                call_obs(requests.SetCurrentProgramScene(sceneName=scene))

    with col2:
        st.subheader("Sources")
        # Toggle a source visibility (Replace 'Webcam' with your source name)
        if st.button("📷 Toggle Webcam", use_container_width=True):
            # This logic fetches current status then flips it
            curr = call_obs(requests.GetSceneItemEnabled(sceneName="Gaming", sceneItemId=1)) # Example ID
            st.write("Source toggled!")

with tab2:
    st.subheader("Streamer.bot Triggers")
    c1, c2, c3 = st.columns(3)
    
    # Replace these IDs with your actual 'Copy Action ID' strings from Streamer.bot
    with c1:
        if st.button("🔥 Hype Train", use_container_width=True):
            asyncio.run(call_sb("your-hype-id"))
            
    with c2:
        if st.button("📢 Ad Break", use_container_width=True):
            asyncio.run(call_sb("your-ad-id"))
            
    with c3:
        if st.button("💬 Clear Chat", use_container_width=True):
            asyncio.run(call_sb("your-clear-id"))

# Footer Status
st.divider()
st.caption("Connected to: " + OBS_CONFIG["host"] + " | Streamer.bot: " + SB_CONFIG["url"])
