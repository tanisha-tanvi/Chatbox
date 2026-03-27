import streamlit as st
import requests
from supabase import create_client, Client

# --- 1. LOAD SECRETS SAFELY ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except KeyError as e:
    st.error(f"Missing Secret: {e}. Ensure .streamlit/secrets.toml exists.")
    st.stop()

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. GITHUB COLLABORATOR FETCHING ---
REPO_OWNER = "tanisha-tanvi"
REPO_NAME = "Chatbox"

@st.cache_data(ttl=3600)
def get_collaborators():
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/collaborators"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        return [user['login'] for user in response.json()]
    else:
        st.sidebar.error(f"GitHub Error: {response.status_code}")
        # Default user if GitHub fails for testing
        return ["Guest_User"]

# --- 3. UI SETUP ---
st.set_page_config(page_title="Team Chatbox", page_icon="💬")
st.title("👨‍💻 Collaborator Chatroom")

collaborators = get_collaborators()

with st.sidebar:
    st.header("Project Members")
    for user in collaborators:
        st.write(f"👤 {user}")
    
    st.divider()
    current_user = st.selectbox("Identify yourself:", collaborators)

# --- 4. CHAT LOGIC ---
# Fetch existing messages
try:
    res = supabase.table("messages").select("*").order("created_at", desc=True).limit(30).execute()
    messages = res.data
except Exception as e:
    st.error(f"Database error: {e}")
    messages = []

# Display messages (Bottom to Top)
for m in reversed(messages):
    is_me = m['user_name'] == current_user
    with st.chat_message("user" if is_me else "assistant"):
        st.write(f"**{m['user_name']}**: {m['content']}")

# Chat Input
if prompt := st.chat_input(f"Message as {current_user}..."):
    new_msg = {"content": prompt, "user_name": current_user}
    supabase.table("messages").insert(new_msg).execute()
    st.rerun()