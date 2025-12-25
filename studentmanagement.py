import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# ============================
# PAGE CONFIGURATION
# ============================
st.set_page_config(
    page_title="Student Management System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================
# CONSTANTS
# ============================
IELTS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1rxO0DSqjaevC5rvuCpwU0Z94jTZZ_PVt72Vnu44H5js/edit?usp=sharing"
APTIS_SHEET_LINK = "https://docs.google.com/spreadsheets/d/1aNcZnUa5JhKE-IQ_xyJRzx7F9P5C2WbnDwO0lVQPWPU/edit?usp=sharing"

# ============================
# SESSION STATE INITIALIZATION
# ============================
if 'page' not in st.session_state:
    st.session_state.page = 'Home'
if 'gc' not in st.session_state:
    st.session_state.gc = None
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "disconnected"
if 'service_account_email' not in st.session_state:
    st.session_state.service_account_email = None

# ============================
# AUTHENTICATION MODULE - SIMPLIFIED
# ============================
def initialize_google_sheets():
    """Initialize Google Sheets client with SIMPLE connection test"""
    
    try:
        # Define required scopes
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Check for credentials in secrets
        if 'gcp_service_account' not in st.secrets:
            st.session_state.connection_status = "no_credentials"
            st.session_state.service_account_email = None
            return None
        
        # Load credentials from secrets
        creds_info = dict(st.secrets['gcp_service_account'])
        
        # Store service account email for sharing instructions
        if 'client_email' in creds_info:
            st.session_state.service_account_email = creds_info['client_email']
        
        # Fix private key formatting if needed
        if 'private_key' in creds_info:
            private_key = creds_info['private_key']
            # Handle different newline formats
            if '-----BEGIN PRIVATE KEY-----\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')
            elif '\\n' in private_key and '\n' not in private_key:
                private_key = private_key.replace('\\n', '\n')
            creds_info['private_key'] = private_key
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            creds_info,
            scopes=SCOPES
        )
        
        # Authorize gspread client
        gc = gspread.authorize(credentials)
        
        # SIMPLE CONNECTION TEST - Try to open a known sheet
        try:
            # Test with IELTS sheet first
            test_sheet = gc.open_by_url(IELTS_SHEET_LINK)
            # If we get here, connection is successful
            st.session_state.gc = gc
            st.session_state.connection_status = "connected"
            return gc
            
        except Exception as sheet_error:
            # Try Aptis sheet as fallback
            try:
                test_sheet = gc.open_by_url(APTIS_SHEET_LINK)
                st.session_state.gc = gc
                st.session_state.connection_status = "connected"
                return gc
            except:
                # Connection succeeded but can't access sheets
                st.session_state.gc = gc
                st.session_state.connection_status = "no_sheet_access"
                return gc
                
    except Exception as e:
        st.session_state.connection_status = "auth_error"
        return None

# Initialize Google Sheets connection
gc = initialize_google_sheets()

# ============================
# GOOGLE SHEETS UTILITIES
# ============================
def get_spreadsheet(batch_type):
    """Get spreadsheet by type"""
    if gc is None:
        return None
    
    try:
        link = IELTS_SHEET_LINK if batch_type == "IELTS" else APTIS_SHEET_LINK
        spreadsheet = gc.open_by_url(link)
        return spreadsheet
    except Exception as e:
        return None

def get_all_batch_names():
    """Get all unique batch names from both spreadsheets"""
    all_batches = []
    
    for batch_type in ["IELTS", "Aptis"]:
        spreadsheet = get_spreadsheet(batch_type)
        if spreadsheet:
            try:
                worksheets = spreadsheet.worksheets()
                for ws in worksheets:
                    all_batches.append({
                        "name": ws.title,
                        "type": batch_type,
                        "worksheet": ws
                    })
            except:
                continue
    
    return all_batches

