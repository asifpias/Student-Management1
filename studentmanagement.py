import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURATION & GOOGLE API SETUP ---
# REMINDER: Add your credentials.json file to the project folder
# and ensure you share your Google Sheets with the 'client_email' in that JSON.

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    # REMINDER: Replace 'credentials.json' with your actual API key filename
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("dc8c1fade39e4047c349adb0fabbe89e8ba5a2d2", scope)
        return gspread.authorize(creds)
    except:
        return None

client = get_gspread_client()

# --- HELPER FUNCTIONS ---

def get_sheet_by_type(batch_type):
    """Returns the correct Google Spreadsheet based on Type."""
    if not client: return None
    sheet_name = "IELTS Batches" if batch_type == "IELTS" else "Aptis Batches"
    try:
        return client.open(sheet_name)
    except:
        st.error(f"Spreadsheet '{sheet_name}' not found. Please create it and share with API email.")
        return None

def get_all_batches():
    """Fetches names of all worksheets from both main sheets."""
    batches = []
    for t in ["IELTS", "Aptis"]:
        ss = get_sheet_by_type(t)
        if ss:
            batches.extend([ws.title for ws in ss.worksheets()])
    return batches

# --- NAVIGATION LOGIC ---

if 'page' not in st.session_state:
    st.session_state.page = 'Home'

def go_to(page_name):
    st.session_state.page = page_name

# --- INTERFACE: HOME ---

if st.session_state.page == 'Home':
    st.title("🎓 Student Management App")
    st.subheader("Welcome, please select an option:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📁 Create Batch", use_container_width=True): go_to('Create Batch')
    with col2:
        if st.button("➕ Add Student Info", use_container_width=True): go_to('Add Student')
    with col3:
        if st.button("🔍 Find Student", use_container_width=True): go_to('Find Student')
    
    st.markdown("---")
    st.caption("Made by Asif Iqbal Pias")

# --- INTERFACE: CREATE BATCH ---

elif st.session_state.page == 'Create Batch':
    st.title("📁 Create New Batch")
    
    if st.button("🏠 Home"): go_to('Home')
    
    with st.form("batch_form"):
        batch_name = st.text_input("Batch Name")
        batch_type = st.selectbox("Type", ["IELTS", "Aptis"])
        year = st.selectbox("Year", range(2024, 2031))
        time = st.selectbox("Time", ["4pm", "6pm"])
        
        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("Create Now")
        with c2:
            reset = st.form_submit_button("Reset")

    if submitted:
        ss = get_sheet_by_type(batch_type)
        if ss:
            try:
                # Create new worksheet
                new_ws = ss.add_worksheet(title=batch_name, rows="100", cols="10")
                # Set Headers
                headers = ["Student Name", "Student ID", "Contact", "Email", "Batch", "Time"]
                new_ws.append_row(headers)
                st.success(f"Batch '{batch_name}' created successfully in {batch_type} Batches!")
            except Exception as e:
                st.error(f"Error: {e}")

# --- INTERFACE: ADD STUDENT ---

elif st.session_state.page == 'Add Student':
    st.title("➕ Add Student Information")
    
    cols = st.columns(2)
    with cols[0]:
        if st.button("🏠 Home"): go_to('Home')
    with cols[1]:
        if st.button("⬅️ Back"): go_to('Home')

    all_existing_batches = get_all_batches()
    
    with st.form("student_form"):
        name = st.text_input("Name of Student")
        std_id = st.text_input("Student ID")
        contact = st.text_input("Contact")
        email = st.text_input("Email")
        batch = st.selectbox("Batch", all_existing_batches)
        time = st.selectbox("Time", ["4pm", "6pm"])
        
        if st.form_submit_button("Save Student"):
            # Logic to find which Spreadsheet contains this batch
            found = False
            for t in ["IELTS", "Aptis"]:
                ss = get_sheet_by_type(t)
                try:
                    ws = ss.worksheet(batch)
                    ws.append_row([name, std_id, contact, email, batch, time])
                    st.success("Student added successfully!")
                    found = True
                    break
                except: continue
            if not found: st.error("Could not find batch worksheet.")

# --- INTERFACE: FIND STUDENT ---

elif st.session_state.page == 'Find Student':
    st.title("🔍 Find Student")
    
    if st.button("🏠 Home"): go_to('Home')
    
    # Search and Filter
    search_q = st.text_input("Search by Name or Student ID")
    batch_filter = st.selectbox("Sort by Batch", ["All"] + get_all_batches())
    
    # Data Retrieval
    all_data = []
    for t in ["IELTS", "Aptis"]:
        ss = get_sheet_by_type(t)
        if ss:
            for ws in ss.worksheets():
                if batch_filter == "All" or ws.title == batch_filter:
                    data = ws.get_all_records()
                    all_data.extend(data)
    
    df = pd.DataFrame(all_data)
    
    if not df.empty:
        # Search Filtering
        if search_q:
            df = df[df['Student Name'].str.contains(search_q, case=False) | 
                    df['Student ID'].astype(str).str.contains(search_q)]
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found.")

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ Add Student"): go_to('Add Student')
    with c2:
        st.button("📝 Edit (Cloud Only)")
    with c3:
        st.button("🗑️ Delete (Cloud Only)")
