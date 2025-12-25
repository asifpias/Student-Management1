import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os

# --- 1. SETTINGS & LINKS (Must be at the very top) ---
IELTS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1rxO0DSqjaevC5rvuCpwU0Z94jTZZ_PVt72Vnu44H5js/edit?usp=sharing"
APTIS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aNcZnUa5JhKE-IQ_xyJRzx7F9P5C2WbnDwO0lVQPWPU/edit?usp=sharing"

# --- 2. AUTHENTICATION LOGIC ---
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", 
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            
            # Critical Fix for Private Key formatting
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
            client = gspread.authorize(creds)
            return client
        else:
            st.error("❌ 'gcp_service_account' not found in Secrets.")
            return None
    except Exception as e:
        st.error(f"⚠️ Authentication Failed: {e}")
        return None

# Initialize the Google Client
gc = get_gspread_client()

# --- 3. DATABASE HELPERS ---
def get_spreadsheet(batch_type):
    if gc is None:
        return None
    
    # Use the links defined at the top
    link = IELTS_SHEET_LINK if batch_type == "IELTS" else APTIS_SHEET_LINK
    
    try:
        return gc.open_by_url(link)
    except Exception as e:
        st.error(f"❌ Error opening {batch_type} sheet: {e}")
        return None

def get_all_batch_names():
    batches = []
    for t in ["IELTS", "Aptis"]:
        ss = get_spreadsheet(t)
        if ss:
            batches.extend([ws.title for ws in ss.worksheets()])
    return batches

# --- 4. NAVIGATION ---
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

def nav(target):
    st.session_state.page = target
    st.rerun()

def show_top_nav():
    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("🏠 Home"): nav('Home')
    with c2:
        if st.button("⬅️ Back"): nav('Home')
    st.markdown("---")

# --- 5. INTERFACES ---

if st.session_state.page == 'Home':
    st.title("🎓 Student Management App")
    st.subheader("Main Menu")
    
    if gc is None:
        st.error("Database connection is offline. Please check your Streamlit Secrets.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📁 Create Batch", use_container_width=True): nav('Create Batch')
    with col2:
        if st.button("➕ Add Student Info", use_container_width=True): nav('Add Student')
    with col3:
        if st.button("🔍 Find Student", use_container_width=True): nav('Find Student')

elif st.session_state.page == 'Create Batch':
    st.title("📁 Create New Batch")
    show_top_nav()
    
    with st.form("batch_form", clear_on_submit=True):
        b_name = st.text_input("Batch Name")
        b_type = st.selectbox("Type", ["IELTS", "Aptis"])
        year = st.selectbox("Year", range(2025, 2031))
        time = st.selectbox("Time", ["4pm", "6pm"])
        
        if st.form_submit_button("Create Now"):
            if b_name:
                ss = get_spreadsheet(b_type)
                if ss:
                    new_ws = ss.add_worksheet(title=b_name, rows="100", cols="10")
                    new_ws.append_row(["Student Name", "Student ID", "Contact", "Email", "Batch", "Time"])
                    st.success(f"✅ Success! Batch '{b_name}' created.")
            else:
                st.warning("Please enter a batch name.")

elif st.session_state.page == 'Add Student':
    st.title("➕ Add Student Information")
    show_top_nav()
    all_batches = get_all_batch_names()
    
    if not all_batches:
        st.info("No batches found. Create a batch first.")
    else:
        with st.form("std_form", clear_on_submit=True):
            name = st.text_input("Name of Student")
            sid = st.text_input("Student ID")
            cont = st.text_input("Contact")
            mail = st.text_input("Email")
            bat = st.selectbox("Batch", all_batches)
            tm = st.selectbox("Time", ["4pm", "6pm"])
            
            if st.form_submit_button("Submit Information"):
                success = False
                for t in ["IELTS", "Aptis"]:
                    ss = get_spreadsheet(t)
                    try:
                        ws = ss.worksheet(bat)
                        ws.append_row([name, sid, cont, mail, bat, tm])
                        st.success(f"✅ Added {name} to {bat}!")
                        success = True
                        break
                    except: continue
                if not success: st.error("Could not find the selected batch.")

elif st.session_state.page == 'Find Student':
    st.title("🔍 Find Student")
    show_top_nav()
    
    search_q = st.text_input("Search Name or ID")
    batch_filter = st.selectbox("Filter by Batch", ["All"] + get_all_batch_names())
    
    all_data = []
    for t in ["IELTS", "Aptis"]:
        ss = get_spreadsheet(t)
        if ss:
            for ws in ss.worksheets():
                if batch_filter == "All" or ws.title == batch_filter:
                    df = pd.DataFrame(ws.get_all_records())
                    if not df.empty: all_data.append(df)
    
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        if search_q:
            final_df = final_df[final_df.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)]
        st.dataframe(final_df, use_container_width=True)
    else:
        st.info("No records found.")
