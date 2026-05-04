import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# Page Configuration
st.set_page_config(page_title="Streamer Dashboard", layout="wide")
st.title("🎮 Unified Stream Control")

# --- SIDEBAR: CONNECTION SETTINGS ---
with st.sidebar:
    st.header("Connection Settings")
    obs_host = st.text_input("OBS Host", "localhost")
    obs_port = st.number_input("OBS Port", value=4455) # Default for OBS 28+
    obs_pw = st.text_input("OBS Password", type="password")
    
    st.divider()
    
    sb_url = st.text_input("Streamer.bot WS URL", "ws://127.0.0.1:8080/")

# --- OBS LOGIC ---
def trigger_obs_scene(scene_name):
    try:
        ws = obsws(obs_host, obs_port, obs_pw)
        ws.connect()
        ws.call(requests.SetCurrentProgramScene(sceneName=scene_name))
        ws.disconnect()
        st.success(f"Switched to {scene_name}")
    except Exception as e:
        st.error(f"OBS Error: {e}")

# --- STREAMER.BOT LOGIC ---
async def call_sb_action(action_id):
    try:
        async with websockets.connect(sb_url) as websocket:
            # Streamer.bot request format
            payload = {
                "request": "DoAction",
                "id": "streamlit-trigger",
                "action": {"id": action_id}
            }
            await websocket.send(json.dumps(payload))
            st.toast("Action triggered!")
    except Exception as e:
        st.error(f"Streamer.bot Error: {e}")

# --- DASHBOARD LAYOUT ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎥 OBS Scene Switcher")
    # Add your specific scene names here
    scenes = ["Starting Soon", "Just Chatting", "Gaming", "Be Right Back"]
    for scene in scenes:
        if st.button(f"Switch to {scene}", use_container_width=True):
            trigger_obs_scene(scene)

with col2:
    st.subheader("🤖 Streamer.bot Actions")
    # Replace these IDs with your actual Action IDs from Streamer.bot
    # You can find the ID by right-clicking an action in Streamer.bot -> Copy Action ID
    actions = {
        "Sound Alert": "123-abc-id",
        "Clear Chat": "456-def-id",
        "Trigger Pyrotechnics": "789-ghi-id"
    }
    
    for name, act_id in actions.items():
        if st.button(f"🔥 {name}", use_container_width=True):
            asyncio.run(call_sb_action(act_id))

# --- LIVE STATUS (Optional) ---
st.divider()
if st.button("Check Connection Status"):
    # Minimal logic to ping both services
    st.info("Checking services...")
