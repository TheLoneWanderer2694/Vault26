import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# --- 1. PERSISTENT STATE INITIALIZATION ---
# This ensures that when you type an IP, it stays there even after a click.
if 'obs_ip' not in st.session_state:
    st.session_state['obs_ip'] = "192.168.10.110"
if 'sb_ip' not in st.session_state:
    st.session_state['sb_ip'] = "192.168.10.110"
if 'obs_pass' not in st.session_state:
    st.session_state['obs_pass'] = ""

# --- 2. CONFIGURATION & UI SETUP ---
st.set_page_config(page_title="Ultimate Stream Hub", layout="wide", page_icon="🎮")

st.markdown("""
    <style>
    .stButton>button { height: 60px; border-radius: 8px; font-weight: bold; }
    .stHeader { color: #FF4B4B; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.header("🔌 Connection Manager")
    
    # OBS Configuration
    st.subheader("🎥 OBS Studio")
    obs_input = st.text_input("OBS IP Address", value=st.session_state['obs_ip'], key="obs_ip_in")
    obs_pass_input = st.text_input("OBS Password", value=st.session_state['obs_pass'], type="password", key="obs_pass_in")
    st.session_state['obs_ip'] = obs_input
    st.session_state['obs_pass'] = obs_pass_input
    
    st.divider()
    
    # Streamer.bot Configuration
    st.subheader("🤖 Streamer.bot")
    sb_input = st.text_input("Bot IP Address", value=st.session_state['sb_ip'], key="sb_ip_in")
    st.session_state['sb_ip'] = sb_input
    
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.rerun()

# --- 3. COMMUNICATION LOGIC ---
def get_obs_client():
    """Connects to OBS using current session state[cite: 2]."""
    try:
        ws = obsws(st.session_state['obs_ip'], 4455, st.session_state['obs_pass'])
        ws.connect()
        return ws
    except:
        return None

async def sb_request(method, params=None):
    """Sends a WebSocket request to Streamer.bot[cite: 2]."""
    uri = f"ws://{st.session_state['sb_ip']}:8080/"
    try:
        async with websockets.connect(uri, open_timeout=3) as ws:
            payload = {"request": method, "id": "st-hub", **(params or {})}
            await ws.send(json.dumps(payload))
            return json.loads(await ws.recv())
    except:
        return None

# --- 4. MAIN DASHBOARD INTERFACE ---
st.title("🕹️ Production Control Center")
tab_obs, tab_sb = st.tabs(["OBS SCENES", "BOT ACTIONS"])

with tab_obs:
    client = get_obs_client()
    if client:
        st.success(f"OBS Connected: {st.session_state['obs_ip']} ✅")
        try:
            res = client.call(requests.GetSceneList())
            scenes = [s['sceneName'] for s in res.getScenes()]
            current = res.getCurrentProgramSceneName()
            
            st.write(f"**Live Scene:** `{current}`")
            cols = st.columns(4)
            for i, scene in enumerate(scenes):
                with cols[i % 4]:
                    # Primary color for the active scene[cite: 2]
                    is_active = (scene == current)
                    if st.button(scene, key=f"obs_{scene}", use_container_width=True, 
                                 type="primary" if is_active else "secondary"):
                        client.call(requests.SetCurrentProgramScene(sceneName=scene))
                        st.rerun()
            client.disconnect()
        except Exception as e:
            st.error(f"OBS Error: {e}")
    else:
        st.error(f"OBS Offline at {st.session_state['obs_ip']}:4455")
        st.info("Check Tools > WebSocket Server Settings in OBS.")

with tab_sb:
    # Fetch actions automatically[cite: 2]
    sb_data = asyncio.run(sb_request("GetActions"))
    if sb_data and "actions" in sb_data:
        st.success(f"Streamer.bot Connected: {st.session_state['sb_ip']} ✅")
        actions = sb_data["actions"]
        cols = st.columns(4)
        for i, action in enumerate(actions):
            if not action.get('name'): continue
            with cols[i % 4]:
                if st.button(action['name'], key=action['id'], use_container_width=True):
                    asyncio.run(sb_request("DoAction", {"action": {"id": action['id']}}))
                    st.toast(f"Triggered: {action['name']}")
    else:
        st.error(f"Streamer.bot Offline at {st.session_state['sb_ip']}:8080")
        st.info("Ensure WebSocket Address is 0.0.0.0 and 'Remote Requests' are allowed[cite: 1, 2].")
