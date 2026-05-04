import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# --- CONFIGURATION DEFAULTS ---
# You can set these to different IPs if your services are on different PCs
DEFAULT_OBS_IP = "192.168.10.110" 
DEFAULT_SB_IP = "192.168.10.110" 

# --- SESSION STATE INITIALIZATION ---
if 'obs_pass' not in st.session_state:
    st.session_state.obs_pass = ""

# --- OBS LOGIC ---
def get_obs_client(ip, port, password):
    try:
        ws = obsws(ip, port, password)
        ws.connect()
        return ws
    except Exception as e:
        return None

# --- STREAMER.BOT LOGIC ---
async def sb_request(ip, port, method, params=None):
    uri = f"ws://{ip}:{port}/"
    try:
        async with websockets.connect(uri, open_timeout=5) as ws:
            payload = {"request": method, "id": "st-split", **(params or {})}
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
            return json.loads(resp)
    except:
        return None

# --- UI SETUP ---
st.set_page_config(page_title="Split IP Stream Control", layout="wide")

with st.sidebar:
    st.header("🔌 Connection Manager")
    
    with st.expander("🎥 OBS Settings", expanded=True):
        obs_ip = st.text_input("OBS IP Address", value=DEFAULT_OBS_IP)
        obs_port = st.number_input("OBS Port", value=4455)
        st.session_state.obs_pass = st.text_input("OBS Password", type="password")
    
    st.divider()
    
    with st.expander("🤖 Streamer.bot Settings", expanded=True):
        sb_ip = st.text_input("Bot IP Address", value=DEFAULT_SB_IP)
        sb_port = st.number_input("Bot Port", value=8080)
    
    if st.button("🔄 Reconnect All", use_container_width=True):
        st.rerun()

# --- MAIN INTERFACE ---
tab_obs, tab_sb = st.tabs(["OBS STUDIO", "STREAMER.BOT"])

with tab_obs:
    client = get_obs_client(obs_ip, obs_port, st.session_state.obs_pass)
    if client:
        st.success(f"Connected to OBS at {obs_ip}")
        res = client.call(requests.GetSceneList())
        scenes = [s['sceneName'] for s in res.getScenes()]
        current = res.getCurrentProgramSceneName()
        
        cols = st.columns(4)
        for i, scene in enumerate(scenes):
            with cols[i % 4]:
                if st.button(scene, key=f"obs_{scene}", use_container_width=True, 
                             type="primary" if scene == current else "secondary"):
                    client.call(requests.SetCurrentProgramScene(sceneName=scene))
                    st.rerun()
        client.disconnect()
    else:
        st.error(f"Failed to connect to OBS at {obs_ip}:{obs_port}")

with tab_sb:
    sb_data = asyncio.run(sb_request(sb_ip, sb_port, "GetActions"))
    if sb_data and "actions" in sb_data:
        st.success(f"Connected to Streamer.bot at {sb_ip}")
        actions = sb_data["actions"]
        cols = st.columns(4)
        for i, action in enumerate(actions):
            if not action.get('name'): continue
            with cols[i % 4]:
                if st.button(action['name'], key=action['id'], use_container_width=True):
                    asyncio.run(sb_request(sb_ip, sb_port, "DoAction", {"action": {"id": action['id']}}))
                    st.toast(f"Triggered: {action['name']}")
    else:
        st.error(f"Failed to connect to Streamer.bot at {sb_ip}:{sb_port}")
