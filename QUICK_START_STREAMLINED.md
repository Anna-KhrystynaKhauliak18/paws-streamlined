# PAWS Streamlined - Quick Start Guide

## 🚀 What is PAWS Streamlined?

A simplified, production-ready version of PAWS that:
- ✅ Uses **only external open-source tools** (no internal dependencies)
- ✅ Simple command-line interface (no complex menus)
- ✅ Minimal dependencies (just boto3 + optional rich)
- ✅ Ready to deliver and use immediately

## 📦 Installation

```bash
# Option 1: Use setup script
./setup_streamlined.sh

# Option 2: Manual installation
pip3 install -r paws_streamlined_requirements.txt
chmod +x paws_streamlined.py
```

## 🎯 Basic Usage

### 1. Check Available Tools

```bash
python3 paws_streamlined.py --check-tools
```

This shows which external security tools are installed and ready to use.

### 2. Run Basic Security Audit

```bash
# Basic audit (IAM, S3, EC2 checks)
python3 paws_streamlined.py --audit

# Save results to file
python3 paws_streamlined.py --audit --output audit_results.json
```

### 3. Run External Security Tools

```bash
# Run PACU (AWS penetration testing)
python3 paws_streamlined.py --pacu

# Run Scout Suite (comprehensive AWS audit)
python3 paws_streamlined.py --scout

# Run aws-public-ips (find public resources)
python3 paws_streamlined.py --public-ips

# Run all available tools
python3 paws_streamlined.py --all
```

## 🛠️ Installing External Tools

### Scout Suite (Recommended - Easiest)

```bash
pip3 install scout-suite
```

### aws-public-ips

```bash
pip3 install aws-public-ips
```

### PACU (More Complex)

```bash
# Clone repository
git clone https://github.com/RhinoSecurityLabs/pacu.git tools/pacu

# Install dependencies
cd tools/pacu
pip3 install -r requirements.txt

# Follow PACU README for database setup
```

## 📊 What Gets Checked?

### Basic Audit (using boto3):
- **IAM**: Users without MFA, old access keys (>90 days), password policy
- **S3**: Public access block configuration
- **EC2**: Security groups with open sensitive ports (22, 3389, 3306, 5432)

### External Tools:
- **PACU**: Comprehensive AWS enumeration and security testing
- **Scout Suite**: Multi-cloud security auditing with detailed reports
- **aws-public-ips**: Find all publicly accessible resources

## ⚙️ AWS Configuration

```bash
# Configure AWS credentials
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2

# Or use a profile
python3 paws_streamlined.py --profile production --region us-east-1
```

## 📝 Example Workflow

```bash
# 1. Check what tools are available
python3 paws_streamlined.py --check-tools

# 2. Run basic audit
python3 paws_streamlined.py --audit --output audit_$(date +%Y%m%d).json

# 3. Run Scout Suite for comprehensive report
python3 paws_streamlined.py --scout

# 4. Check for public IPs
python3 paws_streamlined.py --public-ips
```

## 🎯 Key Differences from Full PAWS

| Feature | Full PAWS | Streamlined |
|---------|-----------|-------------|
| Dependencies | Many (rich, inquirer, pandas, etc.) | Minimal (boto3 + optional rich) |
| Interface | Interactive menus | Simple CLI commands |
| Internal modules | Uses custom analysis engines | None - only external tools |
| Complexity | High | Low |
| Setup | Complex | Simple |
| Production Ready | Maybe | Yes ✅ |

## ✅ Why This Version?

1. **No Internal Dependencies**: Removes all custom modules that may have issues
2. **Proven Tools**: Uses well-established open-source security tools
3. **Simple**: Easy to understand and maintain
4. **Deliverable**: Works out of the box
5. **Extensible**: Easy to add more external tools

## 📚 More Information

- Full documentation: `PAWS_STREAMLINED_README.md`
- Requirements: `paws_streamlined_requirements.txt`
- Original PAWS: `paws_cli.py` (for reference)

---

**Ready to use!** Start with `python3 paws_streamlined.py --check-tools`

