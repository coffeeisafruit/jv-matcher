#!/usr/bin/env python3
"""
JV Directory & Matcher - Combined Streamlit Web Application
Features:
- User authentication via Supabase
- Profile directory browsing and search
- Transcript processing and profile extraction
- AI-powered JV partner matching
- Admin panel for imports and management
"""
import streamlit as st
import pandas as pd
import os
import tempfile
from pathlib import Path
from datetime import datetime
import zipfile

# Import services
try:
    from auth_service import AuthService, init_session_state
    from directory_service import DirectoryService
    from match_generator import MatchGenerator, AIMatchGenerator, HybridMatchGenerator
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from jv_matcher import JVMatcher

# Page configuration
st.set_page_config(
    page_title="JV Directory & Matcher",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Match categories
MATCH_CATEGORIES = ["All", "health", "business", "finance", "personal_dev", "spirituality", "relationships", "content", "tech"]

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a5f;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .profile-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
        margin-bottom: 0.5rem;
    }
    .member-badge {
        background: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
    }
    .non-member-badge {
        background: #6c757d;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
    }
    .match-score {
        background: #ffc107;
        color: #000;
        padding: 0.2rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #17a2b8;
    }
</style>
""", unsafe_allow_html=True)

# Initialize services
if SUPABASE_AVAILABLE:
    auth_service = AuthService()

def main():
    if SUPABASE_AVAILABLE:
        init_session_state()

        # Check for existing session
        if not st.session_state.authenticated:
            show_auth_page()
        else:
            show_main_app()
    else:
        # Fallback mode without Supabase - just show transcript processing
        show_standalone_mode()

# ==========================================
# STANDALONE MODE (No Supabase)
# ==========================================

def show_standalone_mode():
    """Standalone mode for transcript processing without database"""
    st.markdown('<div class="main-header">JV Matcher</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Partner Matching</div>', unsafe_allow_html=True)

    st.warning("Running in standalone mode. Connect Supabase for full features.")

    # Simple navigation
    page = st.sidebar.radio("Navigation", ["Process Transcripts", "Help"])

    if page == "Process Transcripts":
        show_process_transcripts_standalone()
    else:
        show_help()

def show_process_transcripts_standalone():
    """Transcript processing without database integration"""
    st.markdown("## Process Transcripts")

    uploaded_files = st.file_uploader(
        "Upload transcript files",
        type=['txt', 'md', 'docx'],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.markdown(f"### {len(uploaded_files)} file(s) uploaded")

        matches_per_person = st.slider("Matches per person", 5, 20, 10)

        if st.button("Process Files", type="primary"):
            process_transcripts_simple(uploaded_files, matches_per_person)

def process_transcripts_simple(uploaded_files, matches_per_person):
    """Simple transcript processing without saving to database"""
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        temp_dir = tempfile.mkdtemp()
        file_paths = []

        status_text.text("Saving uploaded files...")
        progress_bar.progress(10)

        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(file_path)

        status_text.text("Extracting profiles...")
        progress_bar.progress(30)

        matcher = JVMatcher(output_dir="outputs")

        status_text.text("Finding matches...")
        progress_bar.progress(50)

        results = matcher.process_files(file_paths, matches_per_person=matches_per_person)

        status_text.text("Generating reports...")
        progress_bar.progress(80)

        progress_bar.progress(100)
        status_text.text("Complete!")

        st.success(f"Processed {results['total_profiles']} profiles, generated {results['total_reports']} reports")

        if os.path.exists(results['zip_path']):
            with open(results['zip_path'], 'rb') as f:
                st.download_button(
                    "Download All Reports (ZIP)",
                    data=f.read(),
                    file_name=os.path.basename(results['zip_path']),
                    mime="application/zip"
                )

    except Exception as e:
        st.error(f"Error: {str(e)}")

# ==========================================
# AUTHENTICATION PAGES
# ==========================================

def show_auth_page():
    """Show login/signup page"""
    st.markdown('<div class="main-header">JV Directory</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Your Partner Connection Hub</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        show_login_form()

    with tab2:
        show_signup_form()

def show_login_form():
    """Login form"""
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

        if submit:
            if email and password:
                result = auth_service.sign_in(email, password)
                if result["success"]:
                    st.session_state.authenticated = True
                    st.session_state.user = result["user"]
                    directory_service = DirectoryService(use_admin=True)
                    profile = directory_service.get_profile_by_auth_user(result["user"].id)
                    st.session_state.user_profile = profile
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(f"Login failed: {result.get('error', 'Unknown error')}")
            else:
                st.warning("Please enter email and password")

    with st.expander("Forgot Password?"):
        reset_email = st.text_input("Enter your email", key="reset_email")
        if st.button("Send Reset Link"):
            if reset_email:
                result = auth_service.reset_password(reset_email)
                if result["success"]:
                    st.success("Password reset email sent!")
                else:
                    st.error(f"Error: {result.get('error', 'Unknown error')}")

def show_signup_form():
    """Signup form"""
    with st.form("signup_form"):
        full_name = st.text_input("Full Name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        password_confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Create Account", use_container_width=True)

        if submit:
            if not all([full_name, email, password, password_confirm]):
                st.warning("Please fill in all fields")
            elif password != password_confirm:
                st.error("Passwords do not match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                result = auth_service.sign_up(email, password, full_name)
                if result["success"]:
                    st.success("Account created! Check your email to verify, then log in.")
                else:
                    st.error(f"Signup failed: {result.get('error', 'Unknown error')}")

# ==========================================
# MAIN APPLICATION
# ==========================================

def show_main_app():
    """Main application after login"""
    user_profile = st.session_state.user_profile or {}
    is_admin = user_profile.get('role') == 'admin'

    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"**{user_profile.get('name', 'User')}**")
        if user_profile.get('company'):
            st.caption(user_profile.get('company'))
        if is_admin:
            st.caption("Admin")

        st.markdown("---")

        # Navigation pages
        pages = ["Dashboard", "Directory", "Search", "Process Transcripts", "My Matches", "My Preferences", "My Connections"]
        if is_admin:
            pages.append("Admin")

        page = st.radio("Navigation", pages, label_visibility="collapsed")

        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            auth_service.sign_out()
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_profile = None
            st.rerun()

    # Route to pages
    if page == "Dashboard":
        show_dashboard()
    elif page == "Directory":
        show_directory()
    elif page == "Search":
        show_search()
    elif page == "Process Transcripts":
        show_process_transcripts()
    elif page == "My Matches":
        show_matches()
    elif page == "My Preferences":
        show_preferences()
    elif page == "My Connections":
        show_connections()
    elif page == "Admin":
        show_admin()

# ==========================================
# DASHBOARD
# ==========================================

def show_dashboard():
    """Dashboard with stats"""
    st.markdown('<div class="main-header">Dashboard</div>', unsafe_allow_html=True)

    directory_service = DirectoryService(use_admin=True)
    stats = directory_service.get_stats()

    # Stats cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats.get('total_profiles', 0):,}</div>
            <div class="stat-label">Total Profiles</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats.get('members', 0):,}</div>
            <div class="stat-label">Members</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats.get('non_members', 0):,}</div>
            <div class="stat-label">Resources</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats.get('registered_users', 0):,}</div>
            <div class="stat-label">Registered</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # My Profile Section
    user_profile = st.session_state.user_profile or {}

    tab1, tab2 = st.tabs(["My Profile", "Edit Profile"])

    with tab1:
        st.markdown("### Profile Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Name:** {user_profile.get('name', 'N/A')}")
            st.markdown(f"**Company:** {user_profile.get('company', 'N/A')}")
            st.markdown(f"**Status:** {user_profile.get('status', 'N/A')}")
        with col2:
            st.markdown(f"**List Size:** {user_profile.get('list_size', 0):,}")
            st.markdown(f"**Social Reach:** {user_profile.get('social_reach', 0):,}")
            st.markdown(f"**Business Size:** {user_profile.get('business_size', 'N/A')}")

        if user_profile.get('business_focus'):
            st.markdown(f"**Business Focus:** {user_profile.get('business_focus')}")
        if user_profile.get('service_provided'):
            st.markdown(f"**Services:** {user_profile.get('service_provided')}")

    with tab2:
        st.markdown("### Edit Your Profile")
        st.caption("Update your profile to get better match suggestions")

        # Show success message if profile was just updated
        if st.session_state.get('profile_updated'):
            st.success("Profile updated successfully!")
            del st.session_state['profile_updated']

        with st.form("edit_profile_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Name", value=user_profile.get('name', ''))
                company = st.text_input("Company", value=user_profile.get('company', ''))
                business_focus = st.text_area(
                    "Business Focus",
                    value=user_profile.get('business_focus', ''),
                    help="What does your business do? What's your niche?"
                )

            with col2:
                service_provided = st.text_area(
                    "Services Provided",
                    value=user_profile.get('service_provided', ''),
                    help="What services do you offer?"
                )
                list_size = st.number_input("Email List Size", value=user_profile.get('list_size', 0) or 0, min_value=0)
                social_reach = st.number_input("Social Media Reach", value=user_profile.get('social_reach', 0) or 0, min_value=0)

            if st.form_submit_button("Save Profile", type="primary", use_container_width=True):
                if not user_profile.get('id'):
                    st.error("Profile not found. Please log out and log back in.")
                else:
                    try:
                        update_data = {
                            "name": name,
                            "company": company if company else None,
                            "business_focus": business_focus if business_focus else None,
                            "service_provided": service_provided if service_provided else None,
                            "list_size": list_size,
                            "social_reach": social_reach
                        }

                        result = directory_service.update_profile(user_profile['id'], update_data)
                        if result.get('success'):
                            # Update session state
                            st.session_state.user_profile.update(update_data)
                            st.session_state['profile_updated'] = True
                            st.rerun()
                        else:
                            st.error(f"Error updating profile: {result.get('error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# ==========================================
# DIRECTORY BROWSER
# ==========================================

def show_directory():
    """Browse all profiles"""
    st.markdown('<div class="main-header">Directory</div>', unsafe_allow_html=True)

    directory_service = DirectoryService(use_admin=True)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Status", ["All", "Member", "Non Member Resource"])
    with col2:
        focus_filter = st.text_input("Business Focus", placeholder="e.g., Health")
    with col3:
        per_page = st.selectbox("Per Page", [25, 50, 100], index=0)

    # Pagination state
    if "dir_page" not in st.session_state:
        st.session_state.dir_page = 0

    # Fetch profiles
    result = directory_service.get_profiles(
        status=status_filter if status_filter != "All" else "",
        business_focus=focus_filter,
        limit=per_page,
        offset=st.session_state.dir_page * per_page
    )

    if result["success"]:
        profiles = result["data"]
        total = result["count"] or 0
        total_pages = max(1, (total + per_page - 1) // per_page)

        st.markdown(f"**{total:,} profiles** | Page {st.session_state.dir_page + 1} of {total_pages}")

        # Display as table
        if profiles:
            df = pd.DataFrame(profiles)[['name', 'company', 'business_focus', 'status', 'list_size', 'social_reach']]
            df.columns = ['Name', 'Company', 'Business Focus', 'Status', 'List Size', 'Social Reach']
            df['List Size'] = df['List Size'].fillna(0).astype(int).apply(lambda x: f"{x:,}")
            df['Social Reach'] = df['Social Reach'].fillna(0).astype(int).apply(lambda x: f"{x:,}")
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Pagination
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.dir_page > 0:
                if st.button("Previous"):
                    st.session_state.dir_page -= 1
                    st.rerun()
        with col3:
            if st.session_state.dir_page < total_pages - 1:
                if st.button("Next"):
                    st.session_state.dir_page += 1
                    st.rerun()
    else:
        st.error("Failed to load profiles")

# ==========================================
# SEARCH
# ==========================================

def show_search():
    """Search profiles"""
    st.markdown('<div class="main-header">Search</div>', unsafe_allow_html=True)

    query = st.text_input("Search by name, company, business focus, or services...", key="search_query")

    if query and len(query) >= 2:
        directory_service = DirectoryService(use_admin=True)
        result = directory_service.get_profiles(search=query, limit=50)

        if result["success"]:
            profiles = result["data"]
            st.markdown(f"**{len(profiles)} results**")

            for profile in profiles:
                display_profile_card(profile, directory_service)
        else:
            st.error("Search failed")
    elif query:
        st.info("Enter at least 2 characters")

def display_profile_card(profile: dict, directory_service: DirectoryService):
    """Display a profile card with actions"""
    user_profile = st.session_state.user_profile or {}
    my_profile_id = user_profile.get('id')

    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"**{profile.get('name', 'Unknown')}**")
            if profile.get('company'):
                st.caption(profile['company'])

        with col2:
            status = profile.get('status', '')
            if status == 'Member':
                st.markdown('<span class="member-badge">Member</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="non-member-badge">Resource</span>', unsafe_allow_html=True)

            metrics = []
            if profile.get('list_size'):
                metrics.append(f"List: {profile['list_size']:,}")
            if profile.get('social_reach'):
                metrics.append(f"Reach: {profile['social_reach']:,}")
            if metrics:
                st.caption(" | ".join(metrics))

        with col3:
            if my_profile_id and profile['id'] != my_profile_id:
                if st.button("Connect", key=f"conn_{profile['id']}", use_container_width=True):
                    result = directory_service.add_connection(my_profile_id, profile['id'])
                    if result["success"]:
                        st.success("Connected!")
                    else:
                        st.error("Already connected")

        if profile.get('business_focus'):
            st.caption(f"Focus: {profile['business_focus'][:80]}...")

        st.markdown("---")

# ==========================================
# PROCESS TRANSCRIPTS
# ==========================================

def show_process_transcripts():
    """Process transcripts and optionally save to database"""
    st.markdown('<div class="main-header">Process Transcripts</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        <strong>Upload meeting transcripts to:</strong><br>
        1. Extract participant profiles automatically<br>
        2. Find ideal JV partners for each person<br>
        3. Save profiles to the directory (optional)<br>
        4. Generate personalized reports
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose transcript files",
        type=['txt', 'md', 'docx'],
        accept_multiple_files=True,
        help="Upload one or more meeting transcript files"
    )

    if uploaded_files:
        st.markdown(f"### {len(uploaded_files)} file(s) uploaded")

        with st.expander("View Uploaded Files", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                st.markdown(f"**{i}. {file.name}** ({file.size:,} bytes)")

        # Processing options
        st.markdown("### Processing Options")
        col1, col2 = st.columns(2)

        with col1:
            matches_per_person = st.slider(
                "Number of matches per person",
                min_value=5,
                max_value=20,
                value=10,
                help="How many JV partners to recommend for each person"
            )

        with col2:
            save_to_database = st.checkbox(
                "Save extracted profiles to directory",
                value=True,
                help="Add extracted profiles to your JV Directory database"
            )

        # Process button
        st.markdown("")
        if st.button("Process Files", type="primary", use_container_width=True):
            process_transcripts_with_database(uploaded_files, matches_per_person, save_to_database)

    else:
        st.info("Upload one or more transcript files to get started")

def process_transcripts_with_database(uploaded_files, matches_per_person, save_to_database):
    """Process transcripts and optionally save to database"""
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Save uploaded files to temporary directory
        temp_dir = tempfile.mkdtemp()
        file_paths = []

        status_text.text("Saving uploaded files...")
        progress_bar.progress(10)

        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(file_path)

        status_text.text("Extracting profiles from transcripts...")
        progress_bar.progress(30)

        # Initialize matcher
        matcher = JVMatcher(output_dir="outputs")

        # Extract profiles first
        all_profiles = []
        for file_path in file_paths:
            profiles = matcher.extract_profiles_from_transcript(file_path)
            all_profiles.extend(profiles)

        status_text.text(f"Found {len(all_profiles)} profiles. Processing...")
        progress_bar.progress(40)

        # Save to database if requested
        profiles_saved = 0
        if save_to_database and SUPABASE_AVAILABLE:
            status_text.text("Saving profiles to directory...")
            progress_bar.progress(50)

            directory_service = DirectoryService(use_admin=True)

            for profile in all_profiles:
                # Check if profile already exists
                existing = directory_service.get_profiles(search=profile.get('name', ''), limit=1)

                if not existing.get('data'):
                    # Extract keywords from content if available
                    content = profile.get('content', profile.get('summary', ''))
                    keywords = matcher._extract_keywords(content)[:5] if content else []

                    # Create new profile
                    result = directory_service.create_profile({
                        'name': profile.get('name', 'Unknown'),
                        'status': 'Pending',
                        'business_focus': ', '.join(keywords) if keywords else None,
                        'source': 'transcript_extraction'
                    })
                    if result.get('success'):
                        profiles_saved += 1

        status_text.text("Finding JV partner matches...")
        progress_bar.progress(60)

        # Process files with matcher
        results = matcher.process_files(file_paths, matches_per_person=matches_per_person)

        status_text.text("Generating reports...")
        progress_bar.progress(80)

        status_text.text("Processing complete!")
        progress_bar.progress(100)

        # Show results
        st.markdown("""
        <div class="success-box">
            <h3>Processing Complete!</h3>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Profiles Extracted", results['total_profiles'])
        with col2:
            st.metric("Reports Generated", results['total_reports'])
        with col3:
            st.metric("Saved to Directory", profiles_saved)

        # Download ZIP
        if os.path.exists(results['zip_path']):
            with open(results['zip_path'], 'rb') as f:
                st.download_button(
                    label="Download All Reports (ZIP)",
                    data=f.read(),
                    file_name=os.path.basename(results['zip_path']),
                    mime="application/zip",
                    use_container_width=True
                )

        # Show individual reports
        st.markdown("### Generated Reports")
        for i, report_path in enumerate(results['reports'], 1):
            report_name = os.path.basename(report_path)
            if os.path.exists(report_path):
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()

                with st.expander(f"{report_name}"):
                    st.markdown(report_content)

                    st.download_button(
                        label=f"Download {report_name}",
                        data=report_content,
                        file_name=report_name,
                        mime="text/markdown",
                        key=f"download_{i}"
                    )

    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        progress_bar.empty()
        status_text.empty()

