#!/usr/bin/env python3
"""
Metrics Analysis Script for AURA Research Agent
"""
import os
import sys
import re
import json
import argparse
import logging
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class MetricsAnalyzer:
    def __init__(self, log_file: str = "logs/aura.metrics.log"):
        self.log_file = log_file
        self.success_logs: List[Dict[str, Any]] = []
        self.failure_logs: List[Dict[str, Any]] = []

    def parse_log_file(self, days: int = 7) -> None:
        if not os.path.exists(self.log_file):
            logger.error(f"Log file not found: {self.log_file}")
            return

        logger.info(f"Parsing metrics from last {days} day(s)...")
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'SUCCESS' in line:
                    data = self._parse_success_line(line)
                    if data:
                        self.success_logs.append(data)
                elif 'FAILURE' in line:
                    data = self._parse_failure_line(line)
                    if data:
                        self.failure_logs.append(data)

        logger.info(f"Parsed {len(self.success_logs)} SUCCESS and {len(self.failure_logs)} FAILURE entries")

    def _parse_success_line(self, line: str) -> Dict[str, Any]:
        data = {"status": "success", "session_id": None, "quality_score": None}
        m = re.search(r'session=([^\s|]+)', line)
        if m:
            data["session_id"] = m.group(1)
        m = re.search(r'quality=([^\s|]+)', line)
        if m:
            try:
                data["quality_score"] = float(m.group(1))
            except:
                pass
        return data

    def _parse_failure_line(self, line: str) -> Dict[str, Any]:
        data = {"status": "failure", "session_id": None, "error_type": None}
        m = re.search(r'session=([^\s|]+)', line)
        if m:
            data["session_id"] = m.group(1)
        m = re.search(r'error_type=([^\s|]+)', line)
        if m:
            data["error_type"] = m.group(1)
        return data

    def calculate_metrics(self) -> Dict[str, Any]:
        total = len(self.success_logs) + len(self.failure_logs)
        if total == 0:
            return {}
        success_count = len(self.success_logs)
        success_rate = (success_count / total) * 100
        quality_scores = [x["quality_score"] for x in self.success_logs if x["quality_score"]]
        return {
            "total_queries": total,
            "success_count": success_count,
            "failure_count": total - success_count,
            "success_rate_percent": round(success_rate, 2),
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
        }

    def print_report(self, metrics: Dict[str, Any]) -> None:
        print("\n" + "=" * 70)
        print("AURA RESEARCH AGENT - METRICS ANALYSIS REPORT")
        print("=" * 70)
        print(f"\nOVERALL STATISTICS")
        print(f"  Total Queries:     {metrics['total_queries']}")
        print(f"  Successful:        {metrics['success_count']} ({metrics['success_rate_percent']:.1f}%)")
        print(f"  Failed:            {metrics['failure_count']} ({100 - metrics['success_rate_percent']:.1f}%)")
        
        if metrics['success_rate_percent'] >= 90:
            status = "EXCELLENT"
        elif metrics['success_rate_percent'] >= 80:
            status = "GOOD"
        else:
            status = "NEEDS IMPROVEMENT"
        print(f"  Assessment:        {status}")
        
        if metrics['avg_quality_score']:
            print(f"\nQUALITY METRICS")
            print(f"  Avg Quality Score: {metrics['avg_quality_score']:.2f}/10.0")
        print("\n" + "=" * 70 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Analyze AURA metrics from logs')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--log-file', type=str, default='logs/aura.metrics.log')
    args = parser.parse_args()
    
    analyzer = MetricsAnalyzer(log_file=args.log_file)
    analyzer.parse_log_file(days=args.days)
    metrics = analyzer.calculate_metrics()
    
    if not metrics:
        logger.error("No metrics available")
        sys.exit(1)
    
    analyzer.print_report(metrics)

if __name__ == '__main__':
    main()
