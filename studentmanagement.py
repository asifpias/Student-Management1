import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# --- GOOGLE SHEETS LINKS ---
IELTS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1rxO0DSqjaevC5rvuCpwU0Z94jTZZ_PVt72Vnu44H5js/edit?usp=sharing"
APTIS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aNcZnUa5JhKE-IQ_xyJRzx7F9P5C2WbnDwO0lVQPWPU/edit?usp=sharing"

# --- API SETUP ---
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    # Try to get credentials from Streamlit Secrets (Recommended for Cloud)
    # If running locally, it will look for 'credentials.json' in the folder
    try:
        if "gcp_service_account" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name("dc8c1fade39e4047c349adb0fabbe89e8ba5a2d2", scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

client = get_gspread_client()

# --- DATABASE HELPERS ---

def get_spreadsheet(batch_type):
    if not client: return None
    link = IELTS_SHEET_LINK if batch_type == "IELTS" else APTIS_SHEET_LINK
    return client.open_by_url(link)

def get_all_batch_names():
    batches = []
    for t in ["IELTS", "Aptis"]:
        ss = get_spreadsheet(t)
        if ss:
            batches.extend([ws.title for ws in ss.worksheets()])
    return batches

# --- NAVIGATION ---
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

def nav(target):
    st.session_state.page = target
    st.rerun()

# --- INTERFACES ---

# Global Header for all pages
if st.session_state.page != 'Home':
    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("🏠 Home"): nav('Home')
    with c2:
        if st.button("⬅️ Back"): nav('Home')
    st.markdown("---")

# PAGE: HOME
if st.session_state.page == 'Home':
    st.title("🎓 Student Management App")
    st.subheader("Main Menu")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📁 Create Batch", use_container_width=True): nav('Create Batch')
    with col2:
        if st.button("➕ Add Student Information", use_container_width=True): nav('Add Student')
    with col3:
        if st.button("🔍 Find Student", use_container_width=True): nav('Find Student')

# PAGE: CREATE BATCH
elif st.session_state.page == 'Create Batch':
    st.title("📁 Create New Batch")
    with st.form("batch_form", clear_on_submit=True):
        b_name = st.text_input("Batch Name")
        b_type = st.selectbox("Type", ["IELTS", "Aptis"])
        year = st.selectbox("Year", range(2024, 2031))
        time = st.selectbox("Time", ["4pm", "6pm"])
        
        c1, c2 = st.columns(2)
        with c1:
            if st.form_submit_button("Create Now"):
                ss = get_spreadsheet(b_type)
                if ss:
                    new_ws = ss.add_worksheet(title=b_name, rows="100", cols="10")
                    new_ws.append_row(["Student Name", "Student ID", "Contact", "Email", "Batch", "Time"])
                    st.success(f"✅ Success! Batch '{b_name}' created in {b_type} Sheets.")
        with c2:
            if st.form_submit_button("Reset"):
                st.rerun()

# PAGE: ADD STUDENT
elif st.session_state.page == 'Add Student':
    st.title("➕ Add Student Information")
    all_batches = get_all_batch_names()
    
    with st.form("std_form", clear_on_submit=True):
        name = st.text_input("Name of Student")
        sid = st.text_input("Student ID")
        cont = st.text_input("Contact")
        mail = st.text_input("Email")
        bat = st.selectbox("Batch", all_batches)
        tm = st.selectbox("Time", ["4pm", "6pm"])
        
        if st.form_submit_button("Submit Information"):
            found = False
            for t in ["IELTS", "Aptis"]:
                ss = get_spreadsheet(t)
                try:
                    ws = ss.worksheet(bat)
                    ws.append_row([name, sid, cont, mail, bat, tm])
                    st.success(f"✅ Success! {name} has been added to {bat}.")
                    found = True; break
                except: continue
            if not found: st.error("Batch worksheet not found.")

# PAGE: FIND STUDENT
elif st.session_state.page == 'Find Student':
    st.title("🔍 Find Student")
    
    search = st.text_input("Search by Name or Student ID")
    b_filter = st.selectbox("Filter by Batch", ["All"] + get_all_batch_names())
    
    # Data aggregation
    all_recs = []
    for t in ["IELTS", "Aptis"]:
        ss = get_spreadsheet(t)
        if ss:
            for ws in ss.worksheets():
                if b_filter == "All" or ws.title == b_filter:
                    df_temp = pd.DataFrame(ws.get_all_records())
                    all_recs.append(df_temp)
    
    if all_recs:
        main_df = pd.concat(all_recs, ignore_index=True)
        if search:
            main_df = main_df[main_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        st.dataframe(main_df, use_container_width=True)
        
        st.markdown("---")
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("➕ Add Student"): nav('Add Student')
        with bc2:
            st.button("📝 Edit Selected")
        with bc3:
            st.button("🗑️ Delete Selected")
    else:
        st.warning("No data found in the sheets.")

st.sidebar.caption("Connected to Google Sheets API")
