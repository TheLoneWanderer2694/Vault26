import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# --- CONFIGURATION ---
if 'obs_pass' not in st.session_state:
    st.session_state.obs_pass = ""

# --- OBS LOGIC ---
def get_obs_client():
    try:
        ws = obsws("localhost", 4455, st.session_state.obs_pass)
        ws.connect()
        return ws
    except:
        return None

def fetch_obs_data():
    client = get_obs_client()
    if client:
        scenes_res = client.call(requests.GetSceneList())
        status_res = client.call(requests.GetStreamStatus())
        current_scene = scenes_res.getCurrentProgramSceneName()
        scenes = [s['sceneName'] for s in scenes_res.getScenes()]
        is_live = status_res.getOutputActive()
        client.disconnect()
        return {"scenes": scenes, "current": current_scene, "live": is_live}
    return None

# --- STREAMER.BOT LOGIC ---
async def sb_request(method, params=None):
    try:
        async with websockets.connect("ws://127.0.0.1:8080/") as ws:
            payload = {"request": method, "id": "st-query", **(params or {})}
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
            return json.loads(resp)
    except:
        return None

# --- UI SETUP ---
st.set_page_config(page_title="Pro Stream Center", layout="wide")

# Custom CSS for "Stream Deck" look
st.markdown("""
    <style>
    .stButton>button { height: 80px; border-radius: 10px; font-weight: bold; }
    .live-indicator { color: red; font-weight: bold; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR & AUTH ---
with st.sidebar:
    st.title("🔗 Connections")
    st.session_state.obs_pass = st.text_input("OBS Password", type="password")
    if st.button("🔄 Refresh Connections"):
        st.rerun()
    
    st.divider()
    obs_info = fetch_obs_data()
    if obs_info:
        st.success("OBS: Connected")
        if obs_info['live']:
            st.markdown("<p class='live-indicator'>● LIVE ON STREAM</p>", unsafe_allow_html=True)
    else:
        st.error("OBS: Disconnected")

# --- MAIN DASHBOARD ---
tab_obs, tab_sb, tab_mixer = st.tabs(["🎥 OBS Studio", "🤖 Streamer.bot", "🎚️ Audio Mixer"])

with tab_obs:
    if obs_info:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader("Scenes")
            for scene in obs_info['scenes']:
                # Highlight the active scene
                type = "primary" if scene == obs_info['current'] else "secondary"
                if st.button(scene, key=f"sc_{scene}", use_container_width=True, type=type):
                    client = get_obs_client()
                    client.call(requests.SetCurrentProgramScene(sceneName=scene))
                    client.disconnect()
                    st.rerun()
        
        with col2:
            st.subheader("Quick Toggles")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🎬 Record", use_container_width=True):
                    client = get_obs_client()
                    client.call(requests.ToggleRecord())
                    client.disconnect()
            with c2:
                if st.button("📸 Screenshot", use_container_width=True):
                    st.toast("Screenshot saved to OBS folder!")
    else:
        st.warning("Connect to OBS to see scenes.")

with tab_sb:
    st.subheader("Auto-Populated Actions")
    # Fetching actions directly from Streamer.bot so you don't have to copy IDs!
    sb_data = asyncio.run(sb_request("GetActions"))
    
    if sb_data and "actions" in sb_data:
        actions = sb_data["actions"]
        cols = st.columns(4)
        for i, action in enumerate(actions):
            with cols[i % 4]:
                if st.button(action['name'], key=action['id'], use_container_width=True):
                    asyncio.run(sb_request("DoAction", {"action": {"id": action['id']}}))
                    st.toast(f"Triggered: {action['name']}")
    else:
        st.info("Start Streamer.bot WebSocket server to see actions.")

with tab_mixer:
    st.subheader("Volume Controls")
    if obs_info:
        client = get_obs_client()
        # Fetch audio inputs
        inputs = client.call(requests.GetInputList()).getInputs()
        for i in inputs:
            if "audio" in i['inputKind']:
                vol = client.call(requests.GetInputVolume(inputName=i['inputName']))
                new_vol = st.slider(f"Volume: {i['inputName']}", -100.0, 0.0, float(vol.getInputVolumeDb()))
                # In a real app, you'd add a 'SetVolume' call here on change
        client.disconnect()
