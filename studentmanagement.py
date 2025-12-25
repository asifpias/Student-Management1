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
            st.error("""
            ## 🔑 Missing Google Cloud Credentials
            
            **To fix this:**
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select existing one
            3. Enable **Google Sheets API** and **Google Drive API**
            4. Create a Service Account
            5. Generate a JSON key file
            6. Add the content to Streamlit Cloud Secrets:
            
            ```toml
            [gcp_service_account]
            type = "service_account"
            project_id = "your-project-id"
            private_key_id = "your-private-key-id"
            private_key = "-----BEGIN PRIVATE KEY-----\\nyour-actual-private-key\\n-----END PRIVATE KEY-----\\n"
            client_email = "your-service-account@project.iam.gserviceaccount.com"
            client_id = "your-client-id"
            auth_uri = "https://accounts.google.com/o/oauth2/auth"
            token_uri = "https://oauth2.googleapis.com/token"
            auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
            client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account"
            ```
            
            **IMPORTANT:** Replace `\\n` with actual newlines in the private_key
            """)
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
        
        # Test connection
        try:
            # Simple API call to verify connection
            gc.list_spreadsheet_files(max_results=1)
            
            # Store in session state
            st.session_state.gc = gc
            st.session_state.last_update = datetime.now()
            
            return gc
            
        except Exception as test_error:
            st.error(f"Connection test failed: {str(test_error)}")
            return None
            
    except Exception as e:
        st.error(f"Authentication Error: {str(e)}")
        st.info("""
        **Common Issues & Solutions:**
        1. **Invalid JWT Signature**: Ensure private_key has actual newlines, not \\n strings
        2. **Permission Denied**: Share your Google Sheets with the service account email
        3. **API Not Enabled**: Enable Google Sheets API & Drive API in Google Cloud Console
        """)
        return None

# Initialize Google Sheets connection
gc = initialize_google_sheets()

# ============================
# GOOGLE SHEETS UTILITIES
# ============================
def get_spreadsheet(batch_type):
    """Get spreadsheet by type with comprehensive error handling"""
    if gc is None:
        st.error("❌ Not connected to Google Sheets. Please check authentication.")
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
            
            **Important**: The service account needs edit access to your spreadsheet.
            """)
        elif "notFound" in error_msg:
            st.error(f"""
            ## 📄 Spreadsheet Not Found
            
            The spreadsheet link for {batch_type} might be incorrect or deleted.
            
            **Current link:** {link}
            
            Please verify the spreadsheet exists and is accessible.
            """)
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
                st.warning(f"Could not read worksheets from {batch_type}: {e}")
    
    return all_batches

def get_student_count(worksheet):
    """Get number of students in a batch (excluding header)"""
    try:
        all_values = worksheet.get_all_values()
        return max(0, len(all_values) - 1)  # Subtract header row
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
    col1, col2, col3, col4 = st.columns(4)
    
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
    
    st.markdown("---")

# ============================
# SIDEBAR
# ============================
def show_sidebar():
    """Display sidebar with system info and tools"""
    with st.sidebar:
        st.title("🎓 System Info")
        
        # Connection status
        if gc:
            st.success("✅ Connected to Google Sheets")
            service_email = st.secrets["gcp_service_account"]["client_email"]
            st.caption(f"Service Account: `{service_email[:20]}...`")
        else:
            st.error("❌ Not Connected")
        
        st.markdown("---")
        
        # Quick Stats
        st.subheader("📊 Quick Stats")
        if gc:
            try:
                all_batches = get_all_batch_names()
                total_batches = len(all_batches)
                total_students = sum(get_student_count(batch["worksheet"]) for batch in all_batches)
                
                st.metric("Total Batches", total_batches)
                st.metric("Total Students", total_students)
            except:
                st.info("No data available")
        
        st.markdown("---")
        
        # Tools
        st.subheader("🛠️ Tools")
        if st.button("🔄 Refresh Connection"):
            st.session_state.gc = None
            st.rerun()
        
        if st.button("📋 View All Batches"):
            navigate_to('View Batches')
        
        st.markdown("---")
        
        # Help section
        with st.expander("❓ Need Help?"):
            st.markdown("""
            **Common Issues:**
            1. **Can't access sheet?** Share it with service account
            2. **Private key error?** Ensure newlines are actual \\n characters
            3. **Data not saving?** Check internet connection
            
            **Contact Support:** admin@example.com
            """)

# ============================
# PAGE: HOME
# ============================
def show_home_page():
    """Display home page"""
    st.title("🎓 Student Management System")
    st.markdown("Welcome to the comprehensive student management platform")
    
    # Connection status banner
    if not gc:
        st.warning("⚠️ System is not connected to Google Sheets. Some features may be limited.")
    
    # Feature cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📁 Create New Batch
        - Create IELTS or Aptis batches
        - Set batch time (4pm or 6pm)
        - Automatic spreadsheet creation
        """)
        if st.button("Create Batch →", key="home_create", use_container_width=True):
            navigate_to('Create Batch')
    
    with col2:
        st.markdown("""
        ### 👥 Student Management
        - Add new students to batches
        - Update student information
        - Search and filter students
        """)
        if st.button("Manage Students →", key="home_manage", use_container_width=True):
            navigate_to('Add Student')
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("""
        ### 🔍 Search & Analytics
        - Search by name or ID
        - Filter by batch
        - Export data to CSV
        """)
        if st.button("Search Students →", key="home_search", use_container_width=True):
            navigate_to('Find Student')
    
    with col4:
        st.markdown("""
        ### 📊 View All Data
        - View all batches
        - Student counts per batch
        - Batch statistics
        """)
        if st.button("View Batches →", key="home_view", use_container_width=True):
            navigate_to('View Batches')
    
    # Recent activity (if any)
    st.markdown("---")
    st.subheader("📈 Quick Overview")
    
    if gc:
        try:
            all_batches = get_all_batch_names()
            if all_batches:
                # Show recent batches
                recent_batches = all_batches[:5]  # Show first 5
                
                for batch in recent_batches:
                    student_count = get_student_count(batch["worksheet"])
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.text(f"📚 {batch['name']}")
                    with col2:
                        st.text(f"Type: {batch['type']}")
                    with col3:
                        st.text(f"Students: {student_count}")
                    st.progress(min(student_count / 50, 1.0))  # Cap at 50 for visualization
            else:
                st.info("No batches found. Create your first batch to get started!")
        except:
            st.info("Unable to load batch information")