# ==========================================
# MY MATCHES
# ==========================================

def show_matches():
    """Show match suggestions for current user"""
    st.markdown('<div class="main-header">My Matches</div>', unsafe_allow_html=True)

    user_profile = st.session_state.user_profile
    if not user_profile:
        st.warning("Profile not found")
        return

    directory_service = DirectoryService(use_admin=True)

    # Show success message if matches were just refreshed
    if st.session_state.get('matches_refreshed'):
        st.success(f"Matches refreshed! Found {st.session_state.get('matches_count', 0)} new matches.")
        del st.session_state['matches_refreshed']
        if 'matches_count' in st.session_state:
            del st.session_state['matches_count']

    # Refresh matches button
    col_refresh, col_spacer = st.columns([1, 3])
    with col_refresh:
        if st.button("Refresh My Matches", type="secondary", help="Regenerate matches based on your current profile"):
            with st.spinner("Finding your best matches..."):
                try:
                    # Use hybrid matcher if OpenAI key available
                    import os
                    if os.getenv("OPENAI_API_KEY"):
                        generator = HybridMatchGenerator()
                    else:
                        generator = MatchGenerator()

                    result = generator.generate_matches_for_user(user_profile['id'], top_n=10)

                    if result.get('success'):
                        st.session_state['matches_refreshed'] = True
                        st.session_state['matches_count'] = result.get('matches_created', 0)
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error refreshing matches: {str(e)}")

    st.markdown("---")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox("Status", ["All", "pending", "viewed", "contacted", "connected", "dismissed"])

    with col2:
        category_filter = st.multiselect("Categories", MATCH_CATEGORIES, default=["All"])
        if "All" in category_filter or not category_filter:
            category_filter = None

    with col3:
        use_reach_filter = st.checkbox("Filter by reach")
        if use_reach_filter:
            reach_range = st.slider("Reach Range", min_value=0, max_value=1000000, value=(0, 100000), step=10000, format="%d")
        else:
            reach_range = None

    matches = directory_service.get_match_suggestions(
        user_profile['id'],
        status=status_filter if status_filter != "All" else None
    )

    # Apply client-side filters
    if matches:
        filtered_matches = []
        for match in matches:
            suggested = match.get('suggested', {})
            if not suggested:
                continue

            # Category filter
            if category_filter:
                match_categories = match.get('categories', [])
                if not match_categories or not any(cat in category_filter for cat in match_categories):
                    continue

            # Reach filter
            if reach_range:
                social_reach = suggested.get('social_reach', 0) or 0
                if not (reach_range[0] <= social_reach <= reach_range[1]):
                    continue

            filtered_matches.append(match)

        matches = filtered_matches

    if matches:
        st.markdown(f"**{len(matches)} matches**")

        for match in matches:
            suggested = match.get('suggested', {})
            if not suggested:
                continue

            score = match.get('match_score', 0)
            status = match.get('status', 'pending')

            # Create expandable card for each match
            with st.expander(f"**{suggested.get('name', 'Unknown')}** - {score}% match", expanded=(status == 'viewed')):
                # Header info
                col1, col2 = st.columns([2, 1])

                with col1:
                    if suggested.get('company'):
                        st.markdown(f"**Company:** {suggested['company']}")
                    if suggested.get('business_focus'):
                        st.markdown(f"**Focus:** {suggested['business_focus']}")
                    if suggested.get('service_provided'):
                        st.markdown(f"**Services:** {suggested['service_provided']}")

                with col2:
                    st.markdown(f'<span class="match-score">{score}% match</span>', unsafe_allow_html=True)
                    if suggested.get('social_reach'):
                        st.caption(f"Reach: {suggested['social_reach']:,}")
                    if suggested.get('list_size'):
                        st.caption(f"List: {suggested['list_size']:,}")

                # Match reason
                if match.get('match_reason'):
                    st.markdown("---")
                    st.markdown(f"**Why this match:** {match['match_reason']}")

                # Action buttons
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    if status == 'pending':
                        if st.button("Mark as Viewed", key=f"view_{match['id']}", type="primary"):
                            directory_service.update_match_status(match['id'], 'viewed')
                            st.rerun()
                    elif status == 'viewed':
                        if st.button("Mark as Contacted", key=f"contact_{match['id']}", type="primary"):
                            directory_service.update_match_status(match['id'], 'contacted')
                            st.rerun()
                    elif status == 'contacted':
                        st.success("Contacted")
                    elif status == 'connected':
                        st.success("Connected")

                with col2:
                    if status != 'connected':
                        if st.button("Connect", key=f"connect_{match['id']}"):
                            directory_service.add_connection(user_profile['id'], suggested['id'])
                            directory_service.update_match_status(match['id'], 'connected')
                            st.rerun()

                with col3:
                    if status not in ['dismissed', 'pending']:
                        if st.button("Reset", key=f"reset_{match['id']}", help="Reset to pending status"):
                            directory_service.update_match_status(match['id'], 'pending')
                            st.rerun()

                with col4:
                    if status not in ['dismissed', 'connected']:
                        if st.button("Dismiss", key=f"dismiss_{match['id']}", type="secondary"):
                            directory_service.dismiss_match(user_profile['id'], suggested['id'])
                            st.rerun()
    else:
        st.info("No match suggestions yet. Check back after matches are generated.")

