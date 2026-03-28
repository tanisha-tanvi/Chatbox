import streamlit as st
import requests
import uuid
from supabase import create_client, Client

# --- 1. INITIALIZATION & SECRETS ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except KeyError as e:
    st.error(f"Missing Secret: {e}. Check your .streamlit/secrets.toml")
    st.stop()

# Initialize Supabase
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
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return [user['login'] for user in response.json()]
        else:
            return ["Guest_User"]
    except:
        return ["Guest_User"]

# --- 3. UI CONFIGURATION ---
st.set_page_config(page_title="Team Chatbox", page_icon="💬", layout="centered")
st.title("👨‍💻 Collaborator Chatroom")

collaborators = get_collaborators()

with st.sidebar:
    st.header("Project Settings")
    current_user = st.selectbox("Identify yourself:", collaborators)
    
    st.divider()
    st.subheader("Project Members")
    for user in collaborators:
        st.caption(f"👤 {user}")

# --- 4. DRIVE-STYLE FILE UPLOAD ---
# This section mimics the 'Upload' button in Drive
with st.expander("📤 Upload Files / Photos from PC"):
    uploaded_file = st.file_uploader("Choose a file", type=["png", "jpg", "jpeg", "pdf", "zip", "docx", "mp4"])
    
    if uploaded_file is not None:
        if st.button(f"Upload and Send {uploaded_file.name}"):
            with st.spinner("Uploading to cloud..."):
                try:
                    # Create unique filename to prevent overwriting
                    file_ext = uploaded_file.name.split(".")[-1]
                    unique_name = f"{uuid.uuid4()}.{file_ext}"
                    storage_path = f"uploads/{unique_name}"
                    
                    # 1. Upload file to Supabase Storage Bucket
                    supabase.storage.from_("chat-media").upload(
                        path=storage_path,
                        file=uploaded_file.getvalue(),
                        file_options={"content-type": uploaded_file.type}
                    )
                    
                    # 2. Get the public link
                    file_url = supabase.storage.from_("chat-media").get_public_url(storage_path)
                    
                    # 3. Save message to Database
                    new_msg = {
                        "content": f"Shared a file: {uploaded_file.name}",
                        "user_name": current_user,
                        "file_url": file_url
                    }
                    supabase.table("messages").insert(new_msg).execute()
                    
                    st.success("File shared!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {e}")

st.divider()

# --- 5. MESSAGE DISPLAY LOGIC ---
try:
    # Fetch last 30 messages
    res = supabase.table("messages").select("*").order("created_at", desc=True).limit(30).execute()
    messages = res.data
except Exception as e:
    st.error(f"Database error: {e}")
    messages = []

# Display from bottom to top
for m in reversed(messages):
    is_me = m['user_name'] == current_user
    with st.chat_message("user" if is_me else "assistant"):
        # Header: User Name
        st.markdown(f"**{m['user_name']}**")
        
        # Body: Text Content
        st.write(m['content'])
        
        # Attachment Logic
        if m.get('file_url'):
            url = m['file_url']
            # If it's an image, show it
            if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                st.image(url, use_container_width=True)
            # Otherwise, provide a download button
            else:
                st.link_button(f"📂 View Attachment", url)

# --- 6. CHAT INPUT (Text Only) ---
if prompt := st.chat_input(f"Message as {current_user}..."):
    new_msg = {"content": prompt, "user_name": current_user, "file_url": None}
    supabase.table("messages").insert(new_msg).execute()
    st.rerun()
