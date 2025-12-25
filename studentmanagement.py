import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import json

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
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "disconnected"

# ============================
# AUTHENTICATION MODULE
# ============================
def initialize_google_sheets():
    """Initialize and return Google Sheets client with robust error handling"""
    
    # If already initialized and recent, reuse
    if st.session_state.gc and st.session_state.last_update:
        time_diff = datetime.now() - st.session_state.last_update
        if time_diff.total_seconds() < 300:  # 5 minutes
            return st.session_state.gc
    
    try:
        # Define required scopes
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Check for credentials in secrets
        if 'gcp_service_account' not in st.secrets:
            st.session_state.connection_status = "no_credentials"
            return None
        
        # Load credentials from secrets
        creds_info = dict(st.secrets['gcp_service_account'])
        
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
        
        # Test connection with a simple API call (FIXED: removed max_results)
        try:
            # Try to list spreadsheet files (simple test)
            gc.list_spreadsheet_files()
            
            # Store in session state
            st.session_state.gc = gc
            st.session_state.last_update = datetime.now()
            st.session_state.connection_status = "connected"
            
            return gc
            
        except Exception as test_error:
            st.session_state.connection_status = "test_failed"
            return None
            
    except Exception as e:
        st.session_state.connection_status = "error"
        return None

# Initialize Google Sheets connection
gc = initialize_google_sheets()

# ============================
# GOOGLE SHEETS UTILITIES
# ============================
def get_spreadsheet(batch_type):
    """Get spreadsheet by type with comprehensive error handling"""
    if gc is None:
        st.session_state.connection_status = "disconnected"
        return None
    
    try:
        # Select correct spreadsheet link
        link = IELTS_SHEET_LINK if batch_type == "IELTS" else APTIS_SHEET_LINK
        
        # Open spreadsheet
        spreadsheet = gc.open_by_url(link)
        
        # Verify access by checking worksheets
        spreadsheet.worksheets()
        
        return spreadsheet
        
    except gspread.exceptions.APIError as api_error:
        error_msg = str(api_error)
        
        if "PERMISSION_DENIED" in error_msg:
            if 'gcp_service_account' in st.secrets:
                service_account_email = st.secrets["gcp_service_account"]["client_email"]
                st.error(f"""
                ## 🔐 Permission Denied
                
                **To fix this:**
                1. Open your Google Sheet: [{batch_type} Sheet]({link})
                2. Click the **"Share"** button (top-right corner)
                3. Add this email as an **Editor**: 
                   ```
                   {service_account_email}
                   ```
                4. Click **"Send"**
                """)
        elif "notFound" in error_msg:
            st.error(f"Spreadsheet link for {batch_type} might be incorrect or deleted.")
        else:
            st.error(f"Google Sheets API Error: {error_msg}")
        return None
        
    except Exception as e:
        st.error(f"Error accessing {batch_type} spreadsheet: {type(e).__name__}: {str(e)}")
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
            except Exception as e:
                continue
    
    return all_batches

def get_student_count(worksheet):
    """Get number of students in a batch (excluding header)"""
    try:
        all_values = worksheet.get_all_values()
        # Count non-empty rows after header
        count = 0
        for i, row in enumerate(all_values):
            if i == 0:  # Skip header
                continue
            if any(cell.strip() for cell in row):  # Check if row has any non-empty cells
                count += 1
        return count
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
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            navigate_to('Home')
    
    with col2:
        if st.button("📁 Create Batch", use_container_width=True, key="nav_create"):
            navigate_to('Create Batch')
    
    with col3:
        if st.button("➕ Add Student", use_container_width=True, key="nav_add"):
            navigate_to('Add Student')
    
    with col4:
        if st.button("🔍 Find Student", use_container_width=True, key="nav_find"):
            navigate_to('Find Student')
    
    with col5:
        if st.button("📊 View Batches", use_container_width=True, key="nav_view"):
            navigate_to('View Batches')
    
    st.markdown("---")