def get_student_count(worksheet):
    """Get number of students in a batch"""
    try:
        all_values = worksheet.get_all_values()
        # Skip header row
        return max(0, len(all_values) - 1)
    except:
        return 0

# ============================
# NAVIGATION
# ============================
def navigate_to(page_name):
    """Navigate to different pages"""
    st.session_state.page = page_name
    st.rerun()

def show_navigation():
    """Display navigation buttons"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("🏠 Home", use_container_width=True):
            navigate_to('Home')
    
    with col2:
        if st.button("📁 Create Batch", use_container_width=True):
            navigate_to('Create Batch')
    
    with col3:
        if st.button("➕ Add Student", use_container_width=True):
            navigate_to('Add Student')
    
    with col4:
        if st.button("🔍 Find Student", use_container_width=True):
            navigate_to('Find Student')
    
    with col5:
        if st.button("📊 View Batches", use_container_width=True):
            navigate_to('View Batches')
    
    st.markdown("---")

# ============================
# SIDEBAR
# ============================
def show_sidebar():
    """Display sidebar with system info"""
    with st.sidebar:
        st.title("🎓 System Status")
        
        # Connection status
        status = st.session_state.connection_status
        
        if status == "connected":
            st.success("✅ Connected to Google Sheets")
            
            # Show batch stats
            try:
                all_batches = get_all_batch_names()
                if all_batches:
                    total_students = sum(get_student_count(batch["worksheet"]) for batch in all_batches)
                    st.metric("Total Batches", len(all_batches))
                    st.metric("Total Students", total_students)
            except:
                pass
                
        elif status == "no_sheet_access":
            st.error("🔐 Connected but no sheet access")
            if st.session_state.service_account_email:
                st.info(f"Share sheets with: `{st.session_state.service_account_email}`")
                
        elif status == "no_credentials":
            st.error("🔑 Missing credentials")
            
        elif status == "auth_error":
            st.error("❌ Authentication failed")
            
        else:
            st.warning("⚪ Not connected")
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("Quick Actions")
        
        if st.button("🔄 Refresh Connection", use_container_width=True):
            st.session_state.gc = None
            st.rerun()
        
        if st.button("📋 Setup Guide", use_container_width=True):
            navigate_to('Setup Guide')
        
        st.markdown("---")
        
        # Help
        with st.expander("Need Help?"):
            st.markdown("""
            1. **Share your sheets** with service account
            2. **Check credentials** format
            3. **Enable Sheets & Drive API**
            """)

# ============================
# PAGE: SETUP GUIDE
# ============================
def show_setup_guide():
    """Setup instructions page"""
    st.title("🛠️ Setup Guide")
    show_navigation()
    
    st.markdown("""
    ## Step-by-Step Setup Instructions
    
    ### 1. Google Cloud Console Setup
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Create a new project or select existing
    3. Enable **Google Sheets API** and **Google Drive API**
    
    ### 2. Create Service Account
    1. Navigate to **IAM & Admin → Service Accounts**
    2. Click **Create Service Account**
    3. Name it (e.g., "student-management-app")
    4. Click **Create and Continue**
    5. Grant **Editor** role
    6. Click **Continue** then **Done**
    
    ### 3. Create Service Account Key
    1. Click on your new service account
    2. Go to **Keys** tab
    3. Click **Add Key → Create New Key**
    4. Select **JSON** format
    5. Click **Create** (downloads automatically)
    
    ### 4. Share Your Google Sheets
    1. Open your IELTS Sheet: [IELTS Sheet](https://docs.google.com/spreadsheets/d/1rxO0DSqjaevC5rvuCpwU0Z94jTZZ_PVt72Vnu44H5js/edit?usp=sharing)
    2. Click **Share** button (top-right)
    3. Add this email as **Editor**: 
       ```
       {email}
       ```
    4. Repeat for Aptis Sheet: [Aptis Sheet](https://docs.google.com/spreadsheets/d/1aNcZnUa5JhKE-IQ_xyJRzx7F9P5C2WbnDwO0lVQPWPU/edit?usp=sharing)
    
    ### 5. Configure Streamlit Secrets
    
    **For Local Development:**
    1. Create `.streamlit/secrets.toml` file
    2. Copy the entire content of your downloaded JSON file
    3. Format it like this:
    
    ```toml
    [gcp_service_account]
    type = "service_account"
    project_id = "your-project-id"
    private_key_id = "your-private-key-id"
    private_key = '''-----BEGIN PRIVATE KEY-----
    YOUR-ACTUAL-PRIVATE-KEY-LINES-HERE
    -----END PRIVATE KEY-----'''
    client_email = "your-service-account@project.iam.gserviceaccount.com"
    client_id = "your-client-id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account"
    ```
    
    **For Streamlit Cloud:**
    1. Go to your app on [share.streamlit.io](https://share.streamlit.io)
    2. Click **Settings** (three dots menu)
    3. Go to **Secrets** tab
    4. Paste the same content
    
    ### 6. Test Connection
    1. Return to the Home page
    2. Click **🔄 Refresh Connection**
    3. Status should show **✅ Connected**
    
    ### Common Issues & Fixes
    
    **Issue: "Invalid JWT Signature"**
    - Ensure private_key has actual newlines, not \n strings
    - Use triple quotes ''' in toml file
    
    **Issue: "Permission Denied"**
    - Double-check you shared sheets with the correct email
    - Ensure service account has Editor access
    
    **Issue: "API not enabled"**
    - Enable Google Sheets API AND Google Drive API
    """.format(email=st.session_state.service_account_email or "your-service-account@project.iam.gserviceaccount.com"))

# ============================
# PAGE: HOME
# ============================
def show_home_page():
    """Display home page"""
    st.title("🎓 Student Management System")
    
    # Show connection status prominently
    status = st.session_state.connection_status
    
    if status == "connected":
        st.success("✅ System is fully operational!")
        
        # Quick stats
        try:
            all_batches = get_all_batch_names()
            if all_batches:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Batches", len(all_batches))
                with col2:
                    ielts_count = len([b for b in all_batches if b["type"] == "IELTS"])
                    st.metric("IELTS Batches", ielts_count)
                with col3:
                    aptis_count = len([b for b in all_batches if b["type"] == "Aptis"])
                    st.metric("Aptis Batches", aptis_count)
        except:
            pass
            
    elif status == "no_sheet_access":
        st.error("""
        ## 🔐 Connected but Can't Access Sheets
        
        **Please share your Google Sheets with:**
        ```
        {email}
        ```
        
        1. Open [IELTS Sheet]({ielts_link})
        2. Click **Share** button
        3. Add the email above as **Editor**
        4. Repeat for [Aptis Sheet]({aptis_link})
        5. Click **🔄 Refresh Connection** below
        """.format(
            email=st.session_state.service_account_email or "service-account-email",
            ielts_link=IELTS_SHEET_LINK,
            aptis_link=APTIS_SHEET_LINK
        ))
        
        if st.button("🔄 Refresh Connection", type="primary"):
            st.session_state.gc = None
            st.rerun()
            
    elif status == "no_credentials":
        st.error("""
        ## 🔑 Missing Credentials
        
        Please add your Google Service Account credentials.
        
        Go to **Setup Guide** page for complete instructions.
        """)
        
    else:
        st.warning("""
        ## ⚠️ Setup Required
        
        Please configure the system to connect to Google Sheets.
        
        Click **Setup Guide** in the sidebar for instructions.
        """)
    
    st.markdown("---")
    
    # Feature cards (only show if connected)
    if status == "connected":
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📁 Create New Batch
            Start a new IELTS or Aptis batch with custom settings.
            """)
            if st.button("Go to Create Batch →", use_container_width=True):
                navigate_to('Create Batch')
        
        with col2:
            st.markdown("""
            ### 👥 Add Students
            Add new students to existing batches with complete details.
            """)
            if st.button("Go to Add Student →", use_container_width=True):
                navigate_to('Add Student')
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("""
            ### 🔍 Search Students
            Find students by name, ID, email, or other criteria.
            """)
            if st.button("Go to Find Student →", use_container_width=True):
                navigate_to('Find Student')
        
        with col4:
            st.markdown("""
            ### 📊 View All Data
            See all batches, student counts, and export data.
            """)
            if st.button("Go to View Batches →", use_container_width=True):
                navigate_to('View Batches')
    
    # Setup guide link for non-connected states
    if status != "connected":
        st.markdown("---")
        st.info("""
        **Need help setting up?** 
        
        Click **Setup Guide** in the sidebar or the button below for step-by-step instructions.
        """)
        
        if st.button("📚 Open Setup Guide", type="primary", use_container_width=True):
            navigate_to('Setup Guide')

# ============================
# PAGE: CREATE BATCH (Simplified)
# ============================
def show_create_batch_page():
    """Display create batch page"""
    st.title("📁 Create New Batch")
    show_navigation()
    
    if st.session_state.connection_status != "connected":
        st.error("Please connect to Google Sheets first.")
        return
    
    with st.form("create_batch_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            batch_name = st.text_input("Batch Name*", placeholder="e.g., IELTS_Batch_1_2024")
            batch_type = st.selectbox("Batch Type*", ["IELTS", "Aptis"])
        
        with col2:
            year = st.selectbox("Year*", range(2024, 2031))
            batch_time = st.selectbox("Time Slot*", ["4:00 PM", "6:00 PM"])
        
        submitted = st.form_submit_button("Create Batch", type="primary")
        
        if submitted:
            if not batch_name:
                st.error("Please enter a batch name.")
                return
            
            # Check if batch already exists
            all_batches = get_all_batch_names()
            if any(b["name"] == batch_name for b in all_batches):
                st.error(f"Batch '{batch_name}' already exists!")
                return
            
            # Create the batch
            try:
                spreadsheet = get_spreadsheet(batch_type)
                if spreadsheet:
                    # Create worksheet
                    worksheet = spreadsheet.add_worksheet(title=batch_name, rows="100", cols="10")
                    
                    # Add headers
                    headers = ["Student Name", "Student ID", "Contact", "Email", "Batch", "Time", "Year", "Timestamp"]
                    worksheet.append_row(headers)
                    
                    st.success(f"✅ Batch '{batch_name}' created successfully!")
                    st.balloons()
                    
                    # Option to add students
                    if st.button("Add Students to This Batch"):
                        navigate_to('Add Student')
            except Exception as e:
                st.error(f"Error creating batch: {str(e)}")

# ============================
# PAGE: ADD STUDENT (Simplified)
# ============================
def show_add_student_page():
    """Display add student page"""
    st.title("➕ Add Student Information")
    show_navigation()
    
    if st.session_state.connection_status != "connected":
        st.error("Please connect to Google Sheets first.")
        return
    
    # Get available batches
    all_batches = get_all_batch_names()
    
    if not all_batches:
        st.warning("No batches found. Create a batch first.")
        return
    
    with st.form("student_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Student Name*")
            sid = st.text_input("Student ID*")
        
        with col2:
            contact = st.text_input("Contact*")
            email = st.text_input("Email*")
        
        # Batch selection
        batch_options = [f"{b['name']} ({b['type']})" for b in all_batches]
        selected_batch = st.selectbox("Select Batch*", batch_options)
        batch_name = selected_batch.split(" (")[0]
        
        time_slot = st.selectbox("Time Slot", ["4:00 PM", "6:00 PM"])
        
        submitted = st.form_submit_button("Add Student", type="primary")
        
        if submitted:
            # Validation
            if not all([name, sid, contact, email]):
                st.error("Please fill all required fields.")
                return
            
            # Find the selected batch
            selected_batch_info = None
            for batch in all_batches:
                if batch["name"] == batch_name:
                    selected_batch_info = batch
                    break
            
            if selected_batch_info:
                try:
                    # Prepare data
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    student_data = [name, sid, contact, email, batch_name, time_slot, datetime.now().year, timestamp]
                    
                    # Add to worksheet
                    worksheet = selected_batch_info["worksheet"]
                    worksheet.append_row(student_data)
                    
                    st.success(f"✅ Student '{name}' added successfully!")
                    
                except Exception as e:
                    st.error(f"Error adding student: {str(e)}")

# ============================
# PAGE: FIND STUDENT (Simplified)
# ============================
def show_find_student_page():
    """Display find student page"""
    st.title("🔍 Find Student")
    show_navigation()
    
    if st.session_state.connection_status != "connected":
        st.error("Please connect to Google Sheets first.")
        return
    
    search_query = st.text_input("Search by name, ID, email, or contact")
    
    if search_query:
        try:
            # Collect all data
            all_data = []
            for batch_type in ["IELTS", "Aptis"]:
                spreadsheet = get_spreadsheet(batch_type)
                if spreadsheet:
                    for ws in spreadsheet.worksheets():
                        try:
                            data = ws.get_all_records()
                            if data:
                                df = pd.DataFrame(data)
                                df['Batch'] = ws.title
                                df['Type'] = batch_type
                                all_data.append(df)
                        except:
                            continue
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                
                # Search across all columns
                mask = combined_df.astype(str).apply(
                    lambda x: x.str.contains(search_query, case=False, na=False)
                ).any(axis=1)
                
                results_df = combined_df[mask]
                
                if not results_df.empty:
                    st.success(f"Found {len(results_df)} student(s)")
                    st.dataframe(results_df, use_container_width=True)
                    
                    # Export option
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Results",
                        data=csv,
                        file_name=f"search_results_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No students found matching your search.")
            else:
                st.info("No student data available.")
                
        except Exception as e:
            st.error(f"Search error: {str(e)}")

# ============================
# PAGE: VIEW BATCHES (Simplified)
# ============================
def show_view_batches_page():
    """Display all batches"""
    st.title("📊 View All Batches")
    show_navigation()
    
    if st.session_state.connection_status != "connected":
        st.error("Please connect to Google Sheets first.")
        return
    
    try:
        all_batches = get_all_batch_names()
        
        if not all_batches:
            st.info("No batches found.")
            return
        
        # Create summary table
        batch_data = []
        for batch in all_batches:
            student_count = get_student_count(batch["worksheet"])
            batch_data.append({
                "Batch Name": batch["name"],
                "Type": batch["type"],
                "Student Count": student_count
            })
        
        df = pd.DataFrame(batch_data)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Batches", len(df))
        with col2:
            st.metric("Total Students", df["Student Count"].sum())
        with col3:
            st.metric("IELTS Batches", len(df[df["Type"] == "IELTS"]))
        
        # Display table
        st.dataframe(df, use_container_width=True)
        
        # Export option
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download Batch List",
            data=csv,
            file_name="batches_list.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"Error loading batches: {str(e)}")

# ============================
# MAIN APP
# ============================
def main():
    """Main application"""
    
    # Show sidebar
    show_sidebar()
    
    # Route pages
    if st.session_state.page == 'Home':
        show_home_page()
    elif st.session_state.page == 'Create Batch':
        show_create_batch_page()
    elif st.session_state.page == 'Add Student':
        show_add_student_page()
    elif st.session_state.page == 'Find Student':
        show_find_student_page()
    elif st.session_state.page == 'View Batches':
        show_view_batches_page()
    elif st.session_state.page == 'Setup Guide':
        show_setup_guide()
    else:
        show_home_page()

# ============================
# RUN APP
# ============================
if __name__ == "__main__":
    main()
