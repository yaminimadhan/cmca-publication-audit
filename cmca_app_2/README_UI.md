\# Streamlit UI Enhancements – CMCA Publication Audit 



This README explains the front-end development work done for the \*\*Streamlit user interface (Stage 2 UI)\*\* of the CMCA LLM Publication Audit project.  

It focuses on layout, visual design, and mock data preview, not backend integration.



---



\## Overview  

The Streamlit app allows users to:

\- Upload PDFs and preview parsed metadata  

\- View summary charts (CMCA Yes / No, Top Instruments)  

\- Browse publication records from the API or mock dataset  

\- Display a visual banner that represents CMCA branding  



---



\## UI Enhancements Summary  

\*\*Branch:\*\* `ui-enhancements`  

\*\*Goal:\*\* Improve usability and visual appearance of the dashboard  



\*\*Key updates:\*\*  

1\. Added CMCA image banner with centered text overlay  

2\. Improved page spacing and divider structure  

3\. Created `modules/ui\_theme.py` for consistent styling  

4\. Added `prepare\_assets.py` to process and convert image assets  

5\. Used mock mode (`DEV\_MODE = 1`) for testing without backend calls  



---



\## Run in Mock Mode (Frontend Only)  



```bash

\# Windows PowerShell

$env:DEV\_MODE="1"

streamlit run app.py --server.port 8510