# ============================
# SIDEBAR
# ============================
def show_sidebar():
    """Display sidebar with system info and tools"""
    with st.sidebar:
        st.title("🎓 System Info")
        
        # Connection status with color coding
        status_colors = {
            "connected": "🟢",
            "disconnected": "🔴",
            "no_credentials": "🟡",
            "test_failed": "🟠",
            "error": "🔴"
        }
        
        status_text = {
            "connected": "Connected to Google Sheets",
            "disconnected": "Not Connected",
            "no_credentials": "Missing Credentials",
            "test_failed": "Connection Test Failed",
            "error": "Connection Error"
        }
        
        status = st.session_state.connection_status
        status_icon = status_colors.get(status, "⚪")
        status_message = status_text.get(status, "Unknown Status")
        
        if status == "connected":
            st.success(f"{status_icon} {status_message}")
            if 'gcp_service_account' in st.secrets:
                service_email = st.secrets["gcp_service_account"]["client_email"]
                st.caption(f"Service Account: `{service_email[:20]}...`")
        else:
            st.error(f"{status_icon} {status_message}")
        
        st.markdown("---")
        
        # Quick Stats (only if connected)
        st.subheader("📊 Quick Stats")
        if gc and status == "connected":
            try:
                all_batches = get_all_batch_names()
                total_batches = len(all_batches)
                total_students = sum(get_student_count(batch["worksheet"]) for batch in all_batches)
                
                st.metric("Total Batches", total_batches)
                st.metric("Total Students", total_students)
                
                # IELTS vs Aptis breakdown
                ielts_batches = len([b for b in all_batches if b["type"] == "IELTS"])
                aptis_batches = len([b for b in all_batches if b["type"] == "Aptis"])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("IELTS", ielts_batches)
                with col2:
                    st.metric("Aptis", aptis_batches)
                    
            except Exception as e:
                st.info("Stats not available")
        else:
            st.info("Connect to see stats")
        
        st.markdown("---")
        
        # Tools
        st.subheader("🛠️ Tools")
        
        if st.button("🔄 Refresh Connection", use_container_width=True):
            st.session_state.gc = None
            st.session_state.connection_status = "disconnected"
            st.rerun()
        
        if st.button("📋 Debug Info", use_container_width=True):
            navigate_to('Debug')
        
        st.markdown("---")
        
        # Help section
        with st.expander("❓ Need Help?"):
            st.markdown("""
            **Quick Fixes:**
            1. **Can't access sheet?** 
               - Share it with service account email
            2. **Private key error?**
               - Ensure newlines are actual \\n characters
            3. **Data not saving?**
               - Check internet connection
               - Verify sheet permissions
            
            **Support:** admin@example.com
            """)

