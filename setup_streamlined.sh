#!/bin/bash
# Setup script for PAWS Streamlined

set -e

echo "🐾 PAWS Streamlined Setup"
echo "========================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r paws_streamlined_requirements.txt

echo ""
echo "✅ Python dependencies installed"
echo ""

# Make script executable
chmod +x paws_streamlined.py

echo "✅ PAWS Streamlined is ready!"
echo ""
echo "Quick start:"
echo "  python3 paws_streamlined.py --check-tools"
echo "  python3 paws_streamlined.py --audit"
echo ""
echo "To install external tools:"
echo "  - Scout Suite: pip3 install scout-suite"
echo "  - aws-public-ips: pip3 install aws-public-ips"
echo "  - PACU: git clone https://github.com/RhinoSecurityLabs/pacu.git tools/pacu"
echo ""

