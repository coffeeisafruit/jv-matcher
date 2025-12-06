# JV Matcher - Web Interface Guide

Complete guide to using the JV Matcher web interface.

## 🚀 Quick Start

### Launch the Interface

```bash
python run_interface.py
```

The browser will open automatically to `http://localhost:8501`

### Basic Usage

1. **Upload Files** - Drag & drop transcript files
2. **Click Process** - Watch the progress bar
3. **Download ZIP** - Get all reports in one click
4. **Done!** - Email reports to customers

**Total time: ~15 minutes hands-on**

---

## 📋 Detailed Instructions

### Step 1: Upload Files

1. Navigate to the **"📤 Process Files"** page
2. Click the file upload area or drag & drop files
3. Supported formats:
   - `.txt` - Plain text files
   - `.md` - Markdown files
   - `.docx` - Word documents

**Tips:**
- Upload multiple files at once for batch processing
- Files should contain meeting transcripts with speaker names
- Larger files (2-3 hours) are handled automatically

### Step 2: Configure Options

**Number of Matches:**
- Default: 10 matches per person
- Range: 5-20 matches
- Higher numbers = more recommendations (but may be less relevant)

**Output Format:**
- Markdown (.md) - Recommended, easy to read
- PDF - Professional format
- HTML - Web-friendly format

### Step 3: Process Files

1. Click the **"🚀 Process Files"** button
2. Watch the progress bar:
   - 📥 Saving files (10%)
   - 🤖 Extracting profiles (30%)
   - 🔍 Finding matches (50%)
   - 📝 Generating reports (80%)
   - ✅ Complete (100%)

**Processing Time:**
- Small files (< 10 people): ~30 seconds
- Medium files (10-50 people): ~1-2 minutes
- Large files (50+ people): ~3-5 minutes

### Step 4: Download Reports

**Option 1: Download All (Recommended)**
- Click **"📥 Download All Reports (ZIP)"**
- Get everything in one file
- Extract and email individual reports

**Option 2: Download Individual Reports**
- Expand any report to view it
- Click **"📥 Download [filename]"** for that specific report
- Useful for sending one report at a time

---

## 🎨 Interface Features

### Navigation

**🏠 Home**
- Overview of the system
- Quick start guide
- Feature highlights

**📤 Process Files**
- File upload
- Processing options
- Main workflow

**📊 View Results**
- View latest results
- Download reports
- Browse individual reports

**❓ Help**
- Complete documentation
- FAQ section
- Troubleshooting guide

### Visual Elements

**Progress Bar**
- Real-time processing status
- Percentage complete
- Current operation shown

**Statistics Dashboard**
- Total profiles processed
- Reports generated
- Processing metrics

**Report Preview**
- View reports before downloading
- Markdown formatting
- Easy to read

---

## 💡 Tips & Best Practices

### File Preparation

1. **Speaker Names**: Include speaker names in transcripts
   - Format: `John: Hello everyone...`
   - Or: `Speaker 1: ...`

2. **File Size**: 
   - Small files (< 1MB): Process quickly
   - Large files (1-10MB): May take 2-3 minutes
   - Very large files (> 10MB): Consider splitting

3. **Content Quality**:
   - More content = better matches
   - Include full conversations, not summaries
   - 2-3 hour meetings work best

### Processing Tips

1. **Batch Processing**:
   - Upload all files at once
   - Process together for consistency
   - Faster than processing individually

2. **Match Count**:
   - Start with 10 matches (default)
   - Increase if you want more options
   - Decrease for higher quality matches

3. **Output Format**:
   - Markdown works best for most cases
   - PDF for formal presentations
   - HTML for web embedding

### Workflow Optimization

**For Regular Use:**
1. Create a folder for each batch
2. Upload all files at once
3. Process and download ZIP
4. Extract to organized folders
5. Email reports to customers

**For Large Batches:**
1. Process in groups of 10-20 files
2. Download ZIP after each group
3. Keep track of processed files
4. Archive old reports

---

## 🔧 Troubleshooting

### Common Issues

**Problem: Files won't upload**
- ✅ Check file format (.txt, .md, .docx)
- ✅ Ensure file size < 50MB
- ✅ Try refreshing the page

**Problem: Processing fails**
- ✅ Check file contains readable text
- ✅ Ensure transcripts have speaker names
- ✅ Try processing one file at a time

**Problem: No matches found**
- ✅ Verify multiple speakers in transcript
- ✅ Check content is substantial (not just a few words)
- ✅ Try increasing match count

**Problem: Browser won't open**
- ✅ Manually navigate to `http://localhost:8501`
- ✅ Check firewall settings
- ✅ Try a different browser

### Error Messages

**"Error extracting profiles"**
- Transcript may not have clear speaker separation
- Try reformatting with speaker names

**"No profiles found"**
- File may be empty or corrupted
- Check file content before uploading

**"Processing timeout"**
- File may be too large
- Try splitting into smaller files

---

## 📊 Understanding Results

### Report Structure

Each report contains:

1. **Profile Summary**
   - Name
   - Content length
   - Key interests

2. **Top Matches** (5-20 depending on settings)
   - Match score (percentage)
   - Why this match (reasoning)
   - Shared interests
   - Profile summary

3. **Next Steps**
   - Action items
   - How to connect
   - Best practices

### Match Scores

- **80-100%**: Excellent match, high compatibility
- **60-79%**: Good match, worth exploring
- **40-59%**: Moderate match, may have potential
- **< 40%**: Weak match, less likely to succeed

### Interpreting Results

**High Match Score + Shared Interests**
- Strong potential for collaboration
- Easy conversation starter
- Likely to resonate

**Moderate Match + Complementary Skills**
- Different but complementary
- May create unique opportunities
- Worth exploring

---

## 🎯 Use Cases

### For Event Organizers

1. Upload recordings from weekly events
2. Process all participants at once
3. Generate reports for each person
4. Email reports as value-add service

### For Business Development

1. Upload client meeting transcripts
2. Find potential JV partners
3. Generate personalized recommendations
4. Use in sales conversations

### For Networking Groups

1. Process member profiles
2. Create connection opportunities
3. Facilitate introductions
4. Increase engagement

---

## 📞 Support

For additional help:
- Check the **Help** page in the interface
- Review FAQ section
- Contact your system administrator

---

## 🚀 Advanced Features

### Custom Processing

The system automatically:
- Extracts speaker profiles
- Identifies key interests
- Calculates similarity scores
- Generates match reasons

### Batch Operations

- Process unlimited files
- Generate reports for all participants
- Create organized ZIP downloads
- Track processing statistics

---

**Last Updated:** 2024
**Version:** 1.0

