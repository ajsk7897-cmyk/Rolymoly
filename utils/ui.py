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

    html_str = f"""
    <style>
    .bg-image {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url("data:{mime_type};base64,{encoded_image}");
        background-size: cover;
        background-position: center;
        z-index: -999;
        opacity: {1.0 - overlay_opacity};
    }}
    /* Make Streamlit's main app container transparent so the background shows through */
    .stApp {{
        background-color: rgba(0,0,0,0) !important;
    }}
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0) !important;
    }}
    </style>
    <div class="bg-image"></div>
    """
    st.markdown(html_str, unsafe_allow_html=True)
