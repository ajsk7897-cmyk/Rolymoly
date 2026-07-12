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
    /* Force body to be dark so that image opacity creates a dark overlay effect */
    body, html {{
        background-color: #0E1117 !important;
    }}
    
    .bg-image {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url("data:{mime_type};base64,{encoded_image}");
        background-size: cover;
        background-position: center;
        z-index: -10;
        opacity: {1.0 - overlay_opacity};
        pointer-events: none;
    }}
    
    /* Make Streamlit's main app containers transparent so the background shows through */
    .stApp, [data-testid="stAppViewContainer"], .main {{
        background-color: transparent !important;
    }}
    
    [data-testid="stHeader"] {{
        background-color: transparent !important;
    }}

    /* Target specific text elements in the main container only */
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6, .main p, .main li, .main th, .main td, .main label, .main .stMarkdown {{
        color: #FFFFFF !important;
    }}
    
    /* Revert sidebar navigation tabs to black */
    [data-testid="stSidebarNav"] a, [data-testid="stSidebarNav"] span, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: #000000 !important;
    }}
    
    /* Revert button text and inputs to black */
    button, button *, input, textarea, select {{
        color: #000000 !important;
    }}
    </style>
    <div class="bg-image"></div>
    """
    st.markdown(html_str, unsafe_allow_html=True)