# ============================
# PAGE: HOME
# ============================
def show_home_page():
    """Display home page"""
    st.title("🎓 Student Management System")
    st.markdown("Welcome to the comprehensive student management platform")
    
    # Show connection status banner
    if st.session_state.connection_status != "connected":
        if st.session_state.connection_status == "no_credentials":
            st.error("""
            ## 🔑 Missing Credentials Setup
            
            Please add your Google Service Account credentials to Streamlit Secrets.
            
            **Steps:**
            1. Go to Google Cloud Console
            2. Create Service Account with Sheets & Drive API access
            3. Download JSON key file
            4. Add to `.streamlit/secrets.toml` file
            """)
        else:
            st.warning("⚠️ System is not connected to Google Sheets. Some features may be limited.")
    
    # Feature cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
        <h3>📁 Create New Batch</h3>
        <ul>
        <li>Create IELTS or Aptis batches</li>
        <li>Set batch time (4pm or 6pm)</li>
        <li>Automatic spreadsheet creation</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Create Batch →", key="home_create", use_container_width=True):
            navigate_to('Create Batch')
    
    with col2:
        st.markdown("""
        <div style='padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
        <h3>👥 Student Management</h3>
        <ul>
        <li>Add new students to batches</li>
        <li>Update student information</li>
        <li>Search and filter students</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Manage Students →", key="home_manage", use_container_width=True):
            navigate_to('Add Student')
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("""
        <div style='padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
        <h3>🔍 Search & Analytics</h3>
        <ul>
        <li>Search by name or ID</li>
        <li>Filter by batch</li>
        <li>Export data to CSV</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Search Students →", key="home_search", use_container_width=True):
            navigate_to('Find Student')
    
    with col4:
        st.markdown("""
        <div style='padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
        <h3>📊 View All Data</h3>
        <ul>
        <li>View all batches</li>
        <li>Student counts per batch</li>
        <li>Batch statistics</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Batches →", key="home_view", use_container_width=True):
            navigate_to('View Batches')
    
    # Quick actions for disconnected state
    if not gc:
        st.markdown("---")
        st.subheader("🚀 Quick Setup")
        
        with st.expander("Setup Instructions"):
            st.markdown("""
            ### To get started:
            
            1. **Create Google Cloud Project**
               - Go to [Google Cloud Console](https://console.cloud.google.com/)
               - Create new project or select existing
            
            2. **Enable APIs**
               - Enable **Google Sheets API**
               - Enable **Google Drive API**
            
            3. **Create Service Account**
               - IAM & Admin → Service Accounts
               - Create new service account
               - Grant Editor role
            
            4. **Create Key**
               - Click on service account
               - Keys → Add Key → JSON
               - Download JSON file
            
            5. **Share Google Sheets**
               - Open your IELTS and Aptis sheets
               - Click Share
               - Add service account email as Editor
            
            6. **Add to Streamlit**
               - In `.streamlit/secrets.toml`:
               ```
               [gcp_service_account]
               type = "service_account"
               project_id = "your-project-id"
               private_key_id = "your-key-id"
               private_key = "-----BEGIN PRIVATE KEY-----\\nyour-key\\n-----END PRIVATE KEY-----\\n"
               client_email = "your-email@project.iam.gserviceaccount.com"
               client_id = "your-client-id"
               auth_uri = "https://accounts.google.com/o/oauth2/auth"
               token_uri = "https://oauth2.googleapis.com/token"
               auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
               client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-email"
               ```
            """)
    
    # Recent activity (if connected)
    if gc and st.session_state.connection_status == "connected":
        st.markdown("---")
        st.subheader("📈 Recent Activity")
        
        try:
            all_batches = get_all_batch_names()
            if all_batches:
                # Show recent batches
                recent_batches = all_batches[:3]  # Show first 3
                
                for batch in recent_batches:
                    student_count = get_student_count(batch["worksheet"])
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.text(f"📚 {batch['name']}")
                        with col2:
                            st.text(f"Type: {batch['type']}")
                        with col3:
                            st.text(f"Students: {student_count}")
                        st.progress(min(student_count / 50, 1.0))
                        st.markdown("---")
            else:
                st.info("No batches found. Create your first batch to get started!")
        except:
            st.info("Unable to load recent activity")

# ============================
# PAGE: CREATE BATCH
# ============================
def show_create_batch_page():
    """Display create batch page"""
    st.title("📁 Create New Batch")
    show_navigation()
    
    if not gc:
        st.error("🔌 Please connect to Google Sheets first.")
        st.info("Go to Home page for setup instructions")
        return
    
    with st.form("create_batch_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            batch_name = st.text_input("Batch Name*", placeholder="e.g., IELTS_Batch_1_2024", 
                                      help="Unique name for this batch")
            batch_type = st.selectbox("Batch Type*", ["IELTS", "Aptis"])
        
        with col2:
            year = st.selectbox("Year*", range(2024, 2031))
            batch_time = st.selectbox("Time Slot*", ["4:00 PM", "6:00 PM", "Other"])
        
        description = st.text_area("Batch Description (Optional)", 
                                  placeholder="Enter any additional notes about this batch...",
                                  height=100)
        
        st.markdown("**Required fields***")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            submitted = st.form_submit_button("🚀 Create Batch", type="primary", use_container_width=True)
        with col3:
            if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                st.rerun()
        
        if submitted:
            if not batch_name:
                st.error("Please enter a batch name.")
                return
            
            # Validate batch name doesn't exist
            all_batches = get_all_batch_names()
            existing_names = [b["name"] for b in all_batches]
            
            if batch_name in existing_names:
                st.error(f"❌ Batch '{batch_name}' already exists. Please choose a different name.")
                return
            
            # Create the batch
            with st.spinner(f"Creating {batch_name}..."):
                try:
                    spreadsheet = get_spreadsheet(batch_type)
                    if spreadsheet:
                        # Create new worksheet
                        new_worksheet = spreadsheet.add_worksheet(
                            title=batch_name, 
                            rows="1000", 
                            cols="20"
                        )
                        
                        # Add headers
                        headers = [
                            "Timestamp", "Student ID", "Full Name", "Contact Number", 
                            "Email Address", "Batch", "Time", "Year", "Status", "Notes"
                        ]
                        new_worksheet.append_row(headers)
                        
                        # Format header row (bold)
                        new_worksheet.format('A1:J1', {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8, 'alpha': 0.3}
                        })
                        
                        st.success(f"✅ Batch '{batch_name}' created successfully!")
                        st.balloons()
                        
                        # Show success details
                        with st.expander("📋 Batch Details", expanded=True):
                            st.markdown(f"""
                            **Batch Information:**
                            - **Name:** {batch_name}
                            - **Type:** {batch_type}
                            - **Year:** {year}
                            - **Time:** {batch_time}
                            - **Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                            
                            **Next Steps:**
                            1. Go to **'Add Student'** page to add students
                            2. Share the sheet link with team members
                            3. Monitor progress from the **'View Batches'** page
                            """)
                        
                        # Auto-refresh after 3 seconds
                        time.sleep(3)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Failed to create batch: {str(e)}")

# ============================
# PAGE: ADD STUDENT
# ============================
def show_add_student_page():
    """Display add student page"""
    st.title("➕ Add Student Information")
    show_navigation()
    
    if not gc:
        st.error("🔌 Please connect to Google Sheets first.")
        return
    
    # Get all available batches
    all_batches = get_all_batch_names()
    
    if not all_batches:
        st.warning("📭 No batches found. Please create a batch first.")
        if st.button("📁 Create New Batch"):
            navigate_to('Create Batch')
        return
    
    # Create two-column layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("student_form", clear_on_submit=True):
            st.subheader("👤 Student Details")
            
            col1, col2 = st.columns(2)
            with col1:
                student_name = st.text_input("Full Name*", placeholder="John Smith")
                student_id = st.text_input("Student ID*", placeholder="STU2024001")
            with col2:
                contact_number = st.text_input("Contact Number*", placeholder="+1234567890")
                email = st.text_input("Email Address*", placeholder="john@example.com")
            
            st.subheader("📚 Batch Information")
            
            # Group batches by type
            ielts_batches = [b for b in all_batches if b["type"] == "IELTS"]
            aptis_batches = [b for b in all_batches if b["type"] == "Aptis"]
            
            batch_type = st.radio("Select Batch Type:", ["IELTS", "Aptis"], horizontal=True)
            
            if batch_type == "IELTS":
                available_batches = ielts_batches
            else:
                available_batches = aptis_batches
            
            if not available_batches:
                st.warning(f"📭 No {batch_type} batches available. Create one first.")
                batch_name = None
            else:
                batch_options = [f"{b['name']} ({b['type']})" for b in available_batches]
                selected_batch = st.selectbox("Select Batch*", batch_options)
                batch_name = selected_batch.split(" (")[0]
            
            additional_notes = st.text_area("Additional Notes", 
                                          placeholder="Any special requirements or notes...",
                                          height=80)
            
            st.markdown("**Required fields***")
            
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("💾 Save Student", type="primary", use_container_width=True)
            with col2:
                if st.form_submit_button("🗑️ Clear Form", use_container_width=True):
                    st.rerun()
    
    with col2:
        st.subheader("👁️ Preview")
        st.info("""
        **Guidelines:**
        - All * fields are required
        - Student ID should be unique
        - Email for communication
        - Double-check contact number
        """)
        
        # Live preview
        if student_name or student_id:
            st.markdown("### 📄 Record Preview")
            preview_data = {
                "Name": student_name if student_name else "Not entered",
                "Student ID": student_id if student_id else "Not entered",
                "Contact": contact_number if contact_number else "Not entered",
                "Email": email if email else "Not entered",
                "Batch": batch_name if batch_name else "Not selected",
                "Type": batch_type if batch_name else "Not selected"
            }
            
            for key, value in preview_data.items():
                st.text(f"{key}: {value}")
    
    # Handle form submission
    if submitted:
        # Validation
        missing_fields = []
        if not student_name: missing_fields.append("Full Name")
        if not student_id: missing_fields.append("Student ID")
        if not contact_number: missing_fields.append("Contact Number")
        if not email: missing_fields.append("Email Address")
        if not batch_name: missing_fields.append("Batch")
        
        if missing_fields:
            st.error(f"Please fill all required fields: {', '.join(missing_fields)}")
            return
        
        # Find the selected batch
        selected_batch_info = None
        for batch in all_batches:
            if batch["name"] == batch_name:
                selected_batch_info = batch
                break
        
        if not selected_batch_info:
            st.error("Selected batch not found.")
            return
        
        try:
            # Prepare student data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            student_data = [
                timestamp,
                student_id,
                student_name,
                contact_number,
                email,
                batch_name,
                batch_type,
                datetime.now().year,
                "ACTIVE",
                additional_notes if additional_notes else "No notes"
            ]
            
            # Add to worksheet
            worksheet = selected_batch_info["worksheet"]
            worksheet.append_row(student_data)
            
            # Success message
            st.success(f"✅ Student '{student_name}' added to '{batch_name}'!")
            st.balloons()
            
            # Show summary
            with st.expander("📋 Added Record Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Student Info:**
                    - Name: {student_name}
                    - ID: {student_id}
                    - Contact: {contact_number}
                    - Email: {email}
                    """)
                with col2:
                    st.markdown(f"""
                    **Batch Info:**
                    - Batch: {batch_name}
                    - Type: {batch_type}
                    - Time Added: {timestamp}
                    - Status: ACTIVE
                    """)
            
            # Option to add another student
            if st.button("➕ Add Another Student", use_container_width=True):
                st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to add student: {str(e)}")

# ============================
# PAGE: FIND STUDENT
# ============================
def show_find_student_page():
    """Display find student page"""
    st.title("🔍 Find Student")
    show_navigation()
    
    if not gc:
        st.error("🔌 Please connect to Google Sheets first.")
        return
    
    # Search interface
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input("🔎 Search by Name, ID, Email, or Contact", 
                                    placeholder="Enter search term...",
                                    help="Search across all student fields")
    
    with col2:
        search_type = st.selectbox("Search In", 
                                 ["All Fields", "Name Only", "ID Only", "Email Only", "Contact Only"])
    
    with col3:
        if st.button("Search", type="primary", use_container_width=True):
            st.session_state.search_triggered = True
    
    # Filter options
    with st.expander("🔧 Advanced Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            all_batches = get_all_batch_names()
            batch_names = ["All Batches"] + [b["name"] for b in all_batches]
            batch_filter = st.selectbox("Filter by Batch", batch_names)
        
        with col2:
            type_filter = st.selectbox("Filter by Type", 
                                      ["All Types", "IELTS", "Aptis"])
        
        with col3:
            year_filter = st.selectbox("Filter by Year", 
                                      ["All Years"] + list(range(2020, 2031)))
    
    # Check if search was triggered
    if hasattr(st.session_state, 'search_triggered') and st.session_state.search_triggered:
        with st.spinner("Searching student records..."):
            try:
                # Collect all student data
                all_students = []
                
                for batch in all_batches:
                    try:
                        worksheet = batch["worksheet"]
                        data = worksheet.get_all_records()
                        
                        for row in data:
                            # Skip empty rows and header-like rows
                            if not row.get("Student ID") and not row.get("Full Name"):
                                continue
                            
                            # Add batch info to each row
                            row["Batch_Name"] = batch["name"]
                            row["Batch_Type"] = batch["type"]
                            all_students.append(row)
                    except:
                        continue
                
                if not all_students:
                    st.info("📭 No student records found in the system.")
                    return
                
                # Convert to DataFrame
                df = pd.DataFrame(all_students)
                
                # Apply filters
                if batch_filter != "All Batches":
                    df = df[df["Batch_Name"] == batch_filter]
                
                if type_filter != "All Types":
                    df = df[df["Batch_Type"] == type_filter]
                
                if year_filter != "All Years":
                    if "Year" in df.columns:
                        df = df[df["Year"].astype(str) == str(year_filter)]
                
                # Apply search
                if search_query:
                    search_lower = search_query.lower()
                    
                    if search_type == "Name Only":
                        mask = df["Full Name"].astype(str).str.lower().str.contains(search_lower)
                    elif search_type == "ID Only":
                        mask = df["Student ID"].astype(str).str.lower().str.contains(search_lower)
                    elif search_type == "Email Only":
                        mask = df["Email Address"].astype(str).str.lower().str.contains(search_lower)
                    elif search_type == "Contact Only":
                        mask = df["Contact Number"].astype(str).str.lower().str.contains(search_lower)
                    else:  # All Fields
                        mask = df.astype(str).apply(
                            lambda x: x.str.lower().str.contains(search_lower)
                        ).any(axis=1)
                    
                    df = df[mask]
                
                # Display results
                if len(df) > 0:
                    st.success(f"✅ Found {len(df)} student(s)")
                    
                    # Select columns to display
                    display_cols = ["Timestamp", "Student ID", "Full Name", "Contact Number", 
                                   "Email Address", "Batch_Name", "Batch_Type", "Status", "Notes"]
                    
                    # Filter to available columns
                    available_cols = [col for col in display_cols if col in df.columns]
                    display_df = df[available_cols]
                    
                    # Show data with pagination
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=400,
                        hide_index=True
                    )
                    
                    # Export option
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        csv = display_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name=f"students_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        if st.button("🔄 New Search", use_container_width=True):
                            st.session_state.search_triggered = False
                            st.rerun()
                    
                    with col3:
                        if st.button("📊 Show Stats", use_container_width=True):
                            with st.expander("📈 Search Statistics"):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Found", len(df))
                                with col2:
                                    unique_batches = df["Batch_Name"].nunique()
                                    st.metric("Unique Batches", unique_batches)
                                with col3:
                                    active_count = len(df[df.get("Status", "") == "ACTIVE"])
                                    st.metric("Active Students", active_count)
                
                else:
                    st.warning("🔍 No students found matching your search criteria.")
                    if st.button("🔄 Clear Search", use_container_width=True):
                        st.session_state.search_triggered = False
                        st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Search failed: {str(e)}")
    
    else:
        # Initial state - show search tips
        st.info("""
        **Search Tips:**
        - Enter any student detail to search
        - Use advanced filters for precise results
        - Search is case-insensitive
        - Results can be exported as CSV
        """)

# ============================
# PAGE: VIEW BATCHES
# ============================
def show_view_batches_page():
    """Display all batches with statistics"""
    st.title("📊 View All Batches")
    show_navigation()
    
    if not gc:
        st.error("🔌 Please connect to Google Sheets first.")
        return
    
    try:
        all_batches = get_all_batch_names()
        
        if not all_batches:
            st.info("📭 No batches found. Create your first batch!")
            if st.button("📁 Create New Batch", use_container_width=True):
                navigate_to('Create Batch')
            return
        
        # Create DataFrame for display
        batch_data = []
        for batch in all_batches:
            student_count = get_student_count(batch["worksheet"])
            batch_data.append({
                "Batch Name": batch["name"],
                "Type": batch["type"],
                "Student Count": student_count,
                "Worksheet": batch["worksheet"]
            })
        
        df = pd.DataFrame(batch_data).sort_values("Student Count", ascending=False)
        
        # Display statistics
        st.subheader("📈 Batch Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Batches", len(df))
        with col2:
            st.metric("IELTS Batches", len(df[df["Type"] == "IELTS"]))
        with col3:
            st.metric("Aptis Batches", len(df[df["Type"] == "Aptis"]))
        with col4:
            st.metric("Total Students", df["Student Count"].sum())
        
        # Interactive table
        st.subheader("📋 All Batches")
        
        # Search and filter
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("Search batches by name...")
        with col2:
            type_filter = st.selectbox("Filter by type", ["All", "IELTS", "Aptis"])
        
        # Apply filters
        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[filtered_df["Batch Name"].str.contains(search_term, case=False, na=False)]
        if type_filter != "All":
            filtered_df = filtered_df[filtered_df["Type"] == type_filter]
        
        # Display table
        st.dataframe(
            filtered_df[["Batch Name", "Type", "Student Count"]],
            use_container_width=True,
            height=400,
            column_config={
                "Student Count": st.column_config.NumberColumn(
                    "Students",
                    help="Number of students in batch",
                    format="%d"
                )
            }
        )
        
        # Batch details section
        st.subheader("🔍 Batch Details")
        
        if len(filtered_df) > 0:
            selected_batch = st.selectbox(
                "Select a batch to view details:",
                filtered_df["Batch Name"].tolist()
            )
            
            if selected_batch:
                selected_row = filtered_df[filtered_df["Batch Name"] == selected_batch].iloc[0]
                worksheet = selected_row["Worksheet"]
                
                try:
                    student_data = worksheet.get_all_records()
                    if student_data:
                        # Remove empty rows and header-like rows
                        clean_data = []
                        for row in student_data:
                            if row.get("Student ID") or row.get("Full Name"):
                                clean_data.append(row)
                        
                        if clean_data:
                            students_df = pd.DataFrame(clean_data)
                            
                            # Show batch summary
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Students in Batch", len(students_df))
                            with col2:
                                active_students = len(students_df[students_df.get("Status", "") == "ACTIVE"])
                                st.metric("Active Students", active_students)
                            with col3:
                                if "Year" in students_df.columns:
                                    unique_years = students_df["Year"].nunique()
                                    st.metric("Unique Years", unique_years)
                            
                            # Show student table
                            st.write(f"**Students in {selected_batch}:**")
                            display_cols = ["Student ID", "Full Name", "Contact Number", "Email Address", "Status"]
                            available_cols = [col for col in display_cols if col in students_df.columns]
                            
                            st.dataframe(
                                students_df[available_cols],
                                use_container_width=True,
                                height=300
                            )
                            
                            # Export option
                            csv = students_df.to_csv(index=False)
                            st.download_button(
                                label="📥 Export Batch Data",
                                data=csv,
                                file_name=f"{selected_batch}_students.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.info("📭 No students in this batch yet.")
                    else:
                        st.info("📭 No student data available for this batch.")
                except Exception as e:
                    st.warning(f"Could not load student data: {str(e)}")
        
        # Batch actions
        st.subheader("⚡ Quick Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📥 Export All Batches", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="all_batches.csv",
                    mime="text/csv",
                    key="export_all"
                )
        
    except Exception as e:
        st.error(f"❌ Failed to load batches: {str(e)}")

# ============================
# PAGE: DEBUG
# ============================
def show_debug_page():
    """Debug page for troubleshooting"""
    st.title("🐛 Debug Information")
    show_navigation()
    
    st.subheader("Connection Status")
    st.write(f"Status: {st.session_state.connection_status}")
    st.write(f"Last Update: {st.session_state.last_update}")
    
    if gc:
        st.success("✅ Google Sheets client is initialized")
        
        # Test connection with actual API call
        if st.button("🔌 Test Connection"):
            with st.spinner("Testing connection..."):
                try:
                    # Try to list files
                    files = gc.list_spreadsheet_files()
                    st.success(f"✅ Connection successful! Found {len(files)} spreadsheets")
                    
                    # Try to open your specific sheets
                    st.subheader("Sheet Access Test")
                    
                    for sheet_name, sheet_link in [("IELTS", IELTS_SHEET_LINK), ("Aptis", APTIS_SHEET_LINK)]:
                        try:
                            sheet = gc.open_by_url(sheet_link)
                            worksheets = sheet.worksheets()
                            st.success(f"✅ {sheet_name} Sheet: Access OK ({len(worksheets)} worksheets)")
                        except Exception as e:
                            st.error(f"❌ {sheet_name} Sheet: {str(e)}")
                            
                except Exception as e:
                    st.error(f"❌ Connection test failed: {str(e)}")
    
    # Credentials info (masked)
    st.subheader("Credentials Info")
    if 'gcp_service_account' in st.secrets:
        creds = st.secrets['gcp_service_account']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Client Email:**")
            st.code(creds.get('client_email', 'Not found'))
        with col2:
            st.write("**Project ID:**")
            st.code(creds.get('project_id', 'Not found'))
        
        st.write("**Private Key Preview:**")
        private_key = creds.get('private_key', '')
        if private_key:
            # Show first and last 100 chars
            preview = private_key[:100] + "..." + private_key[-100:] if len(private_key) > 200 else private_key
            st.code(preview)
            
            # Check for newline issues
            if "\\n" in private_key and "\n" not in private_key:
                st.warning("⚠️ Private key contains literal '\\n' strings instead of actual newlines")
            else:
                st.success("✅ Private key format looks good")
    else:
        st.error("❌ No credentials found in secrets")

# ============================
# MAIN APP ROUTER
# ============================
def main():
    """Main application router"""
    
    # Show sidebar
    show_sidebar()
    
    # Route to correct page
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
    elif st.session_state.page == 'Debug':
        show_debug_page()
    else:
        show_home_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; padding: 20px;'>
        🎓 Student Management System v2.0 • Built with Streamlit • 
        <a href='https://docs.streamlit.io' target='_blank' style='color: gray;'>Documentation</a>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================
# RUN THE APPLICATION
# ============================
if __name__ == "__main__":
    main()
