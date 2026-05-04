import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# --- CONFIGURATION ---
# We use your specific IP here so the dashboard knows exactly where to look
TARGET_IP = "127.0.0.1" 
OBS_PORT = 4455
SB_PORT = 8080

if 'obs_pass' not in st.session_state:
    st.session_state.obs_pass = ""

# --- OBS LOGIC ---
def get_obs_client():
    try:
        # Changed 'localhost' to TARGET_IP
        ws = obsws(TARGET_IP, OBS_PORT, st.session_state.obs_pass)
        ws.connect()
        return ws
    except:
        return None

# --- STREAMER.BOT LOGIC ---
async def sb_request(method, params=None):
    try:
        # Changed '127.0.0.1' to TARGET_IP
        uri = f"ws://{TARGET_IP}:{SB_PORT}/"
        async with websockets.connect(uri) as ws:
            payload = {"request": method, "id": "st-query", **(params or {})}
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
            return json.loads(resp)
    except:
        return None

# --- UI LOGIC ---
st.set_page_config(page_title="Remote Stream Deck", layout="wide")

with st.sidebar:
    st.title("🌐 Network Control")
    st.info(f"Connecting to PC at: {TARGET_IP}")
    st.session_state.obs_pass = st.text_input("OBS Password", type="password")
    
    if st.button("🔄 Force Refresh"):
        st.rerun()

# --- MAIN INTERFACE ---
tab_obs, tab_sb = st.tabs(["🎥 OBS Control", "🤖 Bot Actions"])

with tab_obs:
    obs_data = None
    client = get_obs_client()
    if client:
        scenes_res = client.call(requests.GetSceneList())
        scenes = [s['sceneName'] for s in scenes_res.getScenes()]
        current = scenes_res.getCurrentProgramSceneName()
        
        st.subheader("Switch Scenes")
        cols = st.columns(4)
        for i, scene in enumerate(scenes):
            with cols[i % 4]:
                is_active = (scene == current)
                if st.button(scene, key=f"obs_{scene}", use_container_width=True, 
                             type="primary" if is_active else "secondary"):
                    client.call(requests.SetCurrentProgramScene(sceneName=scene))
                    st.rerun()
        client.disconnect()
    else:
        st.warning(f"Could not reach OBS at {TARGET_IP}:{OBS_PORT}")

with tab_sb:
    st.subheader("Bot Actions")
    sb_data = asyncio.run(sb_request("GetActions"))
    
    if sb_data and "actions" in sb_data:
        actions = sb_data["actions"]
        cols = st.columns(4)
        for i, action in enumerate(actions):
            with cols[i % 4]:
                if st.button(action['name'], key=action['id'], use_container_width=True):
                    asyncio.run(sb_request("DoAction", {"action": {"id": action['id']}}))
                    st.toast(f"Executed {action['name']}")
    else:
        st.warning(f"Could not reach Streamer.bot at {TARGET_IP}:{SB_PORT}")
