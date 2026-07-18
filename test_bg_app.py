import streamlit as st
import base64

# encode images (1).jpg
with open("여름 이미지/images (1).jpg", "rb") as f:
    encoded_image = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-image: linear-gradient(rgba(14, 17, 23, 0.75), rgba(14, 17, 23, 0.75)), url("data:image/jpeg;base64,{encoded_image}") !important;
    background-size: cover !important;
    background-position: center !important;
}}
</style>
""", unsafe_allow_html=True)
st.write("Hello World")
