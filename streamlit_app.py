import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import asyncio
import websockets
import json
import time
from datetime import datetime
from obswebsocket import obsws, requests

# --- CONFIGURATION ---
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "your_obs_password"
SB_HOST = "127.0.0.1"
SB_PORT = 8080

# --- PAGE SETUP ---
st.set_page_config(page_title="Ultimate Stream Hub", layout="wide", page_icon="🎙️")

# --- STYLED HEADER ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ Ultimate Stream Hub")
tabs = st.tabs(["📊 Analytics & Events", "🎬 OBS Control", "💻 System Terminal"])

# --- TAB 1: ANALYTICS & STREAMER.BOT ---
with tabs[0]:
    col_metrics, col_events = st.columns([2, 1])
    
    with col_metrics:
        st.subheader("Live Performance")
        metric_placeholder = st.empty()
        chart_placeholder = st.empty()
        
        # Simple simulation logic for the analytics tab
        if 'data' not in st.session_state:
            st.session_state.data = pd.DataFrame({'Time': [datetime.now()], 'Value': [50]})
            
    with col_events:
        st.subheader("🔔 Streamer.bot Events")
        event_placeholder = st.empty()

    async def run_analytics_loop():
        # This acts as our "Main Loop" for data and websockets
        uri = f"ws://{SB_HOST}:{SB_PORT}/"
        recent_events = []
        
        try:
            async with websockets.connect(uri) as ws:
                # Subscribe to events
                sub = {"request": "Subscribe", "id": "1", "events": {"Twitch": ["Follow", "Cheers"]}}
                await ws.send(json.dumps(sub))
                
                while True:
                    # 1. Update Simulated Analytics
                    new_val = st.session_state.data['Value'].iloc[-1] + np.random.randint(-2, 3)
                    new_row = pd.DataFrame({'Time': [datetime.now()], 'Value': [new_val]})
                    st.session_state.data = pd.concat([st.session_state.data, new_row]).tail(30)
                    
                    with metric_placeholder.container():
                        m1, m2 = st.columns(2)
                        m1.metric("Live Viewers", new_val + 100, f"{np.random.randint(-5, 5)}")
                        m2.metric("Stream Health", "Excellent", "0% Drop")
                    
                    chart_placeholder.line_chart(st.session_state.data.set_index('Time'))

                    # 2. Check for Streamer.bot messages (non-blocking)
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        data = json.loads(msg)
                        if "event" in data:
                            user = data["data"].get("user", "Someone")
                            etype = data["event"]["type"]
                            recent_events.insert(0, f"**{user}** performed **{etype}**")
                    except asyncio.TimeoutError:
                        pass
                    
                    with event_placeholder.container():
                        for e in recent_events[:8]:
                            st.write(e)
                            
                    await asyncio.sleep(1)
        except Exception as e:
            st.error(f"Streamer.bot disconnected: {e}")

    if st.button("Connect Live Feed"):
        asyncio.run(run_analytics_loop())

# --- TAB 2: OBS CONTROL ---
with tabs[1]:
    st.subheader("Quick Scene Switcher")
    try:
        obs = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
        obs.connect()
        scenes = obs.call(requests.GetSceneList())
        
        cols = st.columns(4)
        for idx, scene in enumerate(scenes.getScenes()):
            s_name = scene['sceneName']
            if cols[idx % 4].button(f"🎥 {s_name}", use_container_width=True):
                obs.call(requests.SetCurrentProgramScene(sceneName=s_name))
                st.toast(f"Switched to {s_name}")
        obs.disconnect()
    except:
        st.warning("Could not connect to OBS. Check your WebSocket settings.")

# --- TAB 3: BASH TERMINAL ---
with tabs[2]:
    st.subheader("System Command Center")
    cmd = st.text_input("Enter Bash Command", placeholder="ls -la / pgrep obs / ping google.com")
    
    if st.button("Run Command"):
        if cmd:
            try:
                # Using list format for safety, but split() for simple logic
                process = subprocess.Popen(
                    cmd.split(), 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True
                )
                
                output_area = st.empty()
                full_log = ""
                
                # Stream the bash output live
                for line in process.stdout:
                    full_log += line
                    output_area.code(full_log, language="bash")
            except Exception as e:
                st.error(f"Error: {e}")