# ==========================================
# MY PREFERENCES
# ==========================================

def show_preferences():
    """Show and edit user's matching preferences"""
    st.markdown('<div class="main-header">My Preferences</div>', unsafe_allow_html=True)

    user_profile = st.session_state.user_profile
    if not user_profile:
        st.warning("Profile not found")
        return

    directory_service = DirectoryService(use_admin=True)

    st.markdown("""
    <div class="info-box">
        <strong>Customize your match preferences</strong><br>
        Set your category interests and partnership types to get more relevant match suggestions.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # Get current preferences (if available)
    current_categories = user_profile.get('preferred_categories', [])
    current_partnership_types = user_profile.get('preferred_partnership_types', [])

    # Category preferences
    st.markdown("### Category Interests")
    st.caption("Select the categories you're interested in for potential partnerships")

    selected_categories = st.multiselect(
        "Categories",
        [cat for cat in MATCH_CATEGORIES if cat != "All"],
        default=current_categories if current_categories else [],
        help="Choose categories that align with your business interests",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Partnership type preferences
    st.markdown("### Partnership Types")
    st.caption("Select the types of partnerships you're interested in")

    partnership_types = ["affiliate", "speaking", "content collaboration", "referral", "joint venture", "sponsorship"]

    selected_partnership_types = st.multiselect(
        "Partnership Types",
        partnership_types,
        default=current_partnership_types if current_partnership_types else [],
        help="Choose the types of partnerships you're open to",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Save button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Save Preferences", type="primary", use_container_width=True):
            result = directory_service.update_profile_preferences(
                user_profile['id'],
                selected_categories,
                selected_partnership_types
            )

            if result.get('success'):
                st.success("Preferences saved successfully!")
                # Update session state
                st.session_state.user_profile['preferred_categories'] = selected_categories
                st.session_state.user_profile['preferred_partnership_types'] = selected_partnership_types
                st.rerun()
            else:
                st.error("Failed to save preferences")

    with col2:
        if st.button("Reset", type="secondary", use_container_width=True):
            st.rerun()

    # Show current preferences summary
    if selected_categories or selected_partnership_types:
        st.markdown("---")
        st.markdown("### Current Preferences")

        if selected_categories:
            st.markdown(f"**Categories:** {', '.join(selected_categories)}")

        if selected_partnership_types:
            st.markdown(f"**Partnership Types:** {', '.join(selected_partnership_types)}")

# ==========================================
# MY CONNECTIONS
# ==========================================

def show_connections():
    """Show user's connections"""
    st.markdown('<div class="main-header">My Connections</div>', unsafe_allow_html=True)

    user_profile = st.session_state.user_profile
    if not user_profile:
        st.warning("Profile not found")
        return

    directory_service = DirectoryService(use_admin=True)
    connections = directory_service.get_connections(user_profile['id'])

    if connections:
        st.markdown(f"**{len(connections)} connections**")

        for conn in connections:
            following = conn.get('following', {})
            if not following:
                continue

            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.markdown(f"**{following.get('name', 'Unknown')}**")
                    if following.get('company'):
                        st.caption(following['company'])

                with col2:
                    if following.get('business_focus'):
                        st.caption(following['business_focus'][:50])

                with col3:
                    if st.button("Remove", key=f"rm_{conn['following_id']}"):
                        directory_service.remove_connection(user_profile['id'], conn['following_id'])
                        st.rerun()

                st.markdown("---")
    else:
        st.info("No connections yet. Browse the directory to connect with people.")

# ==========================================
# ADMIN PANEL
# ==========================================

def show_admin():
    """Admin panel"""
    st.markdown('<div class="main-header">Admin Panel</div>', unsafe_allow_html=True)

    user_profile = st.session_state.user_profile or {}
    if user_profile.get('role') != 'admin':
        st.error("Admin access required")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["Add Profile", "Import CSV", "Export", "Generate Matches"])

    with tab1:
        show_add_profile_form()

    with tab2:
        show_import_section()

    with tab3:
        show_export_section()

    with tab4:
        show_generate_matches()

