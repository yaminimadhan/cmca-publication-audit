import base64
from pathlib import Path

# helper to turn an image into base64 so Streamlit can show it as CSS 
def _b64(path: str) -> str:
    with open(Path(path), "rb") as f:
        return base64.b64encode(f.read()).decode()

# full-page background (used once in app.py) 
def apply_global_background(st, img_path: str, overlay_rgba=(255,255,255,0.88)):
    r,g,b,a = overlay_rgba
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

# small header section with its own background (for Microprobe etc.)
def section_with_background(st, img_path: str, title: str, subtitle: str="", inner_opacity=0.82):
    b64 = _b64(img_path)
    st.markdown(f"""
    <div style="
      background: url('data:image/jpeg;base64,{b64}') center/cover no-repeat;
      border-radius: 12px; padding: 28px; margin: 12px 0;">
      <div style="background: rgba(255,255,255,{inner_opacity}); padding: 14px 16px; border-radius: 10px; display:inline-block;">
        <h3 style="margin:0;">{title}</h3>
        <p style="margin:6px 0 0;">{subtitle}</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
