import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

def get_slack_client():
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token or "paste_" in token:
        return None
    return WebClient(token=token)

def is_slack_connected() -> bool:
    token = os.getenv("SLACK_BOT_TOKEN", "")
    return bool(token) and "paste_" not in token

def get_slack_channels(limit=10) -> list:
    client = get_slack_client()
    if not client: return ["Error: Slack SLACK_BOT_TOKEN is not configured."]
    try:
        response = client.conversations_list(limit=limit, exclude_archived=True)
        return [{"id": c["id"], "name": c["name"]} for c in response.get("channels", [])]
    except SlackApiError as e:
        logger.error(f"Slack auth error: {e.response['error']}")
        return [f"Slack API Error: {e.response['error']} - Tell the user to grant channels:read scope."]

def read_slack_messages(channel_id: str, limit=10) -> list:
    client = get_slack_client()
    if not client: return ["Error: Slack SLACK_BOT_TOKEN is not configured."]
    try:
        response = client.conversations_history(channel=channel_id, limit=limit)
        return [{"user": m.get("user"), "text": m.get("text")} for m in response.get("messages", [])]
    except SlackApiError as e:
        logger.error(f"Slack history error: {e.response['error']}")
        return [f"Slack API Error: {e.response['error']} - Tell the user to invite the bot to the channel or grant channels:history."]

def send_slack_message(channel_id: str, text: str) -> bool:
    client = get_slack_client()
    if not client: return False
    try:
        client.chat_postMessage(channel=channel_id, text=text)
        return True
    except SlackApiError as e:
        logger.error(f"Slack post error: {e.response['error']}")
        return False
