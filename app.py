"""
JV Matcher - Streamlit Web Interface
AI-Powered Joint Venture Partner Matching
"""

import streamlit as st
import os
from datetime import datetime
from io import BytesIO
import zipfile

# Import our matching engine
from jv_matcher import JVMatcher

# Page config
st.set_page_config(
    page_title="JV Matcher",
    page_icon="🤝",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="main-header">🤝 JV Matcher</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">AI-Powered Joint Venture Partner Matching System</p>', unsafe_allow_html=True)

# Check API key
api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    st.error("""
    ⚠️ **API Key Not Configured**
    
    To use this app, you need to set your Anthropic API key:
    
    1. Click the ⋮ menu (top right)
    2. Go to **Settings** → **Secrets**
    3. Add this line:
    
    ```
    ANTHROPIC_API_KEY = "sk-ant-your-key-here"
    ```
    
    Get your API key at: https://console.anthropic.com/settings/keys
    """)
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("### 📊 About JV Matcher")
    st.markdown("""
    Upload meeting transcripts and chat logs to automatically:
    
    - 📝 Extract participant profiles
    - 🤝 Find ideal JV partners
    - 📄 Generate personalized reports
    - 📧 Create ready-to-send messages
    """)
    
    st.markdown("---")
    st.markdown("### 💡 How It Works")
    st.markdown("""
    1. Upload transcript & chat files
    2. AI extracts all participant profiles
    3. System finds best matches for each person
    4. Download personalized reports
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Tips")
    st.markdown("""
    - Upload multiple files at once
    - Processing takes 5-15 minutes
    - Each person gets top 10 matches
    - Reports include ready-to-send messages
    """)

# Main tabs
tab1, tab2 = st.tabs(["📤 Process Files", "📊 View Results"])

# ==================== TAB 1: PROCESS FILES ====================
with tab1:
    st.header("📤 Upload & Process Files")
    
    st.info("""
    **📁 Supported Formats:** .txt, .md, .docx (text files from Zoom)
    
    **💡 Tip:** You can upload multiple transcript files and multiple chat files at once!
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1️⃣ Transcript Files")
        transcript_files = st.file_uploader(
            "Upload meeting transcripts (can select multiple)",
            type=['txt', 'md', 'docx'],
            accept_multiple_files=True,
            key='transcripts',
            help="The closed caption / transcript files from Zoom"
        )
        if transcript_files:
            st.success(f"✅ {len(transcript_files)} transcript file(s) uploaded")
            for f in transcript_files:
                st.text(f"  📄 {f.name}")
    
    with col2:
        st.subheader("2️⃣ Chat Log Files")
        chat_files = st.file_uploader(
            "Upload chat logs (can select multiple)",
            type=['txt', 'md', 'docx'],
            accept_multiple_files=True,
            key='chats',
            help="The saved chat files from Zoom"
        )
        if chat_files:
            st.success(f"✅ {len(chat_files)} chat file(s) uploaded")
            for f in chat_files:
                st.text(f"  💬 {f.name}")
    
    st.markdown("---")
    
    # Processing options
    st.subheader("⚙️ Processing Options")
    num_matches = st.slider(
        "Number of matches per person",
        min_value=3,
        max_value=15,
        value=10,
        help="How many top matches to generate for each participant"
    )
    
    # Process button
    st.markdown("---")
    
    if transcript_files and chat_files:
        if st.button("🚀 Process Files & Generate Matches", type="primary", use_container_width=True):
            
            # Create progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialize matcher
                status_text.text("🔧 Initializing AI matcher...")
                progress_bar.progress(5)
                
                matcher = JVMatcher(api_key=api_key)
                
                # Process files
                status_text.text("📊 Processing files and extracting profiles...")
                progress_bar.progress(10)
                
                results = matcher.process_files(
                    transcript_files,
                    chat_files,
                    num_matches=num_matches
                )
                
                progress_bar.progress(90)
                
                # Generate reports
                status_text.text("📝 Generating reports...")
                
                reports = {}
                for name, data in results.items():
                    reports[name] = matcher.generate_report(name, data)
                
                progress_bar.progress(100)
                status_text.text("✅ Processing complete!")
                
                # Save to session state
                st.session_state['results'] = results
                st.session_state['reports'] = reports
                st.session_state['processed_at'] = datetime.now()
                
                # Success message
                st.balloons()
                
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown(f"""
                ### 🎉 Processing Complete!
                
                - **Participants processed:** {len(results)}
                - **Total matches generated:** {sum(r['match_count'] for r in results.values())}
                - **Average match score:** {sum(m['score'] for r in results.values() for m in r['matches']) / max(sum(r['match_count'] for r in results.values()), 1):.1f}/100
                
                **👉 Go to the "View Results" tab to download reports!**
                """)
                st.markdown('</div>', unsafe_allow_html=True)
                
            except Exception as e:
                progress_bar.progress(0)
                status_text.text("")
                st.error(f"""
                ❌ **Error processing files:**
                
                ```
                {str(e)}
                ```
                
                **Troubleshooting:**
                - Make sure your API key is valid
                - Check that you have API credits
                - Verify files are from Zoom (transcripts and chats)
                - Try with smaller files first
                """)
    else:
        st.info("👆 Upload both transcript and chat files to get started")

# ==================== TAB 2: VIEW RESULTS ====================
with tab2:
    st.header("📊 View Results")
    
    if 'results' in st.session_state and 'reports' in st.session_state:
        results = st.session_state['results']
        reports = st.session_state['reports']
        processed_at = st.session_state.get('processed_at', datetime.now())
        
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Participants", len(results))
        
        with col2:
            total_matches = sum(r['match_count'] for r in results.values())
            st.metric("Total Matches", total_matches)
        
        with col3:
            avg_matches = total_matches / len(results) if results else 0
            st.metric("Avg Matches/Person", f"{avg_matches:.1f}")
        
        with col4:
            all_scores = [m['score'] for r in results.values() for m in r['matches']]
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
            st.metric("Avg Match Score", f"{avg_score:.1f}/100")
        
        st.caption(f"Processed: {processed_at.strftime('%B %d, %Y at %I:%M %p')}")
        
        st.markdown("---")
        
        # Download all reports
        st.subheader("📥 Download Reports")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create ZIP file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for name, report in reports.items():
                    safe_name = name.replace(' ', '_').replace('/', '_')
                    filename = f"{safe_name}_JV_Report.md"
                    zip_file.writestr(filename, report)
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="📦 Download All Reports (ZIP)",
                data=zip_buffer,
                file_name=f"JV_Reports_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        
        with col2:
            st.info(f"**{len(reports)}** reports ready")
        
        st.markdown("---")
        
        # View individual report
        st.subheader("👤 View Individual Report")
        
        selected_person = st.selectbox(
            "Select participant",
            sorted(reports.keys())
        )
        
        if selected_person:
            # Show summary
            person_data = results[selected_person]
            profile = person_data['profile']
            
            with st.expander("📋 Profile Summary", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**What they do:**")
                    st.write(profile.get('what_they_do', 'N/A'))
                with col2:
                    st.markdown(f"**Who they serve:**")
                    st.write(profile.get('who_they_serve', 'N/A'))
                
                st.markdown(f"**Number of matches:** {person_data['match_count']}")
            
            # Show matches
            st.markdown("### 🤝 Top Matches")
            
            for i, match in enumerate(person_data['matches'], 1):
                with st.expander(f"Match #{i}: {match.get('partner_name', 'Unknown')} - Score: {match.get('score', 0)}/100"):
                    st.markdown(f"**Match Type:** {match.get('match_type', 'N/A')}")
                    st.markdown(f"**Why Good Fit:** {match.get('why_good_fit', 'N/A')}")
                    st.markdown(f"**Collaboration Opportunity:** {match.get('collaboration_opportunity', 'N/A')}")
                    
                    st.markdown("**Ready-to-Send Message:**")
                    st.code(match.get('first_outreach_message', 'N/A'), language=None)
                    
                    st.markdown(f"**Contact:** {match.get('contact_method', 'N/A')}")
            
            # Download this report
            st.markdown("---")
            st.download_button(
                label=f"📄 Download {selected_person}'s Report",
                data=reports[selected_person],
                file_name=f"{selected_person.replace(' ', '_')}_JV_Report.md",
                mime="text/markdown"
            )
    
    else:
        st.info("📤 No results yet. Process some files in the 'Process Files' tab first!")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p><strong>JV Matcher</strong> - AI-Powered Partnership Matching</p>
    <p>Powered by Claude AI | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
