#!/usr/bin/env python3
"""
PAWS Streamlined - Professional AWS Security
Simplified CLI tool using only external open-source security tools
"""

import os
import sys
import json
import argparse
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

try:
    from rich.console import Console
    from rich.table import Table as RichTable
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to basic print
    class Console:
        def print(self, *args, **kwargs):
            print(*args)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

console = Console() if RICH_AVAILABLE else Console()


def _finding_by_title(service_data: Dict[str, Any], title: str) -> Optional[Dict[str, Any]]:
    for finding in service_data.get('findings', []):
        if finding.get('title') == title:
            return finding
    return None


def eval_mfa(service_data: Dict[str, Any]) -> Tuple[bool, str]:
    if service_data.get('error'):
        return False, f"Unable to evaluate: {service_data.get('error')}"
    finding = _finding_by_title(service_data, 'Users without MFA')
    if finding and finding.get('count', 0) > 0:
        return False, f"{finding.get('count', 0)} user(s) without MFA."
    return True, "All IAM users have MFA enforced."


def eval_old_keys(service_data: Dict[str, Any]) -> Tuple[bool, str]:
    if service_data.get('error'):
        return False, f"Unable to evaluate: {service_data.get('error')}"
    finding = _finding_by_title(service_data, 'Old access keys (>90 days)')
    if finding and finding.get('count', 0) > 0:
        return False, f"{finding.get('count', 0)} access key(s) older than 90 days."
    return True, "No IAM access keys older than 90 days."


def eval_password_policy(service_data: Dict[str, Any]) -> Tuple[bool, str]:
    if service_data.get('error'):
        return False, f"Unable to evaluate: {service_data.get('error')}"
    finding = _finding_by_title(service_data, 'Password policy')
    if finding and finding.get('status') == 'not configured':
        return False, "Account password policy is not configured."
    return True, "Password policy is configured."


STANDARD_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    'cis': {
        'name': 'CIS AWS Foundations Benchmark',
        'version': '1.5',
        'controls': [
            {
                'id': '1.1',
                'title': 'Ensure MFA is enabled for console access',
                'service': 'iam',
                'evaluator': eval_mfa,
                'description': 'IAM users with console access should have MFA enabled.'
            },
            {
                'id': '1.4',
                'title': 'Ensure access keys are rotated every 90 days or less',
                'service': 'iam',
                'evaluator': eval_old_keys,
                'description': 'Inactive or old IAM access keys should be rotated.'
            },
            {
                'id': '1.5',
                'title': 'Ensure IAM password policy requires strong passwords',
                'service': 'iam',
                'evaluator': eval_password_policy,
                'description': 'Account password policy must be configured for strong passwords.'
            },
        ]
    },
    'nist': {
        'name': 'NIST Cybersecurity Framework',
        'version': '1.1',
        'controls': [
            {
                'id': 'PR.AC-1',
                'title': 'Identities and credentials are managed',
                'service': 'iam',
                'evaluator': eval_mfa,
                'description': 'Access control requires multi-factor authentication.'
            },
            {
                'id': 'PR.AC-5',
                'title': 'Network integrity is protected',
                'service': 'iam',
                'evaluator': eval_old_keys,
                'description': 'Credential rotation helps maintain access integrity.'
            },
            {
                'id': 'PR.IP-2',
                'title': 'Configuration change control processes are in place',
                'service': 'iam',
                'evaluator': eval_password_policy,
                'description': 'Password policies align with organizational standards.'
            },
        ]
    },
    'pcidss': {
        'name': 'PCI DSS',
        'version': '3.2.1',
        'controls': [
            {
                'id': '8.3',
                'title': 'Secure all individual non-console administrative access with MFA',
                'service': 'iam',
                'evaluator': eval_mfa,
                'description': 'Administrative access must enforce MFA.'
            },
            {
                'id': '8.2',
                'title': 'Employ at least one of the following methods to authenticate all users',
                'service': 'iam',
                'evaluator': eval_password_policy,
                'description': 'Strong password policy must be enforced.'
            },
            {
                'id': '8.1.4',
                'title': 'Remove/disable inactive user accounts within 90 days',
                'service': 'iam',
                'evaluator': eval_old_keys,
                'description': 'Access keys older than 90 days should be rotated/removed.'
            },
        ]
    },
}


