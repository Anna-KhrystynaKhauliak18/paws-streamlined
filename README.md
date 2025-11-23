# PAWS Streamlined

## 🎯 Professional AWS Security - Streamlined Version

A simplified, production-ready AWS security tool that uses **only external open-source tools**. This streamlined version removes all internal dependencies and focuses on integrating proven security tools.

## ✨ Features

- **Basic Security Audits**: IAM, S3, EC2 checks using boto3
- **External Tool Integration**: PACU, Scout Suite, CloudMapper, aws-public-ips
- **Simple CLI Interface**: No complex menus, just commands
- **Minimal Dependencies**: Only boto3 and optional rich formatting
- **Production Ready**: Works out of the box

## 🚀 Quick Start

### Installation

```bash
# Option 1: Use setup script
./setup_streamlined.sh

# Option 2: Manual installation
pip3 install -r paws_streamlined_requirements.txt
chmod +x paws_streamlined.py
```

### Basic Usage

```bash
# Check which tools are available
python3 paws_streamlined.py --check-tools

# Run basic security audit (IAM, S3, EC2)
python3 paws_streamlined.py --audit

# Run PACU
python3 paws_streamlined.py --pacu

# Run Scout Suite
python3 paws_streamlined.py --scout

# Run all available tools
python3 paws_streamlined.py --all
```

## 📚 Documentation

- **[Quick Start Guide](QUICK_START_STREAMLINED.md)** - Get started in minutes
- **[Complete README](PAWS_STREAMLINED_README.md)** - Full documentation
- **[Tool Comparison](TOOL_COMPARISON.md)** - Understand tool differences
- **[Delivery Checklist](DELIVERY_CHECKLIST.md)** - Quality assurance

## 🛠️ External Tools

This tool integrates with:
- **PACU** - AWS penetration testing framework
- **Scout Suite** - Multi-cloud security auditing
- **CloudMapper** - AWS infrastructure visualization
- **aws-public-ips** - Public IP enumeration (optional)

See [TOOL_COMPARISON.md](TOOL_COMPARISON.md) for details.

## 📋 Requirements

- Python 3.7+
- boto3 (AWS SDK)
- rich (optional, for better terminal output)
- AWS credentials configured

## ⚙️ Configuration

Configure AWS credentials using standard methods:

```bash
# Using AWS CLI
aws configure

# Using environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2

# Using profile
python3 paws_streamlined.py --profile production --region us-east-1
```

## 📊 What Gets Checked?

### Basic Audit (using boto3):
- **IAM**: Users without MFA, old access keys (>90 days), password policy
- **S3**: Public access block configuration
- **EC2**: Security groups with open sensitive ports (22, 3389, 3306, 5432)

### External Tools:
- **PACU**: Comprehensive AWS enumeration and security testing
- **Scout Suite**: Multi-cloud security auditing with detailed reports
- **CloudMapper**: Infrastructure visualization and security analysis
- **aws-public-ips**: Find all publicly accessible resources

## 📝 Reporting Outputs

- JSON reports are saved via `--output` (e.g., `audit.json`)
- A PDF report is generated automatically for every audit
  - Default path: `audit_report.pdf`
  - Customize with `--pdf-output /path/report.pdf`
- JSON output now includes `score_breakdown` entries so you can see every deduction applied to the 100-point baseline.
- PDF output includes a **Score Explanation** section plus a detailed findings table (service, item, severity, details).
- PDF report also contains a **Scoring Methodology** section detailing the exact deductions (MFA, old keys, password policy) used on the 100-point scale.
- Compliance profiles (CIS AWS Foundations, NIST CSF, PCI DSS) are evaluated automatically unless you specify `--standards`. Each profile lists pass/fail per control in both JSON (`standards` field) and the PDF’s **Compliance Profiles** tables.

Example:

```bash
python3 paws_streamlined.py --audit --output audit.json --pdf-output reports/security_report.pdf

# Evaluate only CIS controls
python3 paws_streamlined.py --audit --standards cis

# Run CIS + NIST with explicit output paths
python3 paws_streamlined.py --audit --standards cis nist \
  --output reports/cis_nist.json \
  --pdf-output reports/cis_nist.pdf
```

PDF generation uses ReportLab (installed via `pip install -r paws_streamlined_requirements.txt`).

## 🎯 Key Differences from Full PAWS

| Feature | Full PAWS | Streamlined |
|---------|-----------|-------------|
| Dependencies | Many | Minimal (boto3 + optional rich) |
| Interface | Interactive menus | Simple CLI commands |
| Internal modules | Uses custom analysis engines | None - only external tools |
| Complexity | High | Low |
| Setup | Complex | Simple |
| Production Ready | Maybe | Yes ✅ |

## 📝 License

Same as main project.

## 🤝 Contributing

This streamlined version focuses on stability and external tool integration. Contributions welcome!

---

**PAWS Streamlined** - Simple, focused, production-ready AWS security.

