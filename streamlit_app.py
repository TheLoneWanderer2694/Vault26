import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Real-Time Streaming Dashboard",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Real-Time Operational Metrics")

# Create placeholders for the UI elements
metric_placeholder = st.empty()
chart_placeholder = st.empty()
table_placeholder = st.empty()

# Initialize dummy data
def get_initial_data():
    return pd.DataFrame({
        'Timestamp': [datetime.now()],
        'Value': [np.random.randint(40, 60)]
    })

data = get_initial_data()

# Simulation Loop
for i in range(100):
    # 1. Generate "New" Streaming Data
    new_row = {
        'Timestamp': datetime.now(),
        'Value': data['Value'].iloc[-1] + np.random.randint(-5, 6)
    }
    data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
    
    # Keep only the last 20 data points for the view
    display_df = data.tail(20)

    # 2. Update Metrics (KPIs)
    with metric_placeholder.container():
        col1, col2, col3 = st.columns(3)
        current_val = display_df['Value'].iloc[-1]
        prev_val = display_df['Value'].iloc[-2] if len(display_df) > 1 else current_val
        
        col1.metric("System Load", f"{current_val}%", f"{current_val - prev_val}%")
        col2.metric("Active Users", np.random.randint(1000, 1200), "4%")
        col3.metric("Uptime", "99.99%", "0.01%")

    # 3. Update Chart
    with chart_placeholder.container():
        st.subheader("Live Data Feed")
        st.line_chart(display_df.set_index('Timestamp'))

    # 4. Update Data Table
    with table_placeholder.container():
        st.subheader("Recent Logs")
        st.dataframe(display_df.sort_values('Timestamp', ascending=False), use_container_width=True)

    # Control the "Stream" speed
    time.sleep(1)
