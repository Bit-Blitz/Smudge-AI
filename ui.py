import streamlit as st
import speech_recognition as sr
import threading
import time
import queue
import os
import sys
import json
from PIL import Image
import io

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from main import Agent
from utils.logger import logger

# --- Configuration ---
st.set_page_config(
    page_title="Aegis OS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for Native-like, Futuristic Look ---
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #0e1117; /* Dark background */
        color: #e0e0e0;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Hide Streamlit Header/Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Rounded Corners & Futuristic Elements */
    .stButton>button {
        border-radius: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.2);
    }
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 15px;
        background-color: #1e293b;
        color: #e0e0e0;
        border: 1px solid #334155;
    }
    
    /* Toggle Switch Styling (Streamlit's default is okay, but we can enhance container) */
    .stToggle {
        padding: 10px;
        background-color: #1e293b;
        border-radius: 15px;
        margin-bottom: 10px;
    }

    /* Chat/Log Area */
    .chat-message {
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        background-color: #1e293b;
        border-left: 5px solid #764ba2;
    }
    .user-message {
        border-left-color: #667eea;
    }
    .agent-message {
        border-left-color: #764ba2;
    }
    
    /* Status Indicator */
    .status-indicator {
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: bold;
        display: inline-block;
    }
    .status-idle { background-color: #334155; color: #94a3b8; }
    .status-running { background-color: #059669; color: #a7f3d0; }
    
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if 'agent' not in st.session_state:
    st.session_state.agent = Agent()
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'running' not in st.session_state:
    st.session_state.running = False

# --- Header ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("# 🛡️ Aegis OS <span style='font-size:0.5em; opacity:0.6'>Autonomous Desktop Agent</span>", unsafe_allow_html=True)
with col_h2:
    status = "RUNNING" if st.session_state.running else "IDLE"
    status_class = "status-running" if st.session_state.running else "status-idle"
    st.markdown(f"<div style='text-align:right'><span class='status-indicator {status_class}'>{status}</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- Controls Area ---
col_ctrl, col_main = st.columns([1, 2])

with col_ctrl:
    st.markdown("### ⚙️ Controls")
    
    # Toggles
    voice_enabled = st.toggle("🎙️ Enable Voice Input", value=False)
    screen_vision_enabled = st.toggle("👁️ Enable Screen Vision", value=False)
    
    st.markdown("### 📊 Stats")
    st.metric("Steps", len(st.session_state.logs) // 2) # Rough estimate
    
    if st.button("🛑 Stop Agent"):
        st.session_state.running = False
        st.stop()

with col_main:
    # --- Input Section ---
    st.markdown("### 💬 Command Center")
    
    user_input = ""
    run_action = False
    
    if voice_enabled:
        st.info("Voice Mode Active. Click 'Listen' to speak.")
        if st.button("🎤 Listen Now"):
            r = sr.Recognizer()
            with sr.Microphone() as source:
                with st.spinner("Listening..."):
                    try:
                        audio = r.listen(source, timeout=5)
                        text = r.recognize_google(audio)
                        st.success(f"Heard: {text}")
                        user_input = text
                        run_action = True
                    except sr.WaitTimeoutError:
                        st.warning("No speech detected.")
                    except sr.UnknownValueError:
                        st.error("Could not understand audio.")
                    except sr.RequestError as e:
                        st.error(f"Speech service error: {e}")
    else:
        # Text Mode
        user_input = st.text_area("Enter command:", height=80, placeholder="Type your instruction here...")
        if st.button("🚀 Execute"):
            run_action = True

    # --- Execution Logic ---
    if run_action and user_input:
        st.session_state.running = True
        
        # Log User Input
        st.session_state.logs.append({"role": "user", "content": user_input})
        
        with st.spinner("Aegis is thinking..."):
            # Context preparation
            context = {}
            if screen_vision_enabled:
                context["use_vision"] = True
                st.toast("Capturing screen context...", icon="👁️")
            
            # Run Agent Step
            result = st.session_state.agent.run_step(user_input, context=context)
            
            # Log Agent Response
            st.session_state.logs.append({"role": "agent", "content": result})
        
        st.session_state.running = False
        st.rerun()

# --- Logs / History ---
st.markdown("### 📜 Activity Log")
log_container = st.container()

with log_container:
    for log in reversed(st.session_state.logs): # Show newest first
        role = log["role"]
        content = log["content"]
        
        if role == "user":
            st.markdown(f"""
            <div class='chat-message user-message'>
                <b>👤 User:</b> {content}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Format agent output (it might be a dict)
            if isinstance(content, dict):
                msg = content.get("message", str(content))
                status = content.get("status", "")
                detail = ""
                if "log" in content:
                     detail = f"<br><small>Plan: {content['log'].get('plan', {}).get('action', 'N/A')}</small>"
                
                st.markdown(f"""
                <div class='chat-message agent-message'>
                    <b>🛡️ Aegis ({status}):</b> {msg} {detail}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='chat-message agent-message'>
                    <b>🛡️ Aegis:</b> {content}
                </div>
                """, unsafe_allow_html=True)

            st.image(image, caption='Uploaded Image', use_column_width=True)
            vision_instruction = st.text_input("Instruction for this image (optional):", "Analyze this image and take action.")
            if st.button("Process Vision Input"):
                st.session_state.running = True
                with st.spinner("Analyzing image..."):
                    # Save uploaded file to temp path
                    temp_path = f"d:/Ceaser-AI/logs/temp_upload_{int(time.time())}.png"
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    image.save(temp_path)
                    
                    st.session_state.logs.append(f"User (Vision): [Image Uploaded] - {vision_instruction}")
                    
                    # Get current state for context
                    current_state = st.session_state.agent.perception.capture_state()
                    
                    # Call Vision Fallback
                    result = st.session_state.agent.vision_fallback.fallback(vision_instruction, current_state, image_path=temp_path)
                    
                    st.session_state.logs.append(f"Agent (Vision Analysis): {result}")
                    
                    # Execute the action if valid
                    if "action" in result and result["action"] != "wait":
                         exec_result = st.session_state.agent.executor.execute_plan(result)
                         st.session_state.logs.append(f"Agent (Execution): {exec_result}")

                st.session_state.running = False
                st.rerun()

    st.divider()
    st.subheader("Agent Logs")
    log_container = st.container(height=400)
    with log_container:
        for log in st.session_state.logs:
            st.code(log)

with col2:
    st.subheader("Live View")
    # Show screenshot of current desktop
    if st.button("Refresh View"):
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            st.image(screenshot, caption="Current Desktop State", use_column_width=True)
        except Exception as e:
            st.error(f"Failed to capture screen: {e}")

    st.subheader("System State")
    if st.button("Get System Info"):
        state = st.session_state.agent.perception.capture_state()
        st.json(state)