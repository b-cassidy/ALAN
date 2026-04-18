import streamlit as st
import time
from engine import AlanEngine
import platform
import psutil
import subprocess


def get_system_info():
    """Detects local hardware specs dynamically."""
    try:
        # Gets the exact model (e.g., Apple M4 Max) on macOS
        cpu_info = subprocess.check_output(
            ['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
    except:
        cpu_info = platform.processor()

    ram = f"{round(psutil.virtual_memory().total / (1024**3))} GB"
    return {
        "cpu": cpu_info,
        "ram": ram,
        "os": f"{platform.system()} {platform.release()}"
    }


sys_info = get_system_info()


# Page Configuration
st.set_page_config(
    page_title="ALAN | Data Insights",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Dark Theme CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    .stChatMessage {
        border-radius: 10px;
        margin-bottom: 10px;
    }
    /* Style for the sidebar file list */
    .file-text {
        font-size: 0.85rem;
        color: #8b949e;
    }
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'alan' not in st.session_state:
    with st.spinner("Initializing ALAN Core Systems..."):
        st.session_state.alan = AlanEngine()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Dashboard
with st.sidebar:
    st.image("assets/logo_large.png", use_container_width=True)
    # st.title("🤖 ALAN")
    # st.caption("Automated Local Analysis Network")
    # st.markdown("---")

    # System Info
    st.sidebar.info(
        f"**System Status:** Online\n\n"
        f"**Engine:** {st.session_state.alan.model_name}\n\n"
        f"**Hardware:** {sys_info['cpu']}\n\n"
        f"**Memory:** {sys_info['ram']}\n\n"
        f"**Platform:** {sys_info['os']}"
    )

    # Tools & Actions
    # st.subheader("🛠️ Actions")
    if st.button("Clear Conversation History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    # st.markdown("---")

    # Knowledge Base Section
    with st.expander("🗄️ Knowledge Base", expanded=False):
        if st.session_state.alan.filenames:
            for f in st.session_state.alan.filenames:
                st.markdown(f"📄 `{f}`")
        else:
            st.warning("No documents detected in `/data`")
    # st.markdown("---")


# Main Chat Interface
st.title("💬 Data Query Portal")
st.info("ALAN (Automated Local Analysis Network) is grounded in your local data. Answers are generated using only your provided documents.")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Query your knowledge base..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant Response
    with st.chat_message("assistant"):
        with st.status("ALAN is analyzing...", expanded=False) as status:
            st.write("Scanning vector database for relevant snippets...")
            # We skip the fake sleep here for pure performance,
            # but you can add it back if you want that 'cinematic' feel.

            response = st.session_state.alan.ask(prompt)

            st.write("Cross-referencing sources and synthesizing answer...")
            status.update(label="Analysis Complete!",
                          state="complete", expanded=False)

        st.markdown(response)
        st.session_state.messages.append(
            {"role": "assistant", "content": response})