def show_add_profile_form():
    """Form to add a new profile"""
    st.markdown("### Add New Profile")

    with st.form("add_profile"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name*")
            company = st.text_input("Company")
            email = st.text_input("Email")
            phone = st.text_input("Phone")

        with col2:
            status = st.selectbox("Status", ["Member", "Non Member Resource", "Pending"])
            business_focus = st.text_input("Business Focus")
            service_provided = st.text_input("Services")
            website = st.text_input("Website")

        col1, col2, col3 = st.columns(3)
        with col1:
            list_size = st.number_input("List Size", min_value=0, value=0)
        with col2:
            business_size = st.selectbox("Business Size", [
                "", "1. Not Publicly Available", "2. $0 to $10,000",
                "3. $10,000 to $100,000", "4. $100,000 to $1 Million",
                "5. $1 Million to $2.5 Million", "6. $2.5 Million to $10 Million",
                "7. $10 Million and Above"
            ])
        with col3:
            social_reach = st.number_input("Social Reach", min_value=0, value=0)

        if st.form_submit_button("Add Profile", type="primary"):
            if not name:
                st.error("Name is required")
            else:
                directory_service = DirectoryService(use_admin=True)
                result = directory_service.create_profile({
                    "name": name,
                    "company": company or None,
                    "email": email or None,
                    "phone": phone or None,
                    "status": status,
                    "business_focus": business_focus or None,
                    "service_provided": service_provided or None,
                    "website": website or None,
                    "list_size": list_size,
                    "business_size": business_size or None,
                    "social_reach": social_reach
                })
                if result["success"]:
                    st.success(f"Profile '{name}' created!")
                else:
                    st.error(f"Error: {result.get('error')}")

def show_import_section():
    """CSV import"""
    st.markdown("### Import from CSV")

    uploaded = st.file_uploader("Choose CSV", type="csv")

    if uploaded:
        df = pd.read_csv(uploaded)
        st.markdown(f"**{len(df)} rows**")
        st.dataframe(df.head(10))

        if st.button("Import All", type="primary"):
            with st.spinner("Importing..."):
                directory_service = DirectoryService(use_admin=True)
                result = directory_service.import_from_csv(df)
                if result["success"]:
                    st.success(f"Imported {result['records_imported']} profiles")
                else:
                    st.error(f"Error: {result.get('error')}")

def show_export_section():
    """Export data"""
    st.markdown("### Export Directory")

    if st.button("Generate Export"):
        directory_service = DirectoryService(use_admin=True)
        df = directory_service.export_to_dataframe()

        if not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv,
                file_name="jv_directory_export.csv",
                mime="text/csv"
            )
            st.success(f"{len(df)} profiles exported")

