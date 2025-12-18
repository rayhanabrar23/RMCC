import streamlit as st
import base64

def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def apply_custom_style():
    bin_str_main = get_base64('background.png')
    bin_str_sidebar = get_base64('sidebar.png')
    
    bg_style = f"background-image: url('data:image/png;base64,{bin_str_main}');" if bin_str_main else ""
    side_style = f"background-image: url('data:image/png;base64,{bin_str_sidebar}'); background-size: cover;" if bin_str_sidebar else ""

    st.markdown(f"""
        <style>
        .stApp {{ {bg_style} background-size: cover; background-attachment: fixed; }}
        [data-testid="stSidebar"] {{ {side_style} }}
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{ color: white !important; }}
        </style>
        """, unsafe_allow_html=True)
