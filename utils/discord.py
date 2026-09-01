
import requests
import streamlit as st
import logging

logger = logging.getLogger(__name__)

def send_discord_webhook(message: str, webhook_url: str = None) -> bool:
    """
    디스코드 웹훅으로 메시지 전송
    """
    if not webhook_url:
        if "discord_webhook_url" in st.secrets:
            webhook_url = st.secrets["discord_webhook_url"]
        else:
            logger.warning("Discord webhook URL is not provided.")
            return False
            
    try:
        data = {"content": message}
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            return True
        else:
            logger.error(f"Failed to send discord webhook: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"Discord webhook error: {e}")
        return False