def show_generate_matches():
    """Generate match suggestions"""
    st.markdown("### Generate Match Suggestions")

    # Check for API keys - use best available method automatically
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))

    if has_openai_key:
        st.info("Using smart matching (semantic + keywords + categories + reach compatibility)")
        use_hybrid = True
        use_ai = False
    else:
        st.info("Using keyword matching. Add OPENAI_API_KEY in secrets for smarter matching.")
        use_hybrid = False
        use_ai = False

    col1, col2 = st.columns(2)
    with col1:
        top_n = st.number_input("Matches per profile", min_value=1, max_value=50, value=10)
    with col2:
        min_score = st.slider("Minimum match score (%)", min_value=0, max_value=50, value=15)

    only_registered = st.checkbox("Only generate for registered users", value=False)

    st.markdown("---")

    if st.button("Generate Matches for All Users", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Preparing match generation...")

        with st.spinner("Generating matches... This may take a few minutes."):
            if use_hybrid:
                status_text.text("Using smart matching with semantic analysis...")
                generator = HybridMatchGenerator()
                result = generator.generate_all_matches(
                    top_n=top_n,
                    min_score=float(min_score),
                    only_registered=only_registered
                )
            else:
                status_text.text("Using keyword matching...")
                generator = MatchGenerator()
                result = generator.generate_all_matches(
                    top_n=top_n,
                    min_score=float(min_score),
                    only_registered=only_registered
                )

        progress_bar.progress(100)

        if result['success']:
            st.success("Match generation complete!")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Profiles Processed", result['profiles_processed'])
            with col2:
                st.metric("Matches Created", result['matches_created'])
        else:
            st.error(f"Error: {result.get('error', 'Unknown error')}")

    st.markdown("---")
    st.markdown("### Generate for Specific User")

    directory_service = DirectoryService(use_admin=True)

    user_search = st.text_input("Search for user by name")
    if user_search and len(user_search) >= 2:
        result = directory_service.get_profiles(search=user_search, limit=10)
        if result['success'] and result['data']:
            selected_user = st.selectbox(
                "Select user",
                options=result['data'],
                format_func=lambda x: f"{x['name']} - {x.get('company', 'N/A')}"
            )

            if st.button("Generate Matches for This User", type="secondary"):
                generator = MatchGenerator()
                with st.spinner(f"Generating matches for {selected_user['name']}..."):
                    match_result = generator.generate_matches_for_user(
                        selected_user['id'],
                        top_n=top_n
                    )

                if match_result['success']:
                    st.success(f"Created {match_result['matches_created']} matches!")

                    if match_result.get('matches'):
                        st.markdown("**Top Matches:**")
                        for match in match_result['matches'][:5]:
                            profile = match['profile']
                            st.markdown(f"- **{profile.get('name')}** ({match['score']}%) - {match['reason']}")
                else:
                    st.error(f"Error: {match_result.get('error')}")

# ==========================================
# HELP PAGE
# ==========================================

def show_help():
    """Help and documentation page"""
    st.markdown('<div class="main-header">Help</div>', unsafe_allow_html=True)

    st.markdown("""
    ### How to Use

    **Process Transcripts**
    1. Go to "Process Transcripts" page
    2. Upload your meeting transcript files (.txt, .md, .docx)
    3. Choose processing options (matches per person, save to database)
    4. Click "Process Files"
    5. Download generated reports

    **Browse Directory**
    - Use "Directory" to browse all profiles
    - Use "Search" to find specific people
    - Click "Connect" to add someone to your connections

    **View Matches**
    - "My Matches" shows AI-generated partner recommendations
    - Click "View" to mark as reviewed
    - Click "Contact" to mark as contacted

    **Admin Features** (admins only)
    - Add individual profiles
    - Import profiles from CSV
    - Export directory to CSV
    - Generate match suggestions for all users
    """)

    st.markdown("---")

    st.markdown("""
    ### Frequently Asked Questions

    **What file formats are supported?**
    Text files (.txt), Markdown (.md), and Word documents (.docx).

    **How does matching work?**
    The system analyzes business focus, services, and other profile data
    to find complementary partners with shared interests.

    **Can I import existing contacts?**
    Yes! Admins can import contacts from CSV files in the Admin panel.
    """)

if __name__ == "__main__":
    main()
