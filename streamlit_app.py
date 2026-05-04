import streamlit as st
import asyncio
import json
import websockets

# Configuration
SB_WS_URL = "ws://127.0.0.1:8080/"

async def send_sb_request(request_data):
    """Generic function to talk to Streamer.bot"""
    try:
        async with websockets.connect(SB_WS_URL) as ws:
            await ws.send(json.dumps(request_data))
            # Optional: Wait for a response from the bot
            response = await ws.recv()
            return json.loads(response)
    except Exception as e:
        st.error(f"Failed to connect to Streamer.bot: {e}")
        return None

def trigger_action(action_id):
    """Triggers a specific Action via its ID"""
    payload = {
        "request": "DoAction",
        "id": "streamlit-trigger-123", # Unique ID for this request
        "action": {
            "id": action_id
        }
    }
    asyncio.run(send_sb_request(payload))

# --- UI Layout ---
st.header("🤖 Streamer.bot Controls")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📢 Shoutout", use_container_width=True):
        # Replace with your actual Action ID (Right-click action -> Copy ID)
        trigger_action("your-shoutout-id-here")

with col2:
    if st.button("🎵 Skip Song", use_container_width=True):
        trigger_action("your-skip-id-here")

with col3:
    if st.button("🚫 Clear Chat", use_container_width=True):
        trigger_action("your-clear-chat-id-here")
