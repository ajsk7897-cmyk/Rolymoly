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
    /* Apply background directly to Streamlit's main container to preserve original layout */
    [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(14, 17, 23, {overlay_opacity}), rgba(14, 17, 23, {overlay_opacity})), url("data:{mime_type};base64,{encoded_image}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}
    
    [data-testid="stHeader"] {{
        background-color: transparent !important;
    }}

    /* Force global text to white for readability */
    h1, h2, h3, h4, h5, h6, p, span, label, li, a, th, td {{
        color: #FFFFFF !important;
    }}
    
    /* Exceptions: Force sidebar text to black */
    [data-testid="stSidebar"], [data-testid="stSidebar"] * {{
        color: #000000 !important;
    }}
    
    /* Exceptions: Force buttons to black (e.g., 로그인, 비밀번호 변경, 티어 최신화) */
    button, button * {{
        color: #000000 !important;
    }}
    
    /* Exceptions: Force inputs to black */
    input, textarea, select, [data-baseweb="input"] * {{
        color: #000000 !important;
    }}
    
    /* Exceptions: Force dropdown list items to black */
    ul[role="listbox"] *, div[role="listbox"] *, li[role="option"] * {{
        color: #000000 !important;
    }}
    
    </style>
    """
    st.markdown(html_str, unsafe_allow_html=True)
