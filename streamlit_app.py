"""
Entry point for Streamlit Community Cloud, which looks for `streamlit_app.py` by default.
The dashboard itself is app.py; locally you can run either:
    streamlit run streamlit_app.py
    streamlit run app.py
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
