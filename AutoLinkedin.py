import streamlit as st
# Only import class definitions and config constants, not objects created at module level
from Monitor_Feed import LinkedInManager, GPTManager, GoogleManager, _config, _CONFIG_FILENAME, LOGGER
import subprocess
import threading
import queue
import time


# Do NOT instantiate managers at the top level!
# All automation is now run via subprocess (see stream_terminal_output),
# so these objects are not needed in the Streamlit process.


# Set dark theme via Streamlit config (must be in .streamlit/config.toml, but we can show instructions)
st.set_page_config(page_title="LinkedIn Automation Dashboard", layout="wide")

st.markdown(
    """
    <style>
    body, .stApp { background-color: #18191A !important; color: #E4E6EB !important; }
    .st-bw { background-color: #242526 !important; }
    .st-cq { color: #E4E6EB !important; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("LinkedIn Automation Dashboard")


# --- Sidebar: Global Automation Options ---
st.sidebar.header("Automation Options")
# Browser mode (headless/headon)
browser_mode = st.sidebar.radio(
    "Browser Mode",
    ["Headless (no browser window)", "Headon (show browser window)"],
    index=1
)
headless_flag = "--headless" if browser_mode.startswith("Headless") else "--headon"

# Comment source (GPT or Gemini)
comment_source = st.sidebar.radio(
    "Comment Generation Source",
    ["Gemini (Google)", "GPT (OpenAI)"]
)
# Map UI label to CLI value
if comment_source.startswith("Gemini"):
    comment_flag = "--comment-source google"
else:
    comment_flag = "--comment-source gpt"

# Number of posts to interact with (for warmup/feed)
max_posts = st.sidebar.slider("Max Posts to Like/Comment", min_value=1, max_value=20, value=10)
max_posts_flag = f"--max-posts {max_posts}"

# Add more options as needed (e.g., refresh interval, prompt selection, etc.)

menu = st.sidebar.selectbox(
    "Choose Action",
    [
        "Feed Monitoring",
        "Send Connection Requests",
        "Profile Warmup",
        "Connection Hunting",
        "Settings"
    ]
)


# Terminal output capture logic
def run_with_output(command, output_queue):
    """Run a shell command and put output lines in a queue."""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in iter(process.stdout.readline, ''):
        output_queue.put(line)
    process.stdout.close()
    process.wait()
    output_queue.put(None)  # Sentinel for end

def stream_terminal_output(command):
    output_queue = queue.Queue()
    thread = threading.Thread(target=run_with_output, args=(command, output_queue))
    thread.start()
    output_lines = []
    while True:
        line = output_queue.get()
        if line is None:
            break
        output_lines.append(line)
        st.code(''.join(output_lines), language='bash')
        time.sleep(0.1)


if menu == "Feed Monitoring":
    st.header("Feed Monitoring")
    refresh_interval = st.number_input("Feed Refresh Interval (seconds)", min_value=10, max_value=600, value=60)
    refresh_flag = f"--refresh-interval {refresh_interval}"
    if st.button("Start Feed Monitoring"):
        st.info("Feed monitoring will run in a new terminal window. Output will be shown below.")
        cmd = f"python Monitor_Feed.py --feed-monitoring {headless_flag} {comment_flag} {max_posts_flag} {refresh_flag}"
        stream_terminal_output(cmd)

elif menu == "Send Connection Requests":
    st.header("Send Connection Requests")
    uploaded_file = st.file_uploader("Upload Excel file with 'Profile Link' and 'Name' columns", type=["xlsx"])
    message = st.text_area("Message Template", "Hi {Name}, I'd like to connect with you on LinkedIn!")
    if st.button("Send Requests") and uploaded_file:
        with open("uploaded_connections.xlsx", "wb") as f:
            f.write(uploaded_file.read())
        st.info("Sending connection requests. Output will be shown below.")
        cmd = f"python Monitor_Feed.py --send-connections uploaded_connections.xlsx --message '{message}' {headless_flag}"
        stream_terminal_output(cmd)

elif menu == "Profile Warmup":
    st.header("Profile Warmup")
    uploaded_file = st.file_uploader("Upload Excel file with 'Profile Link' column", type=["xlsx"], key="warmup")
    if st.button("Warmup Profiles") and uploaded_file:
        with open("uploaded_warmup.xlsx", "wb") as f:
            f.write(uploaded_file.read())
        st.info("Warming up profiles. Output will be shown below.")
        cmd = f"python Monitor_Feed.py --profile-warmup uploaded_warmup.xlsx {headless_flag} {comment_flag} {max_posts_flag}"
        stream_terminal_output(cmd)

elif menu == "Connection Hunting":
    st.header("Connection Hunting")
    search_url = st.text_input("LinkedIn Search URL")
    output_file = st.text_input("Output Excel Filename", "linkedin_connections.xlsx")
    if st.button("Start Hunting") and search_url:
        st.info("Starting connection hunting. Output will be shown below.")
        cmd = f"python Monitor_Feed.py --connection-hunting '{search_url}' --output '{output_file}' {headless_flag}"
        stream_terminal_output(cmd)

elif menu == "Settings":
    st.header("Settings")
    st.subheader("OpenAI (GPT) Settings")
    # Set OpenAI API key
    openai_api = st.text_input("OpenAI API Key", value=_config["ALL"].get("api", "") if _config.has_section("ALL") else "", type="password")
    # Set GPT static prompt
    gpt_prompt = st.text_area("GPT Static Prompt", value=_config["ALL"].get("static prompt", "") if _config.has_section("ALL") else "")
    # Select GPT model
    gpt_models = [
        'gpt-4', 'gpt-4-0613', 'gpt-4-32k', 'gpt-4-32k-0613',
        'gpt-3.5-turbo', 'gpt-3.5-turbo-0613', 'gpt-3.5-turbo-16k', 'gpt-3.5-turbo-16k-0613'
    ]
    gpt_model = st.selectbox("GPT Model", gpt_models, index=gpt_models.index(_config["ALL"].get("ai model", "gpt-3.5-turbo")) if _config.has_section("ALL") and _config["ALL"].get("ai model", "gpt-3.5-turbo") in gpt_models else 4)
    if st.button("Save GPT Settings"):
        if not _config.has_section("ALL"):
            _config.add_section("ALL")
        _config["ALL"]["api"] = openai_api
        _config["ALL"]["static prompt"] = gpt_prompt
        _config["ALL"]["ai model"] = gpt_model
        with open(_CONFIG_FILENAME, "w", encoding="utf-8") as f:
            _config.write(f)
        st.success("GPT settings saved.")

    st.subheader("Gemini (Google) Settings")
    # Set Gemini API key
    gemini_api = st.text_input("Gemini API Key", value=_config["GOOGLE"].get("api", "") if _config.has_section("GOOGLE") else "", type="password")
    # Set Gemini static prompt
    gemini_prompt = st.text_area("Gemini Static Prompt", value=_config["GOOGLE"].get("static prompt", "") if _config.has_section("GOOGLE") else "")
    # Gemini model selection (show available or allow manual entry)
    gemini_model = st.text_input("Gemini Model (manual entry, e.g. gemini-1.5-pro)", value=_config["GOOGLE"].get("selected_model", "") if _config.has_section("GOOGLE") else "")
    if st.button("Save Gemini Settings"):
        if not _config.has_section("GOOGLE"):
            _config.add_section("GOOGLE")
        _config["GOOGLE"]["api"] = gemini_api
        _config["GOOGLE"]["static prompt"] = gemini_prompt
        _config["GOOGLE"]["selected_model"] = gemini_model
        with open(_CONFIG_FILENAME, "w", encoding="utf-8") as f:
            _config.write(f)
        st.success("Gemini settings saved.")

    st.info("Note: For browser automation, you may need to run this app locally and interact with the browser window.")

    # Show instructions for dark theme in .streamlit/config.toml
    with st.expander("How to enable full dark theme in Streamlit?"):
        st.markdown(
            """
            Add a file `.streamlit/config.toml` to your project with:
            ```toml
            [theme]
            base="dark"
            primaryColor="#1a73e8"
            backgroundColor="#18191A"
            secondaryBackgroundColor="#242526"
            textColor="#E4E6EB"
            font="sans serif"
            ```
            """
        )