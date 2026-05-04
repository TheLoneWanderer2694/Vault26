import streamlit as st
import asyncio
import websockets
import json
from obswebsocket import obsws, requests

# --- CONFIGURATION ---
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "your_obs_password"

SB_HOST = "127.0.0.1"
SB_PORT = 8080 # Default Streamer.bot Websocket port

st.set_page_config(page_title="Stream Control Center", layout="wide")

## --- OBS CONTROL FUNCTIONS ---
def get_obs_client():
    try:
        client = obsws(OBS_HOST, OBS_PORT, OBS_PASSWORD)
        client.connect()
        return client
    except Exception as e:
        st.error(f"OBS Connection Failed: {e}")
        return None

## --- STREAMER.BOT DATA ---
# We use a placeholder to update live events without refreshing the whole page
st.title("🎮 Broadcast Control Dashboard")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🎬 OBS Scenes")
    obs = get_obs_client()
    if obs:
        scenes = obs.call(requests.GetSceneList())
        for scene in scenes.getScenes():
            scene_name = scene['sceneName']
            if st.button(f"Switch to: {scene_name}", key=scene_name):
                obs.call(requests.SetCurrentProgramScene(sceneName=scene_name))
                st.success(f"Switched to {scene_name}")
        obs.disconnect()

with col2:
    st.subheader("🔔 Live Streamer.bot Events")
    event_placeholder = st.empty()
    
    # This async function listens to Streamer.bot events
    async def listen_to_streamerbot():
        uri = f"ws://{SB_HOST}:{SB_PORT}/"
        async with websockets.connect(uri) as websocket:
            # Subscribe to events (General, Twitch, etc.)
            subscribe_msg = {
                "request": "Subscribe",
                "id": "123",
                "events": {
                    "Twitch": ["Follow", "Cheers", "Subscription"],
                    "General": ["Custom"]
                }
            }
            await websocket.send(json.dumps(subscribe_msg))
            
            recent_events = []
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                # Format the timestamp and event type
                if "event" in data:
                    event_type = data["event"]["type"]
                    user = data["data"].get("user", "Unknown")
                    recent_events.insert(0, f"**{event_type}**: {user} just interacted!")
                
                # Keep only last 10 events
                recent_events = recent_events[:10]
                
                with event_placeholder.container():
                    for ev in recent_events:
                        st.write(ev)

    # Start the websocket listener
    if st.button("Start Listening to Events"):
        asyncio.run(listen_to_streamerbot())