class PAWSStreamlined:
    """Streamlined PAWS CLI using only external open-source tools"""
    
    def __init__(self, profile: str = None, region: str = None):
        self.profile = profile
        self.region = region or 'us-west-2'
        self.session = None
        self.aws_connected = False
        
        # Initialize AWS session
        try:
            self.session = boto3.Session(profile_name=profile, region_name=self.region)
            self._initialize_aws_clients()
            self.aws_connected = True
        except Exception as e:
            console.print(f"[red]Warning: AWS connection failed - {e}[/red]")
            console.print("[yellow]Some features may not work without AWS credentials[/yellow]")
            self.aws_connected = False
    
    def _initialize_aws_clients(self):
        """Initialize AWS service clients"""
        self.iam = self.session.client('iam')
        self.s3 = self.session.client('s3')
        self.ec2 = self.session.client('ec2')
        self.sts = self.session.client('sts')
    
    def _resolve_tool_path(self, tool_name: str, alternatives: List[str] = None) -> Optional[str]:
        """Resolve tool path from PATH or local tools directory"""
        alternatives = alternatives or [tool_name]
        
        # Check PATH first
        for alt in alternatives:
            path = shutil.which(alt)
            if path:
                return path
        
        # Check local tools directory (current dir and parent dir)
        tools_dirs = [Path('tools'), Path('../tools')]
        
        for tools_dir in tools_dirs:
            for alt in alternatives:
                # Try as directory with executable inside
                tool_dir = tools_dir / alt
                if tool_dir.exists():
                    # Look for common entry points
                    candidates = [
                        tool_dir / f'{alt}.py',
                        tool_dir / 'cli.py',
                        tool_dir / alt,
                        tool_dir / 'pacu.py',  # PACU specific
                        tool_dir / 'scout.py',  # Scout Suite specific
                    ]
                    for candidate in candidates:
                        if candidate.exists():
                            return str(candidate.resolve())
                
                # Special handling for scout-suite directory name
                if alt == 'scout' or alt == 'scout-suite':
                    scout_dir = tools_dir / 'scout-suite'
                    if scout_dir.exists():
                        scout_py = scout_dir / 'scout.py'
                        if scout_py.exists():
                            return str(scout_py.resolve())
                
                # Special handling for cloudmapper directory name
                if alt == 'cloudmapper':
                    cm_dir = tools_dir / 'cloudmapper'
                    if cm_dir.exists():
                        cm_py = cm_dir / 'cloudmapper.py'
                        if cm_py.exists():
                            return str(cm_py.resolve())
        
        return None
    
    def check_tool_availability(self) -> Dict[str, bool]:
        """Check which external tools are available"""
        tools = {
            'PACU': self._resolve_tool_path('pacu', ['pacu', 'pacu.py']),
            'Scout Suite': self._resolve_tool_path('scout', ['scout', 'scout-suite']),
            'CloudMapper': self._resolve_tool_path('cloudmapper', ['cloudmapper', 'cloudmapper.py']),
            'aws-public-ips': self._resolve_tool_path('aws-public-ips', ['aws-public-ips']),
        }
        
        return {name: path is not None for name, path in tools.items()}
    
    def display_tool_status(self):
        """Display status of available tools"""
        status = self.check_tool_availability()
        
        if RICH_AVAILABLE:
            table = RichTable(title="External Tool Availability")
            table.add_column("Tool", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Installation", style="yellow")
            
            install_info = {
                'PACU': 'git clone https://github.com/RhinoSecurityLabs/pacu.git tools/pacu',
                'Scout Suite': 'git clone https://github.com/nccgroup/ScoutSuite.git tools/scout-suite',
                'CloudMapper': 'git clone https://github.com/duo-labs/cloudmapper.git tools/cloudmapper',
                'aws-public-ips': 'pip install aws-public-ips',
            }
            
            for tool, available in status.items():
                status_icon = "✅" if available else "❌"
                install_cmd = install_info.get(tool, "See tool documentation")
                table.add_row(tool, status_icon, install_cmd)
            
            console.print(table)
        else:
            print("\nExternal Tool Availability:")
            for tool, available in status.items():
                status_text = "✅ Available" if available else "❌ Not found"
                print(f"  {tool}: {status_text}")
    
    def run_pacu(self, modules: List[str] = None):
        """Run PACU with specified modules"""
        pacu_path = self._resolve_tool_path('pacu', ['pacu', 'pacu.py'])
        
        if not pacu_path:
            console.print("[red]PACU not found. Install with:[/red]")
            console.print("[yellow]  git clone https://github.com/RhinoSecurityLabs/pacu.git tools/pacu[/yellow]")
            return False
        
        # Default safe modules if none specified
        if not modules:
            modules = [
                "iam__enum_users",
                "iam__enum_roles",
                "s3__enum_buckets",
                "s3__audit",
                "ec2__enum",
            ]
        
        modules_arg = ",".join(modules)
        
        console.print(f"[bold yellow]Running PACU with modules: {modules_arg}[/bold yellow]")
        
        try:
            env = os.environ.copy()
            if self.profile:
                env['AWS_PROFILE'] = self.profile
            if self.region:
                env['AWS_DEFAULT_REGION'] = self.region
            
            # Build command
            if pacu_path.endswith('.py'):
                cmd = [sys.executable, pacu_path, "-m", modules_arg]
            else:
                cmd = [pacu_path, "-m", modules_arg]
            
            result = subprocess.run(cmd, env=env, check=False)
            return result.returncode == 0
            
        except Exception as e:
            console.print(f"[red]PACU execution failed: {e}[/red]")
            return False
    
    def run_scout_suite(self, output_dir: str = None):
        """Run Scout Suite AWS audit"""
        scout_path = self._resolve_tool_path('scout', ['scout', 'scout-suite'])
        
        if not scout_path:
            console.print("[red]Scout Suite not found. Install with:[/red]")
            console.print("[yellow]  git clone https://github.com/nccgroup/ScoutSuite.git tools/scout-suite[/yellow]")
            console.print("[yellow]  cd tools/scout-suite && pip install -r requirements.txt[/yellow]")
            return False
        
        output_dir = output_dir or 'out/scout-suite'
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        console.print("[bold yellow]Running Scout Suite (this may take several minutes)...[/bold yellow]")
        
        try:
            env = os.environ.copy()
            if self.profile:
                env['AWS_PROFILE'] = self.profile
            if self.region:
                env['AWS_DEFAULT_REGION'] = self.region
            
            # Scout Suite uses scout.py with --provider flag
            if scout_path.endswith('.py'):
                cmd = [sys.executable, scout_path, '--provider', 'aws', '--report-dir', output_dir, '--no-browser']
            else:
                cmd = [scout_path, '--provider', 'aws', '--report-dir', output_dir, '--no-browser']
            
            result = subprocess.run(cmd, env=env, check=False)
            
            if result.returncode == 0:
                console.print(f"[green]Scout Suite completed. Report in {output_dir}[/green]")
                return True
            else:
                console.print("[yellow]Scout Suite completed with warnings. Check output above.[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]Scout Suite failed: {e}[/red]")
            return False
    
    def run_aws_public_ips(self, output_file: str = None):
        """Run aws-public-ips to find public resources"""
        tool_path = self._resolve_tool_path('aws-public-ips', ['aws-public-ips'])
        
        if not tool_path:
            console.print("[red]aws-public-ips not found. Install with:[/red]")
            console.print("[yellow]  pip install aws-public-ips[/yellow]")
            return False
        
        output_file = output_file or 'out/aws-public-ips/public-ips.json'
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        console.print("[bold yellow]Running aws-public-ips...[/bold yellow]")
        
        try:
            env = os.environ.copy()
            if self.profile:
                env['AWS_PROFILE'] = self.profile
            if self.region:
                env['AWS_DEFAULT_REGION'] = self.region
            
            with open(output_file, 'w') as f:
                result = subprocess.run(
                    [tool_path, '--format', 'json'],
                    env=env,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    check=False
                )
            
            if result.returncode == 0:
                console.print(f"[green]Results saved to {output_file}[/green]")
                return True
            else:
                console.print(f"[yellow]aws-public-ips completed with warnings. Check {output_file}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]aws-public-ips failed: {e}[/red]")
            return False
    
    def basic_iam_check(self) -> Dict[str, Any]:
        """Basic IAM security check using boto3"""
        if not self.aws_connected:
            return {'error': 'AWS not connected'}
        
        findings = []
        score = 100
        
        try:
            # Get account info
            identity = self.sts.get_caller_identity()
            account_id = identity.get('Account')
            
            # Check users without MFA
            users = self.iam.list_users().get('Users', [])
            users_without_mfa = []
            old_access_keys = []
            score_breakdown: List[Dict[str, Any]] = []
            
            for user in users:
                user_name = user.get('UserName')
                
                # Check MFA
                mfa_devices = self.iam.list_mfa_devices(UserName=user_name).get('MFADevices', [])
                if not mfa_devices:
                    users_without_mfa.append(user_name)
                
                # Check access key age
                access_keys = self.iam.list_access_keys(UserName=user_name).get('AccessKeyMetadata', [])
                for key in access_keys:
                    create_date = key.get('CreateDate')
                    if isinstance(create_date, datetime):
                        age_days = (datetime.utcnow().replace(tzinfo=None) - 
                                   create_date.replace(tzinfo=None)).days
                        if age_days > 90:
                            old_access_keys.append({
                                'user': user_name,
                                'access_key_id': key.get('AccessKeyId'),
                                'age_days': age_days
                            })
            
            # Calculate score
            if users_without_mfa:
                deduction = min(10, len(users_without_mfa) * 2)
                findings.append({
                    'category': 'IAM',
                    'severity': 'medium',
                    'title': 'Users without MFA',
                    'count': len(users_without_mfa),
                    'users': users_without_mfa[:10]  # Limit to first 10
                })
                score -= deduction
                score_breakdown.append({
                    'control': 'MFA coverage',
                    'deduction': deduction,
                    'details': f"{len(users_without_mfa)} user(s) without MFA"
                })
            
            if old_access_keys:
                deduction = min(10, len(old_access_keys))
                findings.append({
                    'category': 'IAM',
                    'severity': 'medium',
                    'title': 'Old access keys (>90 days)',
                    'count': len(old_access_keys)
                })
                score -= deduction
                score_breakdown.append({
                    'control': 'Old access keys',
                    'deduction': deduction,
                    'details': f"{len(old_access_keys)} access key(s) older than 90 days"
                })
            
            # Check password policy
            try:
                policy = self.iam.get_account_password_policy()
                findings.append({
                    'category': 'IAM',
                    'severity': 'info',
                    'title': 'Password policy',
                    'status': 'configured'
                })
            except ClientError:
                findings.append({
                    'category': 'IAM',
                    'severity': 'low',
                    'title': 'Password policy',
                    'status': 'not configured'
                })
                password_deduction = 5
                score -= password_deduction
                score_breakdown.append({
                    'control': 'Password policy',
                    'deduction': password_deduction,
                    'details': 'No account password policy configured'
                })
            
            score = max(0, min(100, score))
            
            return {
                'account_id': account_id,
                'security_score': score,
                'findings': findings,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'score_breakdown': score_breakdown,
                'baseline_score': 100
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'security_score': 0,
                'findings': [],
                'score_breakdown': [],
                'baseline_score': 100
            }
    
    def basic_s3_check(self) -> Dict[str, Any]:
        """Basic S3 security check"""
        if not self.aws_connected:
            return {'error': 'AWS not connected'}
        
        findings = []
        
        try:
            buckets = self.s3.list_buckets().get('Buckets', [])
            
            for bucket in buckets:
                bucket_name = bucket.get('Name')
                try:
                    # Check public access block
                    pab = self.s3.get_public_access_block(Bucket=bucket_name)
                    config = pab.get('PublicAccessBlockConfiguration', {})
                    
                    if not all(config.get(k, False) for k in 
                              ['BlockPublicAcls', 'IgnorePublicAcls', 
                               'BlockPublicPolicy', 'RestrictPublicBuckets']):
                        findings.append({
                            'bucket': bucket_name,
                            'issue': 'Public access block not fully enabled',
                            'severity': 'medium'
                        })
                except ClientError:
                    findings.append({
                        'bucket': bucket_name,
                        'issue': 'No public access block configuration',
                        'severity': 'high'
                    })
            
            return {
                'buckets_checked': len(buckets),
                'findings': findings,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            return {'error': str(e), 'findings': []}
    
    def basic_ec2_check(self) -> Dict[str, Any]:
        """Basic EC2 security check"""
        if not self.aws_connected:
            return {'error': 'AWS not connected'}
        
        findings = []
        
        try:
            # Check security groups with open ports
            response = self.ec2.describe_security_groups()
            sensitive_ports = {22, 3389, 3306, 5432}  # SSH, RDP, MySQL, PostgreSQL
            
            for sg in response.get('SecurityGroups', []):
                group_id = sg.get('GroupId')
                
                for perm in sg.get('IpPermissions', []):
                    from_port = perm.get('FromPort')
                    to_port = perm.get('ToPort')
                    protocol = perm.get('IpProtocol')
                    
                    # Check if any sensitive ports are open to 0.0.0.0/0
                    if from_port and from_port in sensitive_ports:
                        for ip_range in perm.get('IpRanges', []):
                            if ip_range.get('CidrIp') == '0.0.0.0/0':
                                findings.append({
                                    'security_group': group_id,
                                    'port': from_port,
                                    'protocol': protocol,
                                    'issue': f'Port {from_port} open to 0.0.0.0/0',
                                    'severity': 'high'
                                })
            
            return {
                'security_groups_checked': len(response.get('SecurityGroups', [])),
                'findings': findings,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            return {'error': str(e), 'findings': []}
    
    def run_basic_audit(self, output_file: str = None, pdf_output: str = None,
                        standards: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run basic security audit using boto3"""
        console.print("[bold blue]Running Basic Security Audit...[/bold blue]")
        
        iam_results: Dict[str, Any] = {}
        s3_results: Dict[str, Any] = {}
        ec2_results: Dict[str, Any] = {}

        results: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'region': self.region,
            'profile': self.profile,
            'checks': {},
            'baseline_score': 100,
            'score_breakdown': []
        }
        
        # IAM check
        console.print("[cyan]Checking IAM...[/cyan]")
        iam_results = self.basic_iam_check()
        results['checks']['iam'] = iam_results
        
        # S3 check
        console.print("[cyan]Checking S3...[/cyan]")
        s3_results = self.basic_s3_check()
        results['checks']['s3'] = s3_results
        
        # EC2 check
        console.print("[cyan]Checking EC2...[/cyan]")
        ec2_results = self.basic_ec2_check()
        results['checks']['ec2'] = ec2_results
        
        # Calculate overall score
        scores = []
        if 'security_score' in iam_results:
            scores.append(iam_results['security_score'])
        
        if scores:
            results['overall_score'] = sum(scores) // len(scores)
        else:
            results['overall_score'] = 0
        
        results['baseline_score'] = iam_results.get('baseline_score', 100)
        results['score_breakdown'] = iam_results.get('score_breakdown', [])

        selected_standards = standards or []
        if not selected_standards:
            selected_standards = list(STANDARD_DEFINITIONS.keys())
        results['standards'] = self._evaluate_standards(results, selected_standards)
        results['selected_standards'] = selected_standards
        
        # Save to file if requested
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            console.print(f"[green]Results saved to {output_file}[/green]")

        if pdf_output:
            self._generate_pdf_report(results, pdf_output)
        
        return results

    def _generate_pdf_report(self, results: Dict[str, Any], pdf_path: str) -> None:
        """Generate a PDF report from results"""
        if not REPORTLAB_AVAILABLE:
            console.print("[yellow]ReportLab not installed; skipping PDF generation.[/yellow]")
            return
        try:
            pdf_file = Path(pdf_path)
            pdf_file.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(str(pdf_file), pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("PAWS Streamlined Security Report", styles['Title']))
            elements.append(Spacer(1, 12))
            meta_info = [
                f"Timestamp: {results.get('timestamp', 'N/A')}",
                f"Region: {results.get('region', 'N/A')}",
                f"Profile: {results.get('profile') or 'default'}",
                f"Overall Security Score: {results.get('overall_score', 0)}/100",
            ]
            elements.append(Paragraph("<br/>".join(meta_info), styles['Normal']))
            elements.append(Spacer(1, 12))

            # Scoring methodology
            scoring_lines = [
                "Scoring Methodology (100-point scale):",
                "• Start at 100 points (IAM baseline).",
                "• Missing MFA: -2 points per user (maximum -10).",
                "• Old access keys (>90 days): -1 point per key (maximum -10).",
                "• Missing password policy: -5 points.",
                "• S3/EC2 findings are informational until weighted scoring is enabled."
            ]
            elements.append(Paragraph("Scoring Methodology", styles['Heading2']))
            for line in scoring_lines:
                elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 12))

            # Score explanation
            checks = results.get('checks', {})
            breakdown = results.get('score_breakdown', [])
            baseline = results.get('baseline_score', 100)
            score_lines = [
                f"Baseline score: {baseline} points.",
                "Deductions were applied based on IAM controls (MFA usage, access key hygiene, password policy).",
                "S3 and EC2 findings are currently informational until numeric scoring is added."
            ]
            if breakdown:
                score_lines.append("Detailed deductions:")
                for entry in breakdown:
                    control = entry.get('control', 'Control')
                    deduction = entry.get('deduction', 0)
                    details = entry.get('details', '')
                    score_lines.append(f"- {control}: -{deduction} pts ({details})")
            else:
                score_lines.append("No deductions applied; perfect score.")
            score_lines.append(f"Final score: {results.get('overall_score', 0)}/100.")
            elements.append(Paragraph("Score Explanation", styles['Heading2']))
            elements.append(Paragraph("<br/>".join(score_lines), styles['Normal']))
            elements.append(Spacer(1, 12))

            # Key findings
            key_points: List[str] = []
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
            for service, data in checks.items():
                for finding in data.get('findings', []):
                    severity = finding.get('severity', 'info')
                    title = finding.get('title', 'Finding')
                    detail_parts = []
                    if finding.get('count') is not None:
                        detail_parts.append(f"Count: {finding['count']}")
                    if finding.get('users'):
                        detail_parts.append(f"Users: {', '.join(finding['users'])}")
                    if finding.get('status'):
                        detail_parts.append(f"Status: {finding['status']}")
                    if finding.get('bucket'):
                        detail_parts.append(f"Bucket: {finding['bucket']}")
                    if finding.get('security_group'):
                        detail_parts.append(f"Security Group: {finding['security_group']}")
                    if finding.get('port'):
                        detail_parts.append(f"Port: {finding['port']}")
                    if finding.get('issue'):
                        detail_parts.append(f"Issue: {finding['issue']}")
                    detail_text = "; ".join(detail_parts) or "See summary table for more details"
                    key_points.append({
                        'severity_order': severity_order.get(severity.lower(), 5),
                        'text': f"{service.upper()} • {title} ({severity}) — {detail_text}"
                    })

            key_points.sort(key=lambda x: x['severity_order'])
            elements.append(Paragraph("Key Findings", styles['Heading2']))
            if key_points:
                for point in key_points[:10]:
                    elements.append(Paragraph(f"• {point['text']}", styles['Normal']))
            else:
                elements.append(Paragraph("No findings detected across IAM, S3, or EC2 checks.", styles['Normal']))
            elements.append(Spacer(1, 12))

            table_data = [["Service", "Item", "Severity", "Details"]]
            checks = results.get('checks', {})
            for service, data in checks.items():
                service_label = service.upper()
                findings = data.get('findings', [])

                # Summary row
                summary_bits = []
                if 'security_score' in data:
                    summary_bits.append(f"Score: {data['security_score']}/100")
                if 'buckets_checked' in data:
                    summary_bits.append(f"Buckets checked: {data['buckets_checked']}")
                if 'security_groups_checked' in data:
                    summary_bits.append(f"Security groups checked: {data['security_groups_checked']}")
                if summary_bits:
                    table_data.append([service_label, "Summary", "info", "; ".join(summary_bits)])
                    service_label = ""

                # Error row
                if data.get('error'):
                    table_data.append([service_label or service.upper(), "Error", "critical", data['error']])
                    service_label = ""

                # Finding rows
                if findings:
                    for finding in findings:
                        detail_parts = []
                        if finding.get('count') is not None:
                            detail_parts.append(f"Count: {finding['count']}")
                        if finding.get('users'):
                            detail_parts.append(f"Users: {', '.join(finding['users'])}")
                        if finding.get('status'):
                            detail_parts.append(f"Status: {finding['status']}")
                        if finding.get('bucket'):
                            detail_parts.append(f"Bucket: {finding['bucket']}")
                        if finding.get('security_group'):
                            detail_parts.append(f"Security Group: {finding['security_group']}")
                        if finding.get('port'):
                            detail_parts.append(f"Port: {finding['port']}")
                        if finding.get('issue'):
                            detail_parts.append(f"Issue: {finding['issue']}")
                        detail_text = "; ".join(detail_parts) or finding.get('title', 'See details')
                        table_data.append([
                            service_label or service.upper(),
                            finding.get('title', 'Finding'),
                            finding.get('severity', 'info'),
                            detail_text
                        ])
                        service_label = ""

                if not findings and not data.get('error'):
                    table_data.append([service_label or service.upper(), "No issues", "info", "All checks passed."])

            table = Table(table_data, hAlign='LEFT', colWidths=[90, 140, 80, 250])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)

            standards_data = results.get('standards', {})
            if standards_data:
                elements.append(Paragraph("Compliance Profiles", styles['Heading2']))
                for key, data in standards_data.items():
                    total_controls = len(data.get('controls', []))
                    passed_controls = len([c for c in data.get('controls', []) if c.get('status') == 'pass'])
                    heading = f"{data['name']} v{data.get('version', '')}"
                    elements.append(Paragraph(heading, styles['Heading3']))
                    summary = (
                        f"{'PASS' if data['status'] == 'pass' else 'FAIL'} — "
                        f"{passed_controls}/{total_controls} controls passed."
                    )
                    elements.append(Paragraph(summary, styles['Normal']))
                    elements.append(Spacer(1, 6))
                    standard_table_data = [["Control", "Requirement", "Result", "Notes"]]
                    row_styles = [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                    for idx, ctrl in enumerate(data.get('controls', []), start=1):
                        status_text = "PASS" if ctrl.get('status') == 'pass' else "FAIL"
                        notes = ctrl.get('notes', '')
                        standard_table_data.append([
                            ctrl.get('id'),
                            ctrl.get('title'),
                            status_text,
                            notes,
                        ])
                        row_color = colors.lightgreen if ctrl.get('status') == 'pass' else colors.salmon
                        row_styles.append(('BACKGROUND', (0, idx), (-1, idx), row_color))
                    standard_table = Table(standard_table_data, hAlign='LEFT', colWidths=[60, 230, 50, 220])
                    standard_table.setStyle(TableStyle(row_styles))
                    elements.append(standard_table)
                    elements.append(Spacer(1, 12))

            doc.build(elements)
            console.print(f"[green]PDF report saved to {pdf_file}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to generate PDF report: {e}[/red]")
    
    def _evaluate_standards(self, results: Dict[str, Any], selected: List[str]) -> Dict[str, Any]:
        evaluations: Dict[str, Any] = {}
        checks = results.get('checks', {})
        for key in selected:
            definition = STANDARD_DEFINITIONS.get(key)
            if not definition:
                continue
            controls_output = []
            for ctrl in definition.get('controls', []):
                service_data = checks.get(ctrl.get('service', ''), {})
                passed, notes = ctrl['evaluator'](service_data)
                controls_output.append({
                    'id': ctrl.get('id'),
                    'title': ctrl.get('title'),
                    'description': ctrl.get('description'),
                    'status': 'pass' if passed else 'fail',
                    'notes': notes,
                })
            overall_status = 'pass' if all(c['status'] == 'pass' for c in controls_output) else 'fail'
            evaluations[key] = {
                'name': definition.get('name'),
                'version': definition.get('version'),
                'status': overall_status,
                'controls': controls_output,
            }
        return evaluations

    def display_audit_results(self, results: Dict[str, Any]):
        """Display audit results in a formatted table"""
        if RICH_AVAILABLE:
            table = RichTable(title="Security Audit Results")
            table.add_column("Service", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Findings", style="yellow")
            
            for service, check_results in results.get('checks', {}).items():
                if 'error' in check_results:
                    table.add_row(service.upper(), "❌", f"Error: {check_results['error']}")
                else:
                    findings_count = len(check_results.get('findings', []))
                    status = "✅" if findings_count == 0 else "⚠️"
                    table.add_row(service.upper(), status, str(findings_count))
            
            console.print(table)
            console.print(f"\n[bold]Overall Security Score: {results.get('overall_score', 0)}/100[/bold]")
        else:
            print("\nSecurity Audit Results:")
            for service, check_results in results.get('checks', {}).items():
                if 'error' in check_results:
                    print(f"  {service.upper()}: Error - {check_results['error']}")
                else:
                    findings_count = len(check_results.get('findings', []))
                    print(f"  {service.upper()}: {findings_count} findings")
            print(f"\nOverall Security Score: {results.get('overall_score', 0)}/100")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='PAWS Streamlined - AWS Security using external open-source tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check tool availability
  %(prog)s --check-tools
  
  # Run basic security audit
  %(prog)s --audit
  
  # Run PACU
  %(prog)s --pacu
  
  # Run Scout Suite
  %(prog)s --scout
  
  # Run aws-public-ips
  %(prog)s --public-ips
  
  # Run all tools
  %(prog)s --all
        """
    )
    
    parser.add_argument('--profile', '-p', help='AWS profile to use')
    parser.add_argument('--region', '-r', default='us-west-2', help='AWS region')
    parser.add_argument('--check-tools', action='store_true', help='Check available tools')
    parser.add_argument('--audit', action='store_true', help='Run basic security audit')
    parser.add_argument('--pacu', action='store_true', help='Run PACU')
    parser.add_argument('--scout', action='store_true', help='Run Scout Suite')
    parser.add_argument('--public-ips', action='store_true', help='Run aws-public-ips')
    parser.add_argument('--all', action='store_true', help='Run all available tools')
    parser.add_argument('--output', '-o', help='Output file for audit results (JSON)')
    parser.add_argument('--pdf-output', help='Output PDF file for audit results', default='audit_report.pdf')
    parser.add_argument(
        '--standards',
        nargs='+',
        choices=list(STANDARD_DEFINITIONS.keys()),
        help='Security standards to evaluate (default: all supported profiles)'
    )
    parser.add_argument('--pacu-modules', help='PACU modules to run (comma-separated)')
    
    args = parser.parse_args()
    
    # Display banner
    if RICH_AVAILABLE:
        banner = """
    ██████╗  █████╗ ██╗    ██╗███████╗
    ██╔══██╗██╔══██╗██║    ██║██╔════╝
    ██████╔╝███████║██║ █╗ ██║███████╗
    ██╔═══╝ ██╔══██║██║███╗██║╚════██║
    ██║     ██║  ██║╚███╔███╔╝███████║
    ╚═╝     ╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝
    
    Professional AWS Security - Streamlined
    Using External Open-Source Tools Only
        """
        console.print(Panel.fit(banner, title="[bold blue]PAWS Streamlined[/bold blue]", border_style="blue"))
    
    paws = PAWSStreamlined(profile=args.profile, region=args.region)
    
    # Check tools
    if args.check_tools:
        paws.display_tool_status()
        return
    
    # Run operations
    if args.audit or args.all:
        results = paws.run_basic_audit(
            output_file=args.output,
            pdf_output=args.pdf_output,
            standards=args.standards
        )
        paws.display_audit_results(results)
    
    if args.pacu or args.all:
        modules = None
        if args.pacu_modules:
            modules = [m.strip() for m in args.pacu_modules.split(',')]
        paws.run_pacu(modules=modules)
    
    if args.scout or args.all:
        output_dir = args.output or 'out/scout-suite'
        paws.run_scout_suite(output_dir=output_dir)
    
    if args.public_ips or args.all:
        output_file = args.output or 'out/aws-public-ips/public-ips.json'
        paws.run_aws_public_ips(output_file=output_file)
    
    # If no arguments, show help
    if not any([args.check_tools, args.audit, args.pacu, args.scout, 
                args.public_ips, args.all]):
        parser.print_help()


if __name__ == '__main__':
    main()

