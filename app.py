#!/usr/bin/env python3
"""
JV Matcher - Streamlit Web Interface
Beautiful, professional web interface for JV matching system
"""
import streamlit as st
import os
import tempfile
from pathlib import Path
import time
from jv_matcher import JVMatcher

# Page configuration
st.set_page_config(
    page_title="JV Matcher - Partner Matching System",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
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
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #155a8a;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results' not in st.session_state:
    st.session_state.results = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

def main():
    # Header
    st.markdown('<div class="main-header">🤝 JV Matcher</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Joint Venture Partner Matching System</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Navigation")
        page = st.radio(
            "Choose a page:",
            ["🏠 Home", "📤 Process Files", "📊 View Results", "❓ Help"]
        )
        
        st.markdown("---")
        st.header("ℹ️ Quick Info")
        st.info("""
        **What this does:**
        - Upload meeting transcripts
        - Extract participant profiles
        - Find ideal JV partners
        - Generate personalized reports
        """)
    
    # Route to appropriate page
    if page == "🏠 Home":
        show_home()
    elif page == "📤 Process Files":
        show_process_files()
    elif page == "📊 View Results":
        show_results()
    elif page == "❓ Help":
        show_help()

def show_home():
    """Home page with overview"""
    st.markdown("## Welcome to JV Matcher!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="stat-box">
            <h3>📤 Upload</h3>
            <p>Drag & drop your meeting transcript files</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="stat-box">
            <h3>🤖 Process</h3>
            <p>AI extracts profiles and finds matches</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="stat-box">
            <h3>📥 Download</h3>
            <p>Get personalized reports in one click</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## 🚀 How It Works")
    
    steps = [
        ("1️⃣ Upload Files", "Upload one or more meeting transcript files. Supports .txt, .md, and other text formats."),
        ("2️⃣ Process", "Click the 'Process Files' button. Our AI will extract profiles from each participant and analyze their interests."),
        ("3️⃣ Match", "The system finds 5-10 ideal JV partners for each person based on shared interests and complementary skills."),
        ("4️⃣ Download", "Get a ZIP file with personalized reports for each participant, ready to email to your customers.")
    ]
    
    for step_num, description in steps:
        st.markdown(f"### {step_num}")
        st.markdown(description)
        st.markdown("")
    
    st.markdown("---")
    
    st.markdown("## 💡 Key Features")
    
    features = [
        "✅ **Zero technical knowledge needed** - Just drag, drop, and click",
        "✅ **Handles large files** - Processes 2-3 hour meetings with ease",
        "✅ **Batch processing** - Process multiple profiles at once",
        "✅ **Professional reports** - Ready-to-send personalized reports",
        "✅ **Visual progress tracking** - See exactly what's happening",
        "✅ **One-click downloads** - Get all reports in a single ZIP file"
    ]
    
    for feature in features:
        st.markdown(feature)
    
    st.markdown("---")
    
    if st.button("🚀 Get Started - Process Files Now", use_container_width=True):
        st.session_state.page = "📤 Process Files"
        st.rerun()

def show_process_files():
    """File upload and processing page"""
    st.markdown("## 📤 Upload & Process Files")
    
    st.markdown("""
    <div class="info-box">
        <strong>📝 Supported Formats:</strong> .txt, .md, .docx, and other text files<br>
        <strong>💡 Tip:</strong> You can upload multiple files at once for batch processing
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
        st.markdown(f"### ✅ {len(uploaded_files)} file(s) uploaded")
        
        # Show uploaded files
        with st.expander("📋 View Uploaded Files", expanded=True):
            for i, file in enumerate(uploaded_files, 1):
                st.markdown(f"**{i}. {file.name}** ({file.size:,} bytes)")
        
        # Processing options
        st.markdown("### ⚙️ Processing Options")
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
            output_format = st.selectbox(
                "Output format",
                ["Markdown (.md)", "PDF", "HTML"],
                help="Format for the generated reports"
            )
        
        # Process button
        st.markdown("")
        if st.button("🚀 Process Files", type="primary", use_container_width=True):
            process_files(uploaded_files, matches_per_person)
    
    else:
        st.info("👆 Please upload one or more transcript files to get started")

def process_files(uploaded_files, matches_per_person):
    """Process uploaded files"""
    st.session_state.processing = True
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Save uploaded files to temporary directory
        temp_dir = tempfile.mkdtemp()
        file_paths = []
        
        status_text.text("📥 Saving uploaded files...")
        progress_bar.progress(10)
        
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            file_paths.append(file_path)
        
        status_text.text("🤖 Extracting profiles from transcripts...")
        progress_bar.progress(30)
        
        # Initialize matcher
        matcher = JVMatcher(output_dir="outputs")
        
        status_text.text("🔍 Finding JV partner matches...")
        progress_bar.progress(50)
        
        # Process files
        results = matcher.process_files(file_paths, matches_per_person=matches_per_person)
        
        status_text.text("📝 Generating reports...")
        progress_bar.progress(80)
        
        status_text.text("✅ Processing complete!")
        progress_bar.progress(100)
        
        # Store results
        st.session_state.results = results
        st.session_state.processing = False
        
        # Show success message
        st.markdown("""
        <div class="success-box">
            <h3>✅ Processing Complete!</h3>
            <p><strong>Total Profiles:</strong> {}</p>
            <p><strong>Reports Generated:</strong> {}</p>
        </div>
        """.format(results['total_profiles'], results['total_reports']), unsafe_allow_html=True)
        
        # Show download button
        if os.path.exists(results['zip_path']):
            with open(results['zip_path'], 'rb') as f:
                st.download_button(
                    label="📥 Download All Reports (ZIP)",
                    data=f.read(),
                    file_name=os.path.basename(results['zip_path']),
                    mime="application/zip",
                    use_container_width=True
                )
        
        st.markdown("---")
        st.markdown("### 📊 Processing Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Profiles", results['total_profiles'])
        with col2:
            st.metric("Reports Generated", results['total_reports'])
        with col3:
            st.metric("Matches per Person", matches_per_person)
        
        # Show individual reports
        st.markdown("### 📄 Generated Reports")
        for i, report_path in enumerate(results['reports'], 1):
            report_name = os.path.basename(report_path)
            if os.path.exists(report_path):
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                
                with st.expander(f"📄 {report_name}"):
                    st.markdown(report_content)
                    
                    # Download button for individual report
                    st.download_button(
                        label=f"📥 Download {report_name}",
                        data=report_content,
                        file_name=report_name,
                        mime="text/markdown",
                        key=f"download_{i}"
                    )
        
    except Exception as e:
        st.error(f"❌ Error processing files: {str(e)}")
        st.session_state.processing = False
        progress_bar.empty()
        status_text.empty()

def show_results():
    """Results viewing page"""
    st.markdown("## 📊 View Results")
    
    if st.session_state.results:
        results = st.session_state.results
        
        st.markdown("### ✅ Latest Processing Results")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Profiles", results['total_profiles'])
        with col2:
            st.metric("Reports Generated", results['total_reports'])
        with col3:
            st.metric("Output Directory", os.path.basename(results['reports_dir']))
        
        # Download ZIP
        if os.path.exists(results['zip_path']):
            st.markdown("### 📥 Download Reports")
            with open(results['zip_path'], 'rb') as f:
                st.download_button(
                    label="📥 Download All Reports (ZIP)",
                    data=f.read(),
                    file_name=os.path.basename(results['zip_path']),
                    mime="application/zip",
                    use_container_width=True
                )
        
        # List all reports
        st.markdown("### 📄 Individual Reports")
        for report_path in results['reports']:
            if os.path.exists(report_path):
                report_name = os.path.basename(report_path)
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                
                with st.expander(f"📄 {report_name}"):
                    st.markdown(report_content)
    else:
        st.info("👆 No results yet. Process some files first!")

def show_help():
    """Help and documentation page"""
    st.markdown("## ❓ Help & Documentation")
    
    st.markdown("### 📖 How to Use")
    
    st.markdown("""
    **Step 1: Upload Files**
    - Go to the "Process Files" page
    - Drag and drop your transcript files (or click to browse)
    - Supported formats: .txt, .md, .docx
    
    **Step 2: Configure Options**
    - Choose how many matches you want per person (5-20)
    - Select output format (Markdown, PDF, or HTML)
    
    **Step 3: Process**
    - Click the "Process Files" button
    - Watch the progress bar as files are processed
    - Wait for completion (usually 1-2 minutes)
    
    **Step 4: Download**
    - Click "Download All Reports (ZIP)" to get everything at once
    - Or download individual reports from the list
    - Reports are ready to email to your customers
    """)
    
    st.markdown("---")
    
    st.markdown("### ❓ Frequently Asked Questions")
    
    faqs = [
        ("How long does processing take?", "Typically 1-2 minutes for a single file with 5-10 participants. Larger files may take longer."),
        ("What file formats are supported?", "Text files (.txt), Markdown (.md), and Word documents (.docx). For best results, use plain text transcripts."),
        ("How many people can I process at once?", "There's no hard limit. The system can handle 100+ profiles in a single batch."),
        ("Can I process multiple files?", "Yes! Upload multiple files and they'll all be processed together."),
        ("What if a file is too large?", "The system automatically chunks large files. Files up to 300+ pages are handled automatically."),
        ("How accurate are the matches?", "Matches are based on keyword analysis and shared interests. For production use, consider integrating with advanced AI models."),
    ]
    
    for question, answer in faqs:
        with st.expander(f"❓ {question}"):
            st.markdown(answer)
    
    st.markdown("---")
    
    st.markdown("### 🆘 Troubleshooting")
    
    st.markdown("""
    **Problem: Files won't upload**
    - Check file format (must be .txt, .md, or .docx)
    - Ensure file size is reasonable (< 50MB)
    
    **Problem: Processing fails**
    - Check that files contain readable text
    - Ensure transcripts have speaker names or clear structure
    - Try processing one file at a time
    
    **Problem: No matches found**
    - Ensure transcripts contain multiple speakers
    - Check that content is substantial (not just a few words)
    - Try adjusting the number of matches per person
    """)
    
    st.markdown("---")
    
    st.markdown("### 📞 Support")
    
    st.markdown("""
    For additional help or questions:
    - Check the documentation in the sidebar
    - Review the FAQ section above
    - Contact your system administrator
    """)

if __name__ == "__main__":
    main()

