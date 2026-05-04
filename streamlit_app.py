import streamlit as st
import asyncio
import json
from obswebsocket import obsws, requests
import websockets

# Initialize State
if 'obs_ip' not in st.session_state: st.session_state['obs_ip'] = "192.168.10.110"
if 'sb_ip' not in st.session_state: st.session_state['sb_ip'] = "192.168.10.110"

st.set_page_config(page_title="Stream Control", layout="wide")

with st.sidebar:
    st.header("🔌 Setup")
    st.session_state['obs_ip'] = st.text_input("OBS IP", value=st.session_state['obs_ip'])
    st.session_state['obs_pass'] = st.text_input("OBS Password", type="password")
    st.session_state['sb_ip'] = st.text_input("Bot IP", value=st.session_state['sb_ip'])
    if st.button("🔄 Reconnect"): st.rerun()

tab1, tab2 = st.tabs(["OBS", "Streamer.bot"])

with tab1:
    try:
        ws = obsws(st.session_state['obs_ip'], 4455, st.session_state.get('obs_pass', ''))
        ws.connect()
        st.success("✅ OBS Connected")
        # Scene logic here...
        ws.disconnect()
    except Exception as e:
        st.error(f"❌ OBS Failed: {e}")

with tab2:
    async def test_sb():
        uri = f"ws://{st.session_state['sb_ip']}:8080/"
        try:
            async with websockets.connect(uri, open_timeout=2) as websocket:
                return True
        except: return False

    if asyncio.run(test_sb()):
        st.success("✅ Streamer.bot Connected")
    else:
        st.error(f"❌ Streamer.bot Failed at {st.session_state['sb_ip']}:8080")
