import streamlit as st
import requests
import json

st.set_page_config(page_title="LinkedIn AI Agent", page_icon="🤖")

st.title("🤖 LinkedIn Agent Control Panel")
st.markdown("Enter a specific topic below to force the agent to draft a post about it. If you leave it blank and press the button, it will brainstorm its own topic.")

GITHUB_PAT = st.secrets["GITHUB_PAT"]
REPO_OWNER = st.secrets["REPO_OWNER"]
REPO_NAME = st.secrets["REPO_NAME"]
WORKFLOW_FILE = "daily_draft.yml"

topic_input = st.text_input("Enter custom topic (e.g., 'Optimizing API Latency in Python'):")

if st.button("🚀 Generate Draft Now"):
    with st.spinner("Waking up the agent..."):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
        
        headers = {
            "Authorization": f"token {GITHUB_PAT}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "ref": "main",
            "inputs": {
                "custom_topic": topic_input
            }
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 204:
            st.success("✅ Success! The agent is drafting your post. Check your email in about 30 seconds.")
        else:
            st.error(f"❌ Failed to trigger workflow. Status: {response.status_code}")
            st.write(response.text)