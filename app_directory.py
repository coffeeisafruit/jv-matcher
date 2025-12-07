#!/usr/bin/env python3
"""
JV Directory - Streamlit Web Application
Full-featured directory with authentication and database backend
Schema v2: Unified profiles (contacts = profiles)
"""
import streamlit as st
import pandas as pd
from auth_service import AuthService, init_session_state
from directory_service import DirectoryService
from match_generator import MatchGenerator, AIMatchGenerator, OPENAI_AVAILABLE

# Page configuration
st.set_page_config(
    page_title="JV Directory",
    page_icon="📇",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
</style>
""", unsafe_allow_html=True)

# Initialize services
auth_service = AuthService()

def main():
    init_session_state()

    # Check for existing session
    if not st.session_state.authenticated:
        show_auth_page()
    else:
        show_main_app()

# ==========================================
# AUTHENTICATION PAGES
# ==========================================

def show_auth_page():
    """Show login/signup page"""
    st.markdown('<div class="main-header">📇 JV Directory</div>', unsafe_allow_html=True)
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
                    # Get the profile linked to this auth user
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

        pages = ["Dashboard", "Directory", "Search", "My Matches", "My Connections"]
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
    elif page == "My Matches":
        show_matches()
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

    # My Profile Summary
    user_profile = st.session_state.user_profile or {}
    st.markdown("### My Profile")

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
                if st.button("← Previous"):
                    st.session_state.dir_page -= 1
                    st.rerun()
        with col3:
            if st.session_state.dir_page < total_pages - 1:
                if st.button("Next →"):
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

    # Filter by status
    status_filter = st.selectbox("Filter", ["All", "pending", "viewed", "contacted", "connected", "dismissed"])

    matches = directory_service.get_match_suggestions(
        user_profile['id'],
        status=status_filter if status_filter != "All" else None
    )

    if matches:
        st.markdown(f"**{len(matches)} matches**")

        for match in matches:
            suggested = match.get('suggested', {})
            if not suggested:
                continue

            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.markdown(f"**{suggested.get('name', 'Unknown')}**")
                    if suggested.get('company'):
                        st.caption(suggested['company'])

                with col2:
                    score = match.get('match_score', 0)
                    st.markdown(f'<span class="match-score">{score}% match</span>', unsafe_allow_html=True)
                    st.caption(f"Status: {match.get('status', 'pending')}")

                with col3:
                    if match.get('status') == 'pending':
                        if st.button("View", key=f"view_{match['id']}"):
                            directory_service.update_match_status(match['id'], 'viewed')
                            st.rerun()
                    elif match.get('status') == 'viewed':
                        if st.button("Contact", key=f"contact_{match['id']}"):
                            directory_service.update_match_status(match['id'], 'contacted')
                            st.rerun()

                if match.get('match_reason'):
                    st.caption(f"Why: {match['match_reason']}")

                st.markdown("---")
    else:
        st.info("No match suggestions yet. Check back after matches are generated.")

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
    """Generate match suggestions using keyword or AI matching"""
    st.markdown("### Generate Match Suggestions")

    # Matching mode selection
    import os
    has_api_key = bool(os.getenv("OPENROUTER_API_KEY"))

    matching_mode = st.radio(
        "Matching Mode",
        ["Keyword Matching (Fast)", "AI Matching (Higher Quality)"],
        help="Keyword matching is fast and free. AI matching uses OpenRouter API for better results."
    )

    use_ai = matching_mode == "AI Matching (Higher Quality)"

    if use_ai and not has_api_key:
        st.warning("AI matching requires OPENROUTER_API_KEY in environment. Using keyword matching.")
        use_ai = False

    if use_ai:
        st.info("AI matching analyzes profiles and generates personalized outreach messages.")
    else:
        st.info("Keyword matching analyzes business_focus, service_provided, and company fields.")

    col1, col2 = st.columns(2)
    with col1:
        top_n = st.number_input("Matches per profile", min_value=1, max_value=50, value=10)
    with col2:
        if not use_ai:
            min_score = st.slider("Minimum match score (%)", min_value=0, max_value=50, value=15)
        else:
            min_score = 60  # AI matcher has built-in threshold
            st.info("AI matcher uses 60% threshold")

    only_registered = st.checkbox("Only generate for registered users", value=use_ai)

    st.markdown("---")

    if st.button("Generate Matches for All Users", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Fetching profiles...")

        with st.spinner("Generating matches... This may take a few minutes."):
            if use_ai:
                generator = AIMatchGenerator()
                result = generator.generate_all_matches(
                    top_n=top_n,
                    only_registered=only_registered
                )
            else:
                generator = MatchGenerator()
                result = generator.generate_all_matches(
                    top_n=top_n,
                    min_score=float(min_score),
                    only_registered=only_registered
                )

        progress_bar.progress(100)

        if result['success']:
            st.success(f"Match generation complete!")
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

    # Search for a user
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


if __name__ == "__main__":
    main()
