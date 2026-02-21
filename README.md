
# 🤖 LinkedIn AI Agent (Human-in-the-Loop)

A fully automated, serverless AI agent that generates highly technical LinkedIn posts about Backend Engineering, System Design, and Generative AI. 

Built with **Python**, **AWS Bedrock (Claude)**, and **GitHub Actions**, this agent uses a "Human-in-the-Loop" architecture. It drafts the content, creates a GitHub Issue for review, notifies the user via email, and securely publishes to LinkedIn only after manual approval.

## 🏗 Architecture

The system relies on two separate GitHub Actions workflows to ensure human oversight before anything goes live.

1. **The Drafter (`draft_agent.py`)**: 
   * Runs daily on a cron schedule.
   * Reads `topic_history.json` to avoid repeating past topics.
   * Prompts AWS Bedrock (Claude) to write a technical, human-sounding draft.
   * Creates a GitHub Issue containing the draft text.
   * Sends an email notification to the user.

2. **The Publisher (`publish_agent.py`)**:
   * Triggered automatically when the user adds a `publish` label to the GitHub Issue.
   * Parses the final, human-edited text from the issue.
   * Pushes the content to the user's personal feed via the LinkedIn API.
   * Updates `topic_history.json` and closes the issue.

## 🛠 Prerequisites

To run this agent, you will need access to the following services:

* **AWS Account:** Access to Amazon Bedrock with Anthropic Claude models enabled. An IAM User with `bedrock:InvokeModel` permissions.
* **LinkedIn Developer App:** An app with the `Share on LinkedIn` product enabled, and an OAuth 2.0 Member Access Token with the `w_member_social` scope.
* **Gmail Account:** An App Password generated for sending email notifications.
* **GitHub Repository:** For hosting the code, running Actions, and managing Issues.

## 🔐 Environment Variables & Secrets

Add the following as **Repository Secrets** in GitHub (`Settings > Secrets and variables > Actions`):

| Secret Name | Description |
| :--- | :--- |
| `AWS_ACCESS_KEY_ID` | AWS IAM Access Key for Bedrock. |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM Secret Key for Bedrock. |
| `LINKEDIN_ACCESS_TOKEN` | OAuth 2.0 token generated from LinkedIn Developer Portal. |
| `LINKEDIN_USER_URN` | Your unique LinkedIn Member URN (e.g., `urn:li:person:abc123XYZ`). |
| `EMAIL_USER` | The Gmail address sending the notification. |
| `EMAIL_PASS` | The 16-character Gmail App Password. |
| `EMAIL_RECEIVER` | The email address receiving the notification. |

*Note: The `GITHUB_TOKEN` is provided automatically by GitHub Actions. Ensure your workflow permissions are set to "Read and write permissions" in Repo Settings > Actions > General.*

## 🚀 Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Ankush511/linkedin-agent.git](https://github.com/Ankush511/linkedin-agent.git)
   cd linkedin-agent

```

2. **Install dependencies:**
```bash
pip install -r requirements.txt

```


*(Requires: `boto3`, `requests`, `PyGithub`, `python-dotenv`)*
3. **Configure GitHub Actions:**
Ensure the `.github/workflows` directory contains both `daily_draft.yml` and `publish.yml`.
4. **Initialize Memory:**
The agent will automatically create `topic_history.json` on its first successful publish to ensure it never repeats a topic.

## 💡 Daily Workflow (How to use)

1. **Wait for Notification:** The Drafter bot runs at the scheduled cron time and emails you a link to a new GitHub Issue.
2. **Review & Edit:** Click the link, read the draft in the GitHub Issue, and edit the text directly if you want to make manual adjustments.
3. **Approve:** On the right sidebar of the GitHub Issue, add the label **`publish`**.
4. **Deploy:** The Publisher bot instantly wakes up, posts the text to your LinkedIn profile, updates the memory file, and closes the issue.


```
