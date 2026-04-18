import os
import streamlit as st
import time
from engine import AlanEngine
import platform
import psutil
import subprocess

# Caching as this does not need to run every time we see a change in the UI


@st.cache_data
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
# #####################################
st.set_page_config(
    page_title="ALAN | Data Insights",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Dark Theme CSS
# #####################################
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
    /* Style for the fake expander knowledge base list */
    .library-box {
        background-color: #1c2128 !important;
        padding: 12px !important;
        border-radius: 8px !important;
        border: 2px solid #30363d !important;
        margin-top: 10px;
        margin-bottom: 10px;
        display: block;
    }
    .file-item {
        font-size: 0.85rem;
        color: #c9d1d9;
        margin-bottom: 5px;
        line-height: 1.2;
    }
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
# #####################################
if 'alan' not in st.session_state:
    with st.spinner("Initializing ALAN Core Systems..."):
        st.session_state.alan = AlanEngine()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Dashboard
# #####################################
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
    # #####################################

    # Clear Conversation Button
    # st.subheader("🛠️ Actions")
    if st.button("Clear Conversation History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # File Uploader
    # Initilise toggle state for data upload options
    if "show_uploader" not in st.session_state:
        st.session_state.show_uploader = False

    # Set button text to display
    if st.session_state.show_uploader:
        upload_label = "Cancel Adding to Knowledge Base"
    else:
        upload_label = "Add to Knowledge Base"

    # Upload options toggle button
    if st.button(upload_label, use_container_width=True):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()

    # Show uploader when toggled above
    if st.session_state.show_uploader:
        # st.markdown("---")
        uploaded_files = st.file_uploader(
            "Select documents to add:",
            type=['pdf', 'docx', 'doc', 'txt', 'xlsx', 'xls'],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        # Logic to only show the actual upload button if files have been selected
        if uploaded_files:
            if st.button("Upload & Index Data", use_container_width=True):
                # Assign status that is used in our progress bar
                with st.status("ALAN is absorbing new data...", expanded=True) as status:
                    # Double check that folder exists before continuing
                    if not os.path.exists('data'):
                        os.makedirs('data')

                    for uploaded_file in uploaded_files:
                        file_path = os.path.join("data", uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                    # Create progress bar
                    progress_bar = st.progress(0, text='Preparing indexing...')

                    # Bridge to ingestion function in engine.py
                    def update_ui(percent):
                        progress_bar.progress(
                            percent, text=f"Indexing knowledge: {int(percent*100)}%")

                    result = st.session_state.alan.ingest_data(
                        progress_callback=update_ui)

                    # Remove progress bar when done
                    progress_bar.empty()
                    status.update(label=result, state="complete",
                                  expanded=False)

                    # Hide uplaod section when complete
                    time.sleep(1.5)
                    st.session_state.show_uploader = False
                    st.rerun()

    # View Knowledge Base (Fake Expander)
    # Initilise toggle state
    if "show_library" not in st.session_state:
        st.session_state.show_library = False

    # Set button text to display
    library_count = len(st.session_state.alan.filenames)
    if st.session_state.show_library:
        library_label = f"Hide Knowledge Base - {library_count} file(s)"
    else:
        library_label = f"View Knowledge Base - {library_count} file(s)"
    # library_label = "Hide Knowledge Base" if st.session_state.show_library else "View Knowledge Base"

    # Add toggle option to sidebar for viewing knowledge base
    if st.button(library_label, use_container_width=True):
        st.session_state.show_library = not st.session_state.show_library
        st.rerun()

    # Conditional Library Content
    if st.session_state.get("show_library", False):
        if st.session_state.alan.filenames:
            # Start the styled container
            # st.markdown('<div class="library-box">', unsafe_allow_html=True)
            container_html = '<div class="library-box">'
            for f in st.session_state.alan.filenames:
                # Create display file name
                file_display_name = os.path.splitext(
                    f)[0].replace("_", " ").title()
                container_html += f'<div class="file-item">📄 {file_display_name}</div>'
            container_html += '</div>'

            st.markdown(container_html, unsafe_allow_html=True)
        else:
            # Warning only shows if the user clicked the button AND no files exist
            st.warning("No documents detected in /data folder.")


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
