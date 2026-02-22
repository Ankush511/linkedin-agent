import streamlit as st
import requests
import json
import base64
import boto3
import pandas as pd

st.set_page_config(page_title="LinkedIn Command Center", page_icon="🚀", layout="wide")

# --- CONFIG & SECRETS ---
GITHUB_PAT = st.secrets["GITHUB_PAT"]
REPO_OWNER = st.secrets["REPO_OWNER"]
REPO_NAME = st.secrets["REPO_NAME"]
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]

HEADERS = {
    "Authorization": f"token {GITHUB_PAT}",
    "Accept": "application/vnd.github.v3+json"
}

st.title("🚀 LinkedIn Agent Command Center")

tab1, tab2, tab3 = st.tabs(["✍️ Generate Post", "📊 Dashboard", "🧠 Brainstormer"])

# TAB 1: GENERATION CONTROLS
with tab1:
    st.markdown("### Force the Agent to write a specific post")
    st.markdown("Leave blank to let the agent auto-brainstorm based on your history.")
    
    topic_input = st.text_input("Custom Topic:", placeholder="e.g., Sliding Window Pattern in Python")

    if st.button("🚀 Generate Draft Now", type="primary"):
        with st.spinner("Waking up GitHub Actions..."):
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/daily_draft.yml/dispatches"
            payload = {
                "ref": "main",
                "inputs": {"custom_topic": topic_input}
            }
            resp = requests.post(url, headers=HEADERS, json=payload)
            
            if resp.status_code == 204:
                st.success("✅ Workflow triggered! Your draft will be ready in the Dashboard in ~60 seconds.")
            else:
                st.error(f"❌ Failed to trigger workflow. Status: {resp.status_code}")
                st.write(resp.text)

# TAB 2: THE DASHBOARD
with tab2:
    st.markdown("### 📋 Awaiting Your Approval")
    
    issues_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues?labels=draft&state=open"
    issues_resp = requests.get(issues_url, headers=HEADERS)
    
    if issues_resp.status_code == 200:
        issues = issues_resp.json()
        if not issues:
            st.info("🎉 No drafts waiting for approval! You're all caught up.")
        for issue in issues:
            issue_num = issue['number']
            with st.expander(f"📝 Draft: {issue['title']}", expanded=True):
                
                # Editable Text Area
                updated_body = st.text_area(
                    "Edit your post below:", 
                    value=issue['body'], 
                    height=250, 
                    key=f"text_{issue_num}"
                )
                
                col1, col2 = st.columns([1, 1])
                
                # Button 1: Save Edits to GitHub Issue
                with col1:
                    if st.button("💾 Save Edits", key=f"save_{issue_num}"):
                        patch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}"
                        payload = {"body": updated_body}
                        patch_resp = requests.patch(patch_url, headers=HEADERS, json=payload)
                        
                        if patch_resp.status_code == 200:
                            st.success("✅ Edits saved to GitHub!")
                        else:
                            st.error("❌ Failed to save edits.")
                
                # Button 2: Publish to LinkedIn
                with col2:
                    if st.button("🚀 Publish to LinkedIn", key=f"pub_{issue_num}", type="primary"):
                        patch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}"
                        requests.patch(patch_url, headers=HEADERS, json={"body": updated_body})
                        
                        label_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_num}/labels"
                        label_payload = {"labels": ["publish"]}
                        label_resp = requests.post(label_url, headers=HEADERS, json=label_payload)
                        
                        if label_resp.status_code == 200:
                            st.success("🚀 Publishing sequence initiated! GitHub Actions is posting it now.")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to initiate publish. {label_resp.text}")
    else:
        st.error("Could not fetch drafts from GitHub.")
    
    st.markdown("---")
    st.markdown("### 📚 Content Archive")
    
    history_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/topic_history.json"
    hist_resp = requests.get(history_url, headers=HEADERS)
    
    if hist_resp.status_code == 200:
        content_b64 = hist_resp.json()['content']
        decoded_content = base64.b64decode(content_b64).decode('utf-8')
        history_data = json.loads(decoded_content)
        
        df = pd.DataFrame(history_data)
        if not df.empty:
            df = df.sort_values(by="date", ascending=False).reset_index(drop=True)
            st.metric("Total Posts Published", len(df))
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No history file found yet. It will appear here after your first published post.")

# TAB 3: BRAINSTORMING ASSISTANT
with tab3:
    st.markdown("### Let Claude generate 5 rapid-fire ideas.")
    theme = st.text_input("Enter a broad theme:", placeholder="e.g., Graph Algorithms, GenAI APIs, Clean Code")
    
    if st.button("🧠 Brainstorm Ideas"):
        if not theme:
            st.warning("Please enter a theme first.")
        else:
            with st.spinner("Thinking..."):
                try:
                    bedrock = boto3.client(
                        'bedrock-runtime', 
                        region_name='us-east-1',
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                    )
                    prompt = f"Give me 5 highly specific, actionable LinkedIn post ideas about '{theme}' for backend developers. Output ONLY a numbered list."
                    payload = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                    }
                    response = bedrock.invoke_model(
                        modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0", 
                        body=json.dumps(payload)
                    )
                    result = json.loads(response['body'].read())
                    
                    st.success("Done! Copy your favorite and paste it into the Generate tab.")
                    st.markdown(result['content'][0]['text'])
                except Exception as e:
                    st.error(f"AWS Error: {e}")