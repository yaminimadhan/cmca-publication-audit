import streamlit as st
import base64
from pathlib import Path


# === Helper to encode any image ===
def _b64(path: str) -> str:
    with open(Path(path), "rb") as f:
        return base64.b64encode(f.read()).decode()


# === Full-page global background (used once in app.py) ===
def apply_global_background(st, img_path: str, overlay_rgba=(255, 255, 255, 0.92)):
    r, g, b, a = overlay_rgba
    b64 = _b64(img_path)
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
      background: url("data:image/jpeg;base64,{b64}") center/cover no-repeat fixed;
    }}
    .block-container {{
      background: rgba({r},{g},{b},{a});
      border-radius: 12px;
      padding: 1.2rem 1.4rem;
    }}
    </style>
    """, unsafe_allow_html=True)


# === Section-specific background (e.g., for microprobe card headers) ===
def section_with_background(st, img_path: str, title: str, subtitle: str = "", inner_opacity=0.82):
    b64 = _b64(img_path)
    st.markdown(f"""
    <div style="
      background: url('data:image/jpeg;base64,{b64}') center/cover no-repeat;
      border-radius: 12px; padding: 28px; margin: 12px 0;">
      <div style="background: rgba(255,255,255,{inner_opacity});
                  padding: 14px 16px; border-radius: 10px;
                  display:inline-block;">
        <h3 style="margin:0;">{title}</h3>
        <p style="margin:6px 0 0;">{subtitle}</p>
      </div>
    </div>
    """, unsafe_allow_html=True)


# === Simple background (used by app.py) ===
def apply_background(image_path: str):
    """Apply a static background image to the Streamlit app using CSS."""
    try:
        img_path = Path(image_path)
        if not img_path.exists():
            st.warning(f"Background image not found: {image_path}")
            return

        with open(img_path, "rb") as f:
            img_bytes = f.read()
        encoded = base64.b64encode(img_bytes).decode()

        css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Failed to apply background: {e}")
