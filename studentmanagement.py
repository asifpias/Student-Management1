import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- 1. SETTINGS & LINKS (Must be at the very top) ---
IELTS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1rxO0DSqjaevC5rvuCpwU0Z94jTZZ_PVt72Vnu44H5js/edit?usp=sharing"
APTIS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aNcZnUa5JhKE-IQ_xyJRzx7F9P5C2WbnDwO0lVQPWPU/edit?usp=sharing"

# --- 2. UPDATED AUTHENTICATION LOGIC ---
def get_gspread_client():
    """Initialize Google Sheets connection with google-auth"""
    try:
        # Define the scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Check if secrets exist
        if "gcp_service_account" in st.secrets:
            # Load credentials from Streamlit secrets
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # IMPORTANT: Ensure the private key is properly formatted
            # Some platforms might have already converted \n to actual newlines
            # If it's stored as a string with literal \n, we need to fix it
            if "private_key" in creds_dict:
                private_key = creds_dict["private_key"]
                # Try to detect and fix common formatting issues
                if "-----BEGIN PRIVATE KEY-----\\n" in private_key:
                    # Replace literal \n with actual newlines
                    private_key = private_key.replace("\\n", "\n")
                creds_dict["private_key"] = private_key
            
            # Create credentials using google-auth
            credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=scopes
            )
            
            # Authorize gspread client
            client = gspread.authorize(credentials)
            
            # Test the connection
            try:
                # Try to open a test sheet to verify credentials work
                client.list_spreadsheet_files(max_results=1)
                st.sidebar.success("✅ Connected to Google Sheets")
            except Exception as test_error:
                st.sidebar.error(f"Connection test failed: {test_error}")
                return None
                
            return client
        else:
            st.error("""
            ❌ Missing Google Cloud Service Account credentials.
            
            Please add your service account credentials to Streamlit Secrets:
            
            1. Go to Google Cloud Console
            2. Create a Service Account with Sheets & Drive API access
            3. Download the JSON key file
            4. Add it to your Streamlit secrets under `gcp_service_account`
            """)
            return None
            
    except Exception as e:
        st.error(f"🔥 Authentication failed: {str(e)}")
        st.info("""
        **Common fixes:**
        1. Ensure you've shared your Google Sheets with the service account email
        2. Check that the private key is correctly formatted with actual newlines
        3. Verify all required fields are in your secrets: 
           - type
           - project_id
           - private_key_id
           - private_key
           - client_email
           - client_id
           - auth_uri
           - token_uri
           - auth_provider_x509_cert_url
           - client_x509_cert_url
        """)
        return None

# Initialize the Google Client
gc = get_gspread_client()

# --- 3. DATABASE HELPERS (Updated with better error handling) ---
def get_spreadsheet(batch_type):
    """Get spreadsheet by type with error handling"""
    if gc is None:
        st.error("Not connected to Google Sheets. Please check authentication.")
        return None
    
    try:
        link = IELTS_SHEET_LINK if batch_type == "IELTS" else APTIS_SHEET_LINK
        spreadsheet = gc.open_by_url(link)
        
        # Test access by getting sheet names
        spreadsheet.worksheets()
        
        return spreadsheet
    except gspread.exceptions.APIError as e:
        error_msg = str(e)
        if "PERMISSION_DENIED" in error_msg or "notFound" in error_msg:
            st.error(f"""
            ❌ Permission denied for {batch_type} sheet.
            
            **To fix this:**
            1. Open your Google Sheet: {link}
            2. Click "Share" button
            3. Add your service account email as an editor
            4. Service account email: {st.secrets["gcp_service_account"]["client_email"]}
            """)
        else:
            st.error(f"❌ Google Sheets API Error: {error_msg}")
        return None
    except Exception as e:
        st.error(f"❌ Error opening {batch_type} sheet: {type(e).__name__}: {str(e)}")
        return None

def get_all_batch_names():
    """Get all batch names from both spreadsheets"""
    batches = []
    for batch_type in ["IELTS", "Aptis"]:
        ss = get_spreadsheet(batch_type)
        if ss:
            try:
                worksheets = ss.worksheets()
                batch_names = [ws.title for ws in worksheets]
                batches.extend(batch_names)
            except Exception as e:
                st.warning(f"Could not read worksheets from {batch_type} sheet: {e}")
    return sorted(set(batches))  # Remove duplicates and sort

# --- REST OF YOUR CODE REMAINS THE SAME ---
# (Keep your navigation and interface code as is)

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