# ============================
# PAGE: CREATE BATCH
# ============================
def show_create_batch_page():
    """Display create batch page"""
    st.title("📁 Create New Batch")
    show_navigation()
    
    if not gc:
        st.error("Please connect to Google Sheets first.")
        return
    
    with st.form("create_batch_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            batch_name = st.text_input("Batch Name*", placeholder="e.g., IELTS_Batch_1_2024")
            batch_type = st.selectbox("Batch Type*", ["IELTS", "Aptis"])
        
        with col2:
            year = st.selectbox("Year*", range(2024, 2031))
            batch_time = st.selectbox("Time Slot*", ["4:00 PM", "6:00 PM", "Other"])
        
        # Optional description
        description = st.text_area("Batch Description (Optional)", 
                                  placeholder="Enter any additional notes about this batch...")
        
        st.markdown("**Required fields***")
        
        submitted = st.form_submit_button("🚀 Create Batch", type="primary")
        
        if submitted:
            if not batch_name:
                st.error("Please enter a batch name.")
                return
            
            # Validate batch name doesn't exist
            all_batches = get_all_batch_names()
            existing_names = [b["name"] for b in all_batches]
            
            if batch_name in existing_names:
                st.error(f"Batch '{batch_name}' already exists. Please choose a different name.")
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
                        
                        # Add batch info as first row (optional)
                        batch_info = [
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "",  # No student ID for batch header
                            f"{batch_type} - {batch_name}",
                            "", "",  # Contact and Email empty
                            batch_name,
                            batch_time,
                            str(year),
                            "ACTIVE",
                            description if description else "No description"
                        ]
                        new_worksheet.append_row(batch_info)
                        
                        st.success(f"✅ Batch '{batch_name}' created successfully!")
                        st.balloons()
                        
                        # Show next steps
                        with st.expander("🎯 Next Steps"):
                            st.markdown(f"""
                            1. **Add Students**: Go to 'Add Student' page
                            2. **Share Access**: Batch is ready for data entry
                            3. **Manage**: You can now add students to {batch_name}
                            """)
                        
                        # Auto-clear form after delay
                        time.sleep(2)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Failed to create batch: {str(e)}")

# ============================
# PAGE: ADD STUDENT
# ============================
def show_add_student_page():
    """Display add student page"""
    st.title("➕ Add Student Information")
    show_navigation()
    
    if not gc:
        st.error("Please connect to Google Sheets first.")
        return
    
    # Get all available batches
    all_batches = get_all_batch_names()
    
    if not all_batches:
        st.warning("No batches found. Please create a batch first.")
        if st.button("Create New Batch"):
            navigate_to('Create Batch')
        return
    
    # Create two-column layout
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("student_form", clear_on_submit=True):
            st.subheader("Student Details")
            
            student_name = st.text_input("Full Name*", placeholder="John Smith")
            student_id = st.text_input("Student ID*", placeholder="STU2024001")
            contact_number = st.text_input("Contact Number*", placeholder="+1234567890")
            email = st.text_input("Email Address*", placeholder="john@example.com")
            
            st.subheader("Batch Information")
            
            # Group batches by type for better organization
            ielts_batches = [b for b in all_batches if b["type"] == "IELTS"]
            aptis_batches = [b for b in all_batches if b["type"] == "Aptis"]
            
            batch_type = st.radio("Select Batch Type:", ["IELTS", "Aptis"])
            
            if batch_type == "IELTS":
                available_batches = ielts_batches
            else:
                available_batches = aptis_batches
            
            if not available_batches:
                st.warning(f"No {batch_type} batches available. Create one first.")
                batch_name = None
            else:
                batch_options = [f"{b['name']} ({b['type']})" for b in available_batches]
                selected_batch = st.selectbox("Select Batch*", batch_options)
                batch_name = selected_batch.split(" (")[0]  # Extract just the name
            
            additional_notes = st.text_area("Additional Notes", 
                                          placeholder="Any special requirements or notes...",
                                          height=100)
            
            st.markdown("**Required fields***")
            
            submitted = st.form_submit_button("💾 Save Student Record", type="primary")
    
    with col2:
        st.subheader("📋 Preview & Information")
        st.info("""
        **Guidelines:**
        - All fields marked with * are required
        - Student ID must be unique
        - Email should be valid for communication
        - Double-check contact number
        """)
        
        # Live preview
        if student_name:
            st.markdown("### 📄 Record Preview")
            preview_data = {
                "Name": student_name,
                "Student ID": student_id,
                "Contact": contact_number,
                "Email": email,
                "Batch": batch_name if batch_name else "Not selected",
                "Type": batch_type
            }
            
            for key, value in preview_data.items():
                st.text(f"{key}: {value}")
    
    # Handle form submission
    if submitted:
        # Validation
        if not all([student_name, student_id, contact_number, email, batch_name]):
            st.error("Please fill all required fields.")
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
            st.success(f"✅ Student '{student_name}' added to '{batch_name}' successfully!")
            st.balloons()
            
            # Show summary
            with st.expander("📋 View Added Record"):
                summary_df = pd.DataFrame([{
                    "Field": ["Timestamp", "ID", "Name", "Contact", "Email", "Batch", "Type", "Status"],
                    "Value": [timestamp, student_id, student_name, contact_number, 
                             email, batch_name, batch_type, "ACTIVE"]
                }])
                st.table(summary_df)
            
            # Option to add another student
            if st.button("➕ Add Another Student"):
                st.rerun()
            
        except Exception as e:
            st.error(f"Failed to add student: {str(e)}")

# ============================
# PAGE: FIND STUDENT
# ============================
def show_find_student_page():
    """Display find student page"""
    st.title("🔍 Find Student")
    show_navigation()
    
    if not gc:
        st.error("Please connect to Google Sheets first.")
        return
    
    # Search interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input("Search by Name, ID, Email, or Contact", 
                                    placeholder="Enter search term...")
    
    with col2:
        search_type = st.selectbox("Search In", 
                                 ["All Fields", "Name Only", "ID Only", "Email Only"])
    
    # Filter options
    with st.expander("🔧 Advanced Filters"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            batch_filter = st.selectbox("Filter by Batch", 
                                       ["All Batches"] + [b["name"] for b in get_all_batch_names()])
        
        with col2:
            type_filter = st.selectbox("Filter by Type", 
                                      ["All Types", "IELTS", "Aptis"])
        
        with col3:
            year_filter = st.selectbox("Filter by Year", 
                                      ["All Years"] + list(range(2020, 2031)))
    
    # Search button
    search_button = st.button("🔎 Search", type="primary")
    
    if search_button or search_query:
        with st.spinner("Searching..."):
            try:
                # Collect all student data
                all_students = []
                
                for batch in get_all_batch_names():
                    try:
                        worksheet = batch["worksheet"]
                        data = worksheet.get_all_records()
                        
                        for row in data:
                            # Add batch info to each row
                            row["Batch_Name"] = batch["name"]
                            row["Batch_Type"] = batch["type"]
                            all_students.append(row)
                    except:
                        continue
                
                if not all_students:
                    st.info("No student records found.")
                    return
                
                # Convert to DataFrame
                df = pd.DataFrame(all_students)
                
                # Apply filters
                if batch_filter != "All Batches":
                    df = df[df["Batch_Name"] == batch_filter]
                
                if type_filter != "All Types":
                    df = df[df["Batch_Type"] == type_filter]
                
                if year_filter != "All Years":
                    # Assuming there's a Year column
                    if "Year" in df.columns:
                        df = df[df["Year"] == str(year_filter)]
                
                # Apply search
                if search_query:
                    if search_type == "Name Only":
                        mask = df["Full Name"].astype(str).str.contains(search_query, case=False, na=False)
                    elif search_type == "ID Only":
                        mask = df["Student ID"].astype(str).str.contains(search_query, case=False, na=False)
                    elif search_type == "Email Only":
                        mask = df["Email Address"].astype(str).str.contains(search_query, case=False, na=False)
                    else:  # All Fields
                        mask = df.astype(str).apply(
                            lambda x: x.str.contains(search_query, case=False, na=False)
                        ).any(axis=1)
                    
                    df = df[mask]
                
                # Display results
                if len(df) > 0:
                    st.success(f"Found {len(df)} student(s)")
                    
                    # Select columns to display
                    display_cols = ["Timestamp", "Student ID", "Full Name", "Contact Number", 
                                   "Email Address", "Batch_Name", "Batch_Type", "Status"]
                    
                    # Filter to available columns
                    available_cols = [col for col in display_cols if col in df.columns]
                    display_df = df[available_cols]
                    
                    # Show data
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        height=400
                    )
                    
                    # Export option
                    col1, col2 = st.columns(2)
                    with col1:
                        csv = display_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name=f"students_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        if st.button("🔄 Clear Search"):
                            st.rerun()
                    
                    # Show statistics
                    with st.expander("📊 Search Statistics"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Records", len(df))
                        with col2:
                            unique_batches = df["Batch_Name"].nunique()
                            st.metric("Unique Batches", unique_batches)
                        with col3:
                            active_count = len(df[df.get("Status", "") == "ACTIVE"])
                            st.metric("Active Students", active_count)
                
                else:
                    st.warning("No students found matching your search criteria.")
                    
            except Exception as e:
                st.error(f"Search failed: {str(e)}")

# ============================
# PAGE: VIEW BATCHES
# ============================
def show_view_batches_page():
    """Display all batches with statistics"""
    st.title("📊 View All Batches")
    show_navigation()
    
    if not gc:
        st.error("Please connect to Google Sheets first.")
        return
    
    try:
        all_batches = get_all_batch_names()
        
        if not all_batches:
            st.info("No batches found. Create your first batch!")
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
        
        df = pd.DataFrame(batch_data)
        
        # Display statistics
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
        st.subheader("📋 Batch Details")
        
        # Add search
        search_term = st.text_input("Search batches...")
        if search_term:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        
        # Display table with interactive features
        edited_df = st.data_editor(
            df[["Batch Name", "Type", "Student Count"]],
            use_container_width=True,
            height=400,
            column_config={
                "Student Count": st.column_config.ProgressColumn(
                    "Student Count",
                    help="Number of students in batch",
                    format="%d",
                    min_value=0,
                    max_value=df["Student Count"].max() if len(df) > 0 else 100
                )
            }
        )
        
        # Batch actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Data"):
                st.rerun()
        
        with col2:
            if st.button("📥 Export Batch List"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="batches.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("📊 View Statistics"):
                with st.expander("Detailed Statistics"):
                    st.write(df.describe())
        
        # Show individual batch details
        st.subheader("🔍 Batch Details")
        selected_batch = st.selectbox("Select a batch to view details:", df["Batch Name"].tolist())
        
        if selected_batch:
            selected_row = df[df["Batch Name"] == selected_batch].iloc[0]
            worksheet = selected_row["Worksheet"]
            
            try:
                student_data = worksheet.get_all_records()
                if student_data:
                    st.write(f"**Students in {selected_batch}:**")
                    students_df = pd.DataFrame(student_data)
                    # Remove batch info row if present
                    students_df = students_df[students_df["Student ID"].astype(str) != ""]
                    st.dataframe(students_df, use_container_width=True, height=300)
                else:
                    st.info("No students in this batch yet.")
            except:
                st.warning("Could not load student data for this batch.")
        
    except Exception as e:
        st.error(f"Failed to load batches: {str(e)}")

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
    else:
        show_home_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        🎓 Student Management System • Built with Streamlit • 
        <a href='https://docs.streamlit.io' target='_blank'>Documentation</a>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================
# RUN THE APPLICATION
# ============================
if __name__ == "__main__":
    main()
