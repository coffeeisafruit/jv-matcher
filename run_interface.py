#!/usr/bin/env python3
"""
Easy launcher for the JV Matcher web interface
"""
import subprocess
import sys
import os

def main():
    """Launch Streamlit interface"""
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    # Launch Streamlit
    print("🚀 Launching JV Matcher web interface...")
    print("📝 The browser will open automatically")
    print("🛑 Press Ctrl+C to stop the server")
    print("")
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])

if __name__ == "__main__":
    main()




