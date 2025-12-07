#!/bin/bash
# Quick script to push JV Matcher to GitHub

echo "🚀 Setting up GitHub repository for JV Matcher"
echo ""

# Check if GitHub CLI is installed
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI detected!"
    echo ""
    read -p "Enter your GitHub username: " GITHUB_USER
    read -p "Enter repository name (default: jv-matcher): " REPO_NAME
    REPO_NAME=${REPO_NAME:-jv-matcher}
    
    echo ""
    echo "Creating repository: $GITHUB_USER/$REPO_NAME"
    gh repo create "$REPO_NAME" --public --source=. --remote=origin --push
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Success! Repository created and pushed to GitHub"
        echo "🌐 Repository URL: https://github.com/$GITHUB_USER/$REPO_NAME"
        echo ""
        echo "Next steps:"
        echo "1. Go to https://share.streamlit.io"
        echo "2. Click 'New app'"
        echo "3. Select repository: $GITHUB_USER/$REPO_NAME"
        echo "4. Set main file to: app.py"
        echo "5. Click 'Deploy'"
    else
        echo "❌ Error creating repository. Please do it manually."
    fi
else
    echo "📝 GitHub CLI not found. Manual setup required:"
    echo ""
    echo "1. Create repository on GitHub.com:"
    echo "   - Go to https://github.com/new"
    echo "   - Name: jv-matcher"
    echo "   - Make it Public"
    echo "   - Don't initialize with README"
    echo ""
    echo "2. Then run these commands:"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/jv-matcher.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
    echo "3. Deploy on Streamlit Cloud:"
    echo "   - Go to https://share.streamlit.io"
    echo "   - Click 'New app'"
    echo "   - Select your repository"
    echo "   - Set main file to: app.py"
    echo "   - Click 'Deploy'"
fi




