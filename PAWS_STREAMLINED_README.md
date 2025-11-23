# PAWS Streamlined - Professional AWS Security

## 🎯 Overview

PAWS Streamlined is a simplified, production-ready AWS security tool that uses **only external open-source tools**. It removes all internal dependencies and focuses on integrating proven security tools.

## ✨ Features

- **Basic Security Audits**: IAM, S3, EC2 checks using boto3
- **External Tool Integration**: PACU, Scout Suite, aws-public-ips
- **Simple CLI Interface**: No complex menus, just commands
- **Minimal Dependencies**: Only boto3 and optional rich formatting
- **Production Ready**: Works out of the box

## 🚀 Quick Start

### Installation

```bash
# Install minimal dependencies
pip install -r paws_streamlined_requirements.txt

# Make executable
chmod +x paws_streamlined.py
```

### Basic Usage

```bash
# Check which tools are available
python paws_streamlined.py --check-tools

# Run basic security audit (IAM, S3, EC2)
python paws_streamlined.py --audit

# Run PACU
python paws_streamlined.py --pacu

# Run Scout Suite
python paws_streamlined.py --scout

# Run aws-public-ips
python paws_streamlined.py --public-ips

# Run all available tools
python paws_streamlined.py --all
```

## 📋 Commands

### Check Tool Availability

```bash
python paws_streamlined.py --check-tools
```

Shows which external tools are installed and available.

### Basic Security Audit

```bash
python paws_streamlined.py --audit --output audit.json
```

Runs basic security checks on:
- **IAM**: Users without MFA, old access keys, password policy
- **S3**: Public access block configuration
- **EC2**: Security groups with open sensitive ports

### Run PACU

```bash
# Run with default safe modules
python paws_streamlined.py --pacu

# Run with specific modules
python paws_streamlined.py --pacu --pacu-modules "iam__enum_users,s3__enum_buckets"
```

### Run Scout Suite

```bash
python paws_streamlined.py --scout
```

Generates comprehensive AWS security audit report.

### Run aws-public-ips

```bash
python paws_streamlined.py --public-ips --output public-ips.json
```

Finds all public IP addresses in your AWS account.

## 🛠️ Installing External Tools

### PACU (AWS Penetration Testing)

```bash
git clone https://github.com/RhinoSecurityLabs/pacu.git tools/pacu
cd tools/pacu
pip install -r requirements.txt
# Follow PACU setup instructions for database initialization
```

### Scout Suite (Multi-Cloud Audit)

```bash
pip install scout-suite
```

### aws-public-ips

```bash
pip install aws-public-ips
```

### CloudMapper (Optional)

```bash
git clone https://github.com/duo-labs/cloudmapper.git tools/cloudmapper
cd tools/cloudmapper
pip install -r requirements.txt
```

## 📊 Output

### Audit Results

The basic audit generates JSON output with:
- Security scores per service
- Detailed findings
- Timestamps and metadata

Example:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "region": "us-west-2",
  "checks": {
    "iam": {
      "security_score": 85,
      "findings": [...]
    },
    "s3": {
      "buckets_checked": 5,
      "findings": [...]
    },
    "ec2": {
      "security_groups_checked": 12,
      "findings": [...]
    }
  },
  "overall_score": 85
}
```

## ⚙️ Configuration

### AWS Credentials

Configure AWS credentials using standard methods:

```bash
# Using AWS CLI
aws configure

# Using environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2

# Using profile
python paws_streamlined.py --profile production --region us-east-1
```

### Required Permissions

Minimum IAM permissions needed:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:ListUsers",
        "iam:ListMFADevices",
        "iam:ListAccessKeys",
        "iam:GetAccountPasswordPolicy",
        "s3:ListAllMyBuckets",
        "s3:GetPublicAccessBlock",
        "ec2:DescribeSecurityGroups",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🔧 Troubleshooting

### Tool Not Found

If a tool is not found:
1. Check if it's installed: `which pacu` or `which scout`
2. Install the tool (see installation section)
3. For local tools, ensure they're in `tools/` directory
4. Check PATH environment variable

### AWS Connection Issues

```bash
# Test AWS connectivity
aws sts get-caller-identity

# Check credentials
aws configure list
```

### PACU Issues

PACU requires additional setup:
1. Database initialization (see PACU README)
2. Python dependencies: `pip install -r tools/pacu/requirements.txt`
3. System jq library: `brew install jq` (macOS) or `apt-get install jq` (Linux)

## 📝 Examples

### Daily Security Check

```bash
# Run basic audit and save results
python paws_streamlined.py --audit --output daily_audit_$(date +%Y%m%d).json
```

### Comprehensive Security Scan

```bash
# Run all tools
python paws_streamlined.py --all --output comprehensive_scan.json
```

### CI/CD Integration

```bash
#!/bin/bash
# Run in CI/CD pipeline
python paws_streamlined.py --audit --output audit.json
SCORE=$(jq '.overall_score' audit.json)
if [ "$SCORE" -lt 80 ]; then
  echo "Security score $SCORE is below threshold"
  exit 1
fi
```

## 🎯 Differences from Full PAWS

PAWS Streamlined is simplified:
- ✅ No internal dependencies
- ✅ No complex menu system
- ✅ Only external open-source tools
- ✅ Simple command-line interface
- ✅ Minimal dependencies
- ✅ Production ready

## 📄 License

Same as main project.

## 🤝 Contributing

This streamlined version focuses on stability and external tool integration. Contributions welcome!

---

**PAWS Streamlined** - Simple, focused, production-ready AWS security.

