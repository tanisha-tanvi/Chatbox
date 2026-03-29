import streamlit as st
import requests
import uuid
from supabase import create_client, Client

# --- SETUP --- 
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except KeyError as e:
    st.error(f"Missing Secret: {e}. Check your .streamlit/secrets.toml")
    st.stop()

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# Configure Page Layout
st.set_page_config(page_title="Team Chatbox + IoT", page_icon="🌡️", layout="wide") 
st.title("👨‍💻 Collaborator Chatroom")

collaborators = get_collaborators()

# --- SIDEBAR: IoT MONITORING --- 
with st.sidebar:
    st.header("🏢 Lab IoT Monitor")
    
    # FETCH LATEST TEMPERATURE
    try:
        iot_res = supabase.table("messages") \
            .select("content") \
            .eq("user_name", "IoT-Sensor-Node") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if iot_res.data:
            latest_raw = iot_res.data[0]['content']
            # Clean "Temp: 24.00°C" to just "24.00°C" for the metric
            display_temp = latest_raw.replace("Temp: ", "")
            
            # BIG VISIBILITY: Professional Dashboard Metric
            st.metric(label="Current Lab Temperature", value=display_temp)
            
            if "ALERT" in latest_raw:
                st.error("⚠️ Temperature Threshold Exceeded!")
            else:
                st.success("✅ Sensor Streaming Live")
        else:
            st.info("Waiting for IoT data...")
            
        # Refresh Button for Demo
        if st.button("🔄 Refresh Live Feed"):
            st.rerun()
            
    except Exception as e:
        st.sidebar.write("IoT Data unavailable")

    st.divider()
    st.header("Project Settings")
    current_user = st.selectbox("Identify yourself:", collaborators)
    
    st.divider()
    st.subheader("Project Members")
    for user in collaborators:
        st.caption(f"👤 {user}")

# --- MAIN CHAT INTERFACE: FILE UPLOADS ---
with st.expander("📁 Upload Files / Photos from PC"):
    uploaded_file = st.file_uploader("Choose a file", type=["png", "jpg", "jpeg", "pdf", "zip", "docx", "mp4"])
    
    if uploaded_file is not None:
        if st.button(f"Upload and Send {uploaded_file.name}"):
            with st.spinner("Uploading to cloud..."):
                try:
                    file_ext = uploaded_file.name.split(".")[-1]
                    unique_name = f"{uuid.uuid4()}.{file_ext}"
                    storage_path = f"uploads/{unique_name}"
                    
                    # Upload to Supabase Buckets
                    supabase.storage.from_("chat-media").upload(
                        path=storage_path,
                        file=uploaded_file.getvalue(),
                        file_options={"content-type": uploaded_file.type}
                    )
                    
                    file_url = supabase.storage.from_("chat-media").get_public_url(storage_path)
                    
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

# --- FETCH & DISPLAY MESSAGES ---
try:
    res = supabase.table("messages").select("*").order("created_at", desc=True).limit(30).execute()
    messages = res.data
except Exception as e:
    st.error(f"Database error: {e}")
    messages = []

# Displaying the message loop
for m in reversed(messages):
    is_iot = m['user_name'] == "IoT-Sensor-Node"
    is_me = m['user_name'] == current_user
    
    # Use assistant style for others/bot, user style for self
    with st.chat_message("user" if is_me else "assistant"):
        
        if is_iot:
            # IoT Messages: Visible in chat with a blue highlight
            st.markdown("🤖 **IoT Live Feed**")
            st.info(m['content'])
        else:
            # Standard User Messages
            st.markdown(f"**{m['user_name']}**")
            st.write(m['content'])
        
        # Display attachments if they exist
        if m.get('file_url'):
            url = m['file_url']
            if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                st.image(url, use_container_width=True)
            else:
                st.link_button(f"🔗 View Attachment", url)

# --- SEND MESSAGE INPUT ---
if prompt := st.chat_input(f"Message as {current_user}..."):
    new_msg = {"content": prompt, "user_name": current_user, "file_url": None}
    supabase.table("messages").insert(new_msg).execute()
    st.rerun()
