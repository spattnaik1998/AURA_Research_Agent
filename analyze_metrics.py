#!/usr/bin/env python3
"""
Metrics Analysis Script for AURA Research Agent

Parses structured log entries to calculate:
- Overall success rate
- Success rate by query type
- Average quality scores
- Most common failure reasons
- Regeneration statistics

Usage:
    python analyze_metrics.py --days 7        # Last 7 days
    python analyze_metrics.py --days 1        # Last 24 hours
    python analyze_metrics.py --file logs/aura.log  # Specific file
"""

import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Tuple

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def find_log_files(days: int) -> List[Path]:
    """Find recent log files matching the last N days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    log_dir = Path("logs")

    if not log_dir.exists():
        print(f"{Colors.RED}Error: logs directory not found{Colors.ENDC}")
        return []

    # Find log files - typically named aura.log or aura.YYYY-MM-DD.log
    log_files = []
    for log_file in log_dir.glob("*aura*.log*"):
        try:
            # Try to extract date from filename
            if log_file.stat().st_mtime > cutoff_date.timestamp():
                log_files.append(log_file)
        except:
            pass

    # If no files by modification time, just return aura.log
    if not log_files:
        default_log = log_dir / "aura.log"
        if default_log.exists():
            log_files.append(default_log)

    return sorted(log_files, reverse=True)

def parse_metrics_logs(log_file: Path) -> Tuple[List[Dict], List[Dict]]:
    """Parse success and failure entries from metrics log"""
    successes = []
    failures = []

    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                # Parse SUCCESS entries
                if "aura.metrics" in line and "SUCCESS |" in line:
                    match = re.search(
                        r"SUCCESS \| session=(\S+) \| query=(.+?) \| "
                        r"quality=(\S+) \| citations=(\S+) \| facts=(\S+) \| "
                        r"regen_attempts=(\d+) \| word_count=(\d+)",
                        line
                    )
                    if match:
                        successes.append({
                            'session_id': match.group(1),
                            'query': match.group(2),
                            'quality_score': float(match.group(3)) if match.group(3) != 'N/A' else None,
                            'citation_accuracy': float(match.group(4)) if match.group(4) != 'N/A' else None,
                            'fact_check_score': float(match.group(5)) if match.group(5) != 'N/A' else None,
                            'regeneration_attempts': int(match.group(6)),
                            'word_count': int(match.group(7))
                        })

                # Parse FAILURE entries
                elif "aura.metrics" in line and "FAILURE |" in line:
                    match = re.search(
                        r"FAILURE \| session=(\S+) \| query=(.+?) \| "
                        r"error_type=(\S+) \| message=(.+?)(?:\n|$)",
                        line
                    )
                    if match:
                        failures.append({
                            'session_id': match.group(1),
                            'query': match.group(2),
                            'error_type': match.group(3),
                            'error_message': match.group(4)
                        })
    except Exception as e:
        print(f"{Colors.RED}Error reading log file: {e}{Colors.ENDC}")

    return successes, failures

def calculate_stats(successes: List[Dict], failures: List[Dict]) -> Dict:
    """Calculate statistics from success/failure data"""
    total = len(successes) + len(failures)

    if total == 0:
        return {}

    success_rate = len(successes) / total * 100

    quality_scores = [s['quality_score'] for s in successes if s['quality_score']]
    citation_scores = [s['citation_accuracy'] for s in successes if s['citation_accuracy']]
    fact_scores = [s['fact_check_score'] for s in successes if s['fact_check_score']]

    return {
        'total_sessions': total,
        'successful': len(successes),
        'failed': len(failures),
        'success_rate': success_rate,
        'avg_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
        'avg_citation_accuracy': sum(citation_scores) / len(citation_scores) if citation_scores else 0,
        'avg_fact_check_score': sum(fact_scores) / len(fact_scores) if fact_scores else 0,
        'avg_regeneration_attempts': sum(s['regeneration_attempts'] for s in successes) / len(successes) if successes else 0,
        'max_regeneration_attempts': max((s['regeneration_attempts'] for s in successes), default=0),
        'total_word_count': sum(s['word_count'] for s in successes),
        'avg_essay_length': sum(s['word_count'] for s in successes) / len(successes) if successes else 0,
    }

def print_report(stats: Dict, successes: List[Dict], failures: List[Dict]):
    """Print formatted metrics report"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}AURA Research Agent - Metrics Report{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

    if not stats:
        print(f"{Colors.RED}No metrics data found{Colors.ENDC}")
        return

    # Overall statistics
    print(f"{Colors.CYAN}{Colors.BOLD}Overall Statistics{Colors.ENDC}")
    print(f"  Total Sessions: {stats['total_sessions']}")
    print(f"  Successful: {Colors.GREEN}{stats['successful']}{Colors.ENDC}")
    print(f"  Failed: {Colors.RED}{stats['failed']}{Colors.ENDC}")

    success_color = Colors.GREEN if stats['success_rate'] >= 90 else Colors.YELLOW if stats['success_rate'] >= 70 else Colors.RED
    print(f"  Success Rate: {success_color}{stats['success_rate']:.1f}%{Colors.ENDC}")

    print(f"\n{Colors.CYAN}{Colors.BOLD}Quality Metrics{Colors.ENDC}")
    print(f"  Avg Quality Score: {stats['avg_quality_score']:.2f}/10.0")
    print(f"  Avg Citation Accuracy: {stats['avg_citation_accuracy']*100:.1f}%")
    print(f"  Avg Fact-Check Score: {stats['avg_fact_check_score']*100:.1f}%")

    print(f"\n{Colors.CYAN}{Colors.BOLD}Essay Statistics{Colors.ENDC}")
    print(f"  Total Words Generated: {stats['total_word_count']:,}")
    print(f"  Avg Essay Length: {stats['avg_essay_length']:.0f} words")
    print(f"  Avg Regeneration Attempts: {stats['avg_regeneration_attempts']:.1f}")
    print(f"  Max Regeneration Attempts: {stats['max_regeneration_attempts']}")

    # Most common failures
    if failures:
        print(f"\n{Colors.CYAN}{Colors.BOLD}Most Common Failures{Colors.ENDC}")
        error_types = Counter(f['error_type'] for f in failures)
        for error_type, count in error_types.most_common(5):
            pct = count / len(failures) * 100
            print(f"  {Colors.RED}{error_type}{Colors.ENDC}: {count} ({pct:.1f}%)")

    # Regeneration statistics
    regen_stats = Counter(s['regeneration_attempts'] for s in successes)
    if regen_stats:
        print(f"\n{Colors.CYAN}{Colors.BOLD}Regeneration Distribution{Colors.ENDC}")
        for attempts in sorted(regen_stats.keys()):
            count = regen_stats[attempts]
            pct = count / len(successes) * 100
            attempts_str = f"{attempts} attempt{'s' if attempts != 1 else ''}"
            print(f"  {attempts_str}: {count} ({pct:.1f}%)")

    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze AURA Research Agent metrics from logs"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Analyze logs from last N days (default: 7)'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Specific log file to analyze'
    )

    args = parser.parse_args()

    # Find log files
    if args.file:
        log_files = [Path(args.file)]
        if not log_files[0].exists():
            print(f"{Colors.RED}Error: Log file not found: {args.file}{Colors.ENDC}")
            sys.exit(1)
    else:
        log_files = find_log_files(args.days)

    if not log_files:
        print(f"{Colors.RED}Error: No log files found{Colors.ENDC}")
        sys.exit(1)

    print(f"Analyzing logs from last {args.days} day(s)...")
    print(f"Found {len(log_files)} log file(s): {', '.join(f.name for f in log_files)}\n")

    # Parse all logs
    all_successes = []
    all_failures = []

    for log_file in log_files:
        print(f"Reading {log_file.name}...")
        successes, failures = parse_metrics_logs(log_file)
        all_successes.extend(successes)
        all_failures.extend(failures)

    # Calculate and print stats
    stats = calculate_stats(all_successes, all_failures)
    print_report(stats, all_successes, all_failures)

    # Success rate assessment
    if stats['success_rate'] >= 90:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Target success rate achieved (≥90%)!{Colors.ENDC}\n")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ Success rate below target. Tuning thresholds recommended.{Colors.ENDC}\n")

if __name__ == '__main__':
    main()
