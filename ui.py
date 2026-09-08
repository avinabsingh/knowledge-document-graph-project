import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Fact Knowledge Layer", layout="wide")
st.title("📄 Fact Knowledge Layer")

# --- Sidebar: Upload ---
st.sidebar.header("1. Upload Documents")
uploaded_file = st.sidebar.file_uploader("Upload a PDF", type=["pdf"])

if st.sidebar.button("Process PDF") and uploaded_file:
    with st.spinner("Parsing and Extracting Facts..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        res = requests.post(f"{API_URL}/upload", files=files)
        if res.status_code == 200:
            st.sidebar.success(f"Extracted {res.json()['facts_extracted']} facts!")
        else:
            st.sidebar.error("Upload failed.")

# --- Main Area: View Facts ---
st.header("2. Knowledge Base")
if st.button("Refresh Facts"):
    res = requests.get(f"{API_URL}/facts")
    if res.status_code == 200:
        facts = res.json().get("facts", [])
        if facts:
            df = pd.DataFrame(facts)
            st.dataframe(df[["id", "category", "entity", "metric_or_attribute", "value", "context", "source_filename"]])
        else:
            st.info("No facts extracted yet.")

# --- Main Area: Cross-Document Analysis ---
st.header("3. Cross-Document Auditor")
if st.button("Run Analysis"):
    with st.spinner("Analyzing relationships across documents..."):
        res = requests.get(f"{API_URL}/analyze")
        if res.status_code == 200:
            data = res.json()
            st.write(f"**Found {data['clusters_found']} overlapping clusters.**")
            
            for comp in data.get("comparisons", []):
                rel = comp["relationship"]
                color = "green" if rel == "CORROBORATION" else "red" if rel == "CONTRADICTION" else "orange"
                
                st.markdown(f"### :{color}[{rel}]")
                if comp.get("reconciliation_dimension"):
                    st.write(f"**Dimension:** {comp['reconciliation_dimension']}")
                st.write(f"**Reasoning:** {comp['explanation']}")
                st.caption(f"Comparing Fact ID {comp['fact_a_id']} and Fact ID {comp['fact_b_id']}")
                st.divider()