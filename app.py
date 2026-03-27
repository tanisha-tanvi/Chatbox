import streamlit as st
import requests
from supabase import create_client, Client

# --- CONFIGURATION ---
GITHUB_TOKEN = "your_github_pat_here"
REPO_OWNER = "your_username"
REPO_NAME = "your_repo_name"
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_anon_key"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. FETCH GITHUB COLLABORATORS ---
@st.cache_data(ttl=3600) # Cache for 1 hour so we don't hit API limits
def get_collaborators():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/collaborators"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return [user['login'] for user in response.json()]
    else:
        st.error("Failed to fetch GitHub collaborators. Check your Token/Repo details.")
        return []

# --- 2. UI SETUP ---
st.title("👨‍💻 Collaborator Chatroom")
collaborators = get_collaborators()

with st.sidebar:
    st.header("Active Collaborators")
    # This creates a list of people in the sidebar
    for user in collaborators:
        st.write(f"👤 {user}")
    
    # Identity Selection (In a real app, this would be handled by GitHub Login)
    current_user = st.selectbox("Identify yourself as:", collaborators)

# --- 3. CHAT LOGIC ---
if prompt := st.chat_input(f"Message as {current_user}..."):
    # Insert message into Supabase with the GitHub username
    data = {"content": prompt, "user_name": current_user}
    supabase.table("messages").insert(data).execute()
    st.rerun()

# Display Chat History (Fetch from Supabase)
res = supabase.table("messages").select("*").order("created_at", desc=True).limit(20).execute()
for m in res.data:
    with st.chat_message("user" if m['user_name'] == current_user else "assistant"):
        st.write(f"**{m['user_name']}**: {m['content']}")