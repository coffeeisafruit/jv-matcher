# 🤝 JV Matcher - AI-Powered Joint Venture Partner Matching System

A beautiful, professional web application for matching people with ideal joint venture partners based on meeting transcripts.

## 🚀 Features

- **📤 Drag & Drop Upload** - Easy file upload interface
- **🤖 AI-Powered Matching** - Intelligent partner matching algorithm
- **📊 Visual Dashboard** - Real-time progress tracking and statistics
- **📥 One-Click Downloads** - Get all reports in a ZIP file
- **💼 Professional Reports** - Ready-to-email personalized reports

## 📋 Requirements

- Python 3.8+
- Streamlit
- Pandas

## 🛠️ Installation

```bash
pip install -r requirements.txt
```

## 🎯 Quick Start

### Local Development

```bash
python run_interface.py
```

Or directly:

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 📁 Project Structure

```
.
├── app.py                    # Streamlit web interface
├── jv_matcher.py            # Core matching engine
├── run_interface.py          # Easy launcher script
├── requirements.txt         # Python dependencies
├── QUICKSTART.md            # Quick start guide
├── WEB_INTERFACE_GUIDE.md   # Complete user guide
└── outputs/                 # Generated reports (created automatically)
```

## 🚀 Streamlit Cloud Deployment

This app is ready to deploy on [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository
5. Set main file to `app.py`
6. Deploy!

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in minutes
- **[WEB_INTERFACE_GUIDE.md](WEB_INTERFACE_GUIDE.md)** - Complete user guide
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - System overview

## 💡 Usage

1. Upload meeting transcript files (.txt, .md, .docx)
2. Configure processing options (matches per person, output format)
3. Click "Process Files" and watch the progress
4. Download ZIP file with all personalized reports
5. Email reports to customers

## 🎨 Interface

The app features:
- Beautiful, professional UI
- Multi-page navigation (Home, Process Files, View Results, Help)
- Real-time progress tracking
- Visual statistics dashboard
- Built-in help documentation

## 📝 License

Private project - All rights reserved

## 👥 Author

Built for JV matching system

---

**Ready to match JV partners? Launch the app and get started!** 🚀
