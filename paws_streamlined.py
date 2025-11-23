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
from typing import Dict, List, Optional, Any
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

console = Console() if RICH_AVAILABLE else Console()


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
                findings.append({
                    'category': 'IAM',
                    'severity': 'medium',
                    'title': 'Users without MFA',
                    'count': len(users_without_mfa),
                    'users': users_without_mfa[:10]  # Limit to first 10
                })
                score -= min(10, len(users_without_mfa) * 2)
            
            if old_access_keys:
                findings.append({
                    'category': 'IAM',
                    'severity': 'medium',
                    'title': 'Old access keys (>90 days)',
                    'count': len(old_access_keys)
                })
                score -= min(10, len(old_access_keys))
            
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
                score -= 5
            
            score = max(0, min(100, score))
            
            return {
                'account_id': account_id,
                'security_score': score,
                'findings': findings,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'security_score': 0,
                'findings': []
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
    
    def run_basic_audit(self, output_file: str = None) -> Dict[str, Any]:
        """Run basic security audit using boto3"""
        console.print("[bold blue]Running Basic Security Audit...[/bold blue]")
        
        results = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'region': self.region,
            'profile': self.profile,
            'checks': {}
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
        
        # Save to file if requested
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            console.print(f"[green]Results saved to {output_file}[/green]")
        
        return results
    
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
        results = paws.run_basic_audit(output_file=args.output)
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

