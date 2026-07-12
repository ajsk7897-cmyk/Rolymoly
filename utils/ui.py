import base64
import streamlit as st
import os

def set_background(image_filename, overlay_opacity=0.75):
    ext = os.path.splitext(image_filename)[1].lower()
    if ext == '.gif':
        mime_type = 'image/gif'
    elif ext in ['.jpg', '.jpeg']:
        mime_type = 'image/jpeg'
    elif ext == '.png':
        mime_type = 'image/png'
    else:
        mime_type = 'image/jpeg'
        
    image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "여름 이미지", image_filename)
    if not os.path.exists(image_path):
        return
        
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode()
        
    css = f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background-image: linear-gradient(rgba(14, 17, 23, {overlay_opacity}), rgba(14, 17, 23, {overlay_opacity})), url("data:{mime_type};base64,{encoded_image}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
