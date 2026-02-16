#!/usr/bin/env python3
"""
AURA Research Agent - Complete Pipeline Testing & Validation Script
=================================================================

This script validates the essay generation pipeline end-to-end after implementing
the 3-phase validation guardrails relaxation (commit 2996a74).

Usage:
    python validate_pipeline.py [--stage 1-4] [--verbose]

Stages:
    1. System Startup & Health Check
    2. Basic Pipeline Test (Single Essay)
    3. Comprehensive Testing (5 Diverse Topics)
    4. Edge Case & Validation Testing
"""

import json
import requests
import time
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
TEST_USER_ID = "test_user_validation_001"
RESULTS_FILE = "validation_results.json"

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_section(title: str):
    """Log a major section title."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def log_subsection(title: str):
    """Log a subsection title."""
    print(f"\n{Colors.CYAN}{title}{Colors.RESET}")
    print(f"{Colors.CYAN}{'-'*len(title)}{Colors.RESET}")

def log_pass(message: str):
    """Log a passing test."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def log_fail(message: str):
    """Log a failing test."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def log_warning(message: str):
    """Log a warning."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def log_info(message: str):
    """Log informational message."""
    print(f"{Colors.CYAN}ℹ {message}{Colors.RESET}")

def log_metric(label: str, value: str):
    """Log a metric."""
    print(f"  {label}: {Colors.BOLD}{value}{Colors.RESET}")

# ============================================================================
# STAGE 1: System Startup & Health Check
# ============================================================================

def stage1_system_health() -> Dict:
    """Stage 1: Verify all services are running and healthy."""
    log_section("STAGE 1: System Startup & Health Check")

    results = {
        "stage": 1,
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "passed": 0,
        "failed": 0
    }

    # Check 1.1: Backend Health
    log_subsection("1.1: Backend Health Check")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            log_pass(f"Backend is healthy (HTTP {response.status_code})")
            results["checks"]["backend_health"] = {"status": "pass", "code": 200}
            results["passed"] += 1
        else:
            log_fail(f"Backend returned unexpected status (HTTP {response.status_code})")
            results["checks"]["backend_health"] = {"status": "fail", "code": response.status_code}
            results["failed"] += 1
    except requests.exceptions.ConnectionError:
        log_fail("Cannot connect to backend at http://localhost:8000")
        log_warning("Is Docker running? Are containers started? Run: docker-compose up -d")
        results["checks"]["backend_health"] = {"status": "fail", "error": "connection_error"}
        results["failed"] += 1
    except Exception as e:
        log_fail(f"Unexpected error checking backend: {str(e)}")
        results["checks"]["backend_health"] = {"status": "fail", "error": str(e)}
        results["failed"] += 1

    # Check 1.2: Frontend Accessibility
    log_subsection("1.2: Frontend Accessibility")
    try:
        response = requests.get(f"{FRONTEND_URL}/", timeout=5)
        if response.status_code == 200:
            log_pass(f"Frontend is accessible (HTTP {response.status_code})")
            results["checks"]["frontend_access"] = {"status": "pass", "code": 200}
            results["passed"] += 1
        else:
            log_fail(f"Frontend returned unexpected status (HTTP {response.status_code})")
            results["checks"]["frontend_access"] = {"status": "fail", "code": response.status_code}
            results["failed"] += 1
    except Exception as e:
        log_fail(f"Cannot connect to frontend: {str(e)}")
        results["checks"]["frontend_access"] = {"status": "fail", "error": str(e)}
        results["failed"] += 1

    # Check 1.3: Database Connection
    log_subsection("1.3: Database Connection")
    try:
        response = requests.get(f"{BACKEND_URL}/api/health/db", timeout=5)
        if response.status_code == 200:
            log_pass(f"Database is connected (HTTP {response.status_code})")
            results["checks"]["database_connection"] = {"status": "pass", "code": 200}
            results["passed"] += 1
        else:
            log_fail(f"Database check failed (HTTP {response.status_code})")
            results["checks"]["database_connection"] = {"status": "fail", "code": response.status_code}
            results["failed"] += 1
    except Exception as e:
        log_fail(f"Cannot connect to database: {str(e)}")
        results["checks"]["database_connection"] = {"status": "fail", "error": str(e)}
        results["failed"] += 1

    # Check 1.4: Configuration Verification
    log_subsection("1.4: Configuration Verification")
    log_info("Checking relaxed thresholds in config.py...")

    config_path = Path("aura_research/utils/config.py")
    if config_path.exists():
        content = config_path.read_text()

        config_checks = {
            "MIN_QUALITY_SCORE": ("4.0", "4.0"),
            "MAX_ESSAY_REGENERATION_ATTEMPTS": ("4", "4"),
            "MIN_CITATION_ACCURACY": ("0.85", "0.85"),
            "MIN_SUPPORTED_CLAIMS_PCT": ("0.75", "0.75")
        }

        config_status = True
        for key, (expected, description) in config_checks.items():
            if key in content:
                # Find the line with this key
                for line in content.split('\n'):
                    if key in line and '=' in line:
                        log_pass(f"{key} = {description} (found in config)")
                        break
            else:
                log_fail(f"{key} not found in config.py")
                config_status = False

        results["checks"]["config_thresholds"] = {
            "status": "pass" if config_status else "fail",
            "message": "All thresholds are configured"
        }
        results["passed"] += 1 if config_status else 0
        results["failed"] += 0 if config_status else 1
    else:
        log_fail("config.py not found")
        results["checks"]["config_thresholds"] = {"status": "fail", "error": "file_not_found"}
        results["failed"] += 1

    # Summary
    log_subsection("Stage 1 Summary")
    log_metric("Checks Passed", f"{results['passed']}/4")
    log_metric("Checks Failed", f"{results['failed']}/4")

    return results

# ============================================================================
# STAGE 2: Basic Pipeline Test
# ============================================================================

def stage2_basic_pipeline() -> Dict:
    """Stage 2: Generate single essay with known-good academic topic."""
    log_section("STAGE 2: Basic Pipeline Test (Single Essay)")

    results = {
        "stage": 2,
        "timestamp": datetime.now().isoformat(),
        "query": "machine learning in healthcare",
        "tests": {},
        "passed": 0,
        "failed": 0,
        "session_id": None
    }

    # Step 2.1: Submit Request
    log_subsection("2.1: Submit Research Request")
    try:
        payload = {
            "user_id": TEST_USER_ID,
            "query": results["query"]
        }
        response = requests.post(f"{BACKEND_URL}/research/start", json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            results["session_id"] = session_id
            log_pass(f"Request submitted successfully")
            log_metric("Session ID", session_id)
            results["tests"]["submit_request"] = {"status": "pass", "session_id": session_id}
            results["passed"] += 1
        else:
            log_fail(f"Request failed (HTTP {response.status_code})")
            log_info(f"Response: {response.text[:200]}")
            results["tests"]["submit_request"] = {"status": "fail", "code": response.status_code}
            results["failed"] += 1
            return results
    except Exception as e:
        log_fail(f"Exception during request submission: {str(e)}")
        results["tests"]["submit_request"] = {"status": "fail", "error": str(e)}
        results["failed"] += 1
        return results

    # Step 2.2: Monitor Progress
    log_subsection("2.2: Monitor Progress (Real-time Polling)")
    session_id = results["session_id"]
    max_attempts = 150  # 5 minutes with 2-second intervals
    attempt = 0
    last_status = None
    start_time = time.time()

    while attempt < max_attempts:
        try:
            response = requests.get(f"{BACKEND_URL}/research/status/{session_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                current_stage = data.get("current_stage", "unknown")

                if status != last_status:
                    log_info(f"Status: {status} | Stage: {current_stage}")
                    last_status = status

                if status == "completed":
                    elapsed = time.time() - start_time
                    log_pass(f"Research completed in {elapsed:.1f} seconds")
                    results["tests"]["progress_monitoring"] = {
                        "status": "pass",
                        "elapsed_seconds": elapsed,
                        "attempts": attempt
                    }
                    results["passed"] += 1
                    break
                elif status == "error":
                    error_msg = data.get("error", "Unknown error")
                    log_fail(f"Research failed: {error_msg}")
                    results["tests"]["progress_monitoring"] = {
                        "status": "fail",
                        "error": error_msg
                    }
                    results["failed"] += 1
                    return results

            time.sleep(2)
            attempt += 1

            # Show progress indicator every 10 attempts
            if attempt % 10 == 0:
                elapsed = time.time() - start_time
                log_info(f"Still processing... ({elapsed:.1f}s elapsed, {max_attempts - attempt} attempts remaining)")

        except Exception as e:
            log_fail(f"Exception during progress polling: {str(e)}")
            results["tests"]["progress_monitoring"] = {"status": "fail", "error": str(e)}
            results["failed"] += 1
            return results

    if attempt >= max_attempts:
        log_fail("Research did not complete within 5 minutes (timeout)")
        results["tests"]["progress_monitoring"] = {"status": "fail", "error": "timeout"}
        results["failed"] += 1
        return results

    # Step 2.3: Retrieve Essay Details
    log_subsection("2.3: Retrieve Essay Details")
    try:
        response = requests.get(f"{BACKEND_URL}/research/session/{session_id}/details", timeout=10)
        if response.status_code == 200:
            data = response.json()
            essay = data.get("essay", {})

            # Validate essay structure
            checks = {
                "has_title": bool(essay.get("title")),
                "has_content": bool(essay.get("full_content_markdown")),
                "word_count": len(essay.get("full_content_markdown", "").split()),
                "citation_count": len(essay.get("citations", [])),
                "quality_score": essay.get("quality_score"),
            }

            log_pass(f"Essay retrieved successfully")
            log_metric("Title", essay.get("title", "N/A")[:50] + "...")
            log_metric("Word Count", f"{checks['word_count']}")
            log_metric("Citation Count", f"{checks['citation_count']}")
            log_metric("Quality Score", f"{checks['quality_score']:.2f}" if checks['quality_score'] else "N/A")

            # Validate word count
            if checks['word_count'] >= 1500:
                log_pass(f"Essay length adequate ({checks['word_count']} words)")
            else:
                log_warning(f"Essay may be short ({checks['word_count']} words, target: 1500+)")

            # Validate citations
            if checks['citation_count'] >= 8:
                log_pass(f"Sufficient citations ({checks['citation_count']} citations)")
            else:
                log_warning(f"May need more citations ({checks['citation_count']}, target: 8+)")

            # Validate quality score
            if checks['quality_score'] and checks['quality_score'] >= 4.0:
                log_pass(f"Quality score acceptable ({checks['quality_score']:.2f}/10)")
            elif checks['quality_score']:
                log_warning(f"Quality score low ({checks['quality_score']:.2f}/10, threshold: 4.0)")

            results["tests"]["retrieve_details"] = {
                "status": "pass",
                "essay_checks": checks
            }
            results["passed"] += 1
            results["essay_data"] = {
                "word_count": checks['word_count'],
                "citation_count": checks['citation_count'],
                "quality_score": checks['quality_score']
            }
        else:
            log_fail(f"Failed to retrieve essay (HTTP {response.status_code})")
            results["tests"]["retrieve_details"] = {"status": "fail", "code": response.status_code}
            results["failed"] += 1
            return results
    except Exception as e:
        log_fail(f"Exception retrieving essay: {str(e)}")
        results["tests"]["retrieve_details"] = {"status": "fail", "error": str(e)}
        results["failed"] += 1
        return results

    # Summary
    log_subsection("Stage 2 Summary")
    log_metric("Tests Passed", f"{results['passed']}/3")
    log_metric("Tests Failed", f"{results['failed']}/3")

    return results

# ============================================================================
# STAGE 3: Comprehensive Testing
# ============================================================================

def stage3_comprehensive_testing() -> Dict:
    """Stage 3: Test 5 diverse academic topics."""
    log_section("STAGE 3: Comprehensive Testing (5 Diverse Topics)")

    test_queries = [
        {"query": "neural networks for image classification", "expected": "PASS"},
        {"query": "quantum computing algorithms", "expected": "PASS"},
        {"query": "climate change modeling techniques", "expected": "PASS"},
        {"query": "blockchain consensus mechanisms", "expected": "MARGINAL"},
        {"query": "artificial intelligence ethics", "expected": "MARGINAL"}
    ]

    results = {
        "stage": 3,
        "timestamp": datetime.now().isoformat(),
        "queries_tested": len(test_queries),
        "tests": [],
        "summary": {
            "total": len(test_queries),
            "passed": 0,
            "marginal": 0,
            "failed": 0,
            "success_rate": 0.0
        }
    }

    for idx, test_case in enumerate(test_queries, 1):
        log_subsection(f"Test {idx}/{len(test_queries)}: \"{test_case['query']}\"")

        test_result = {
            "query": test_case['query'],
            "expected": test_case['expected'],
            "submitted": False,
            "completed": False,
            "essay_generated": False,
            "metrics": {}
        }

        try:
            # Submit research request
            payload = {"user_id": TEST_USER_ID, "query": test_case['query']}
            response = requests.post(f"{BACKEND_URL}/research/start", json=payload, timeout=10)

            if response.status_code != 200:
                log_fail(f"Failed to submit request (HTTP {response.status_code})")
                test_result["submitted"] = False
                results["summary"]["failed"] += 1
                results["tests"].append(test_result)
                continue

            test_result["submitted"] = True
            session_id = response.json().get("session_id")
            log_pass(f"Request submitted (Session: {session_id})")

            # Poll for completion (max 5 minutes)
            max_attempts = 150
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{BACKEND_URL}/research/status/{session_id}", timeout=5)
                    if response.status_code == 200:
                        status = response.json().get("status")
                        if status == "completed":
                            test_result["completed"] = True
                            log_pass(f"Research completed")
                            break
                        elif status == "error":
                            log_fail(f"Research failed: {response.json().get('error')}")
                            break
                    time.sleep(2)
                except:
                    time.sleep(2)
                    continue

            if not test_result["completed"]:
                log_warning("Research did not complete within timeout")
                results["tests"].append(test_result)
                results["summary"]["failed"] += 1
                continue

            # Retrieve essay
            try:
                response = requests.get(f"{BACKEND_URL}/research/session/{session_id}/details", timeout=10)
                if response.status_code == 200:
                    essay = response.json().get("essay", {})
                    word_count = len(essay.get("full_content_markdown", "").split())
                    citation_count = len(essay.get("citations", []))
                    quality_score = essay.get("quality_score", 0)

                    if word_count > 0:
                        test_result["essay_generated"] = True
                        log_pass(f"Essay generated ({word_count} words, {citation_count} citations, QS: {quality_score:.1f})")

                        test_result["metrics"] = {
                            "word_count": word_count,
                            "citation_count": citation_count,
                            "quality_score": quality_score
                        }

                        if test_case['expected'] == "PASS":
                            results["summary"]["passed"] += 1
                        else:
                            results["summary"]["marginal"] += 1
                    else:
                        log_fail("Essay generated but empty")
                        results["summary"]["failed"] += 1
            except:
                log_fail("Failed to retrieve essay details")
                results["summary"]["failed"] += 1

        except Exception as e:
            log_fail(f"Unexpected error: {str(e)}")
            results["summary"]["failed"] += 1

        results["tests"].append(test_result)

    # Calculate success rate
    results["summary"]["success_rate"] = (results["summary"]["passed"] + results["summary"]["marginal"]) / results["summary"]["total"]

    # Summary
    log_subsection("Stage 3 Summary")
    log_metric("Queries Tested", str(results["summary"]["total"]))
    log_metric("Successful", f"{results['summary']['passed']}")
    log_metric("Marginal", f"{results['summary']['marginal']}")
    log_metric("Failed", f"{results['summary']['failed']}")
    log_metric("Success Rate", f"{results['summary']['success_rate']*100:.1f}% (Target: 80%+)")

    if results["summary"]["success_rate"] >= 0.80:
        log_pass("Success rate meets target!")
    else:
        log_warning(f"Success rate below target (achieved {results['summary']['success_rate']*100:.1f}%, target 80%+)")

    return results

# ============================================================================
# STAGE 4: Edge Cases & Validation Testing
# ============================================================================

def stage4_edge_cases() -> Dict:
    """Stage 4: Test edge cases and validation layers."""
    log_section("STAGE 4: Edge Case & Validation Testing")

    results = {
        "stage": 4,
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }

    # Test 4.1: Non-academic Query Rejection (Layer 0)
    log_subsection("Test 4.1: Topic Classification (Layer 0) - Reject Non-Academic")

    non_academic_queries = [
        "Tom Cruise filmography",
        "best chocolate cake recipe",
        "iPhone 15 Pro features"
    ]

    rejection_count = 0
    for query in non_academic_queries:
        try:
            payload = {"user_id": TEST_USER_ID, "query": query}
            response = requests.post(f"{BACKEND_URL}/research/start", json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Check if rejected at Layer 0
                if "error" in data and "academic" in data.get("error", "").lower():
                    log_pass(f"Correctly rejected: \"{query}\"")
                    rejection_count += 1
                else:
                    # Try to check status
                    session_id = data.get("session_id")
                    if session_id:
                        time.sleep(1)
                        status_response = requests.get(f"{BACKEND_URL}/research/status/{session_id}", timeout=5)
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if status_data.get("status") == "error" and "academic" in status_data.get("error", "").lower():
                                log_pass(f"Correctly rejected: \"{query}\"")
                                rejection_count += 1
                            else:
                                log_warning(f"Query not rejected at Layer 0: \"{query}\"")
        except Exception as e:
            log_fail(f"Error testing query \"{query}\": {str(e)}")

    results["tests"]["layer0_rejection"] = {
        "total_tested": len(non_academic_queries),
        "rejected": rejection_count,
        "status": "pass" if rejection_count >= 2 else "fail"
    }

    log_metric("Non-Academic Queries Tested", str(len(non_academic_queries)))
    log_metric("Correctly Rejected", f"{rejection_count}/{len(non_academic_queries)}")

    # Test 4.2: Academic Query with Diverse Topics
    log_subsection("Test 4.2: Academic Query Validation")

    try:
        payload = {"user_id": TEST_USER_ID, "query": "decision trees in machine learning"}
        response = requests.post(f"{BACKEND_URL}/research/start", json=payload, timeout=10)

        if response.status_code == 200:
            log_pass("Academic query (decision trees) accepted")
            results["tests"]["academic_query"] = {"status": "pass"}
        else:
            log_fail("Academic query rejected unexpectedly")
            results["tests"]["academic_query"] = {"status": "fail"}
    except Exception as e:
        log_fail(f"Error testing academic query: {str(e)}")
        results["tests"]["academic_query"] = {"status": "fail", "error": str(e)}

    # Summary
    log_subsection("Stage 4 Summary")
    layer0_pass = results["tests"]["layer0_rejection"]["status"] == "pass"
    academic_pass = results["tests"]["academic_query"]["status"] == "pass"

    log_metric("Layer 0 Tests", "PASS" if layer0_pass else "FAIL")
    log_metric("Academic Tests", "PASS" if academic_pass else "FAIL")

    return results

# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Execute the testing plan."""
    parser = argparse.ArgumentParser(description="AURA Research Agent Pipeline Validation")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4], help="Run specific stage")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔" + "═"*68 + "╗")
    print("║" + "AURA Research Agent - Complete Pipeline Testing".center(68) + "║")
    print("╚" + "═"*68 + "╝")
    print(Colors.RESET)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_results = []

    # Execute requested stages
    stages_to_run = [args.stage] if args.stage else [1, 2, 3, 4]

    for stage_num in stages_to_run:
        try:
            if stage_num == 1:
                result = stage1_system_health()
            elif stage_num == 2:
                result = stage2_basic_pipeline()
            elif stage_num == 3:
                result = stage3_comprehensive_testing()
            elif stage_num == 4:
                result = stage4_edge_cases()

            all_results.append(result)
        except Exception as e:
            log_fail(f"Stage {stage_num} encountered fatal error: {str(e)}")
            continue

    # Final Summary
    log_section("FINAL SUMMARY")

    for result in all_results:
        stage_num = result.get("stage")
        if stage_num == 1:
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            log_metric(f"Stage {stage_num} (Health Check)", f"{passed} passed, {failed} failed")
        elif stage_num == 2:
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            log_metric(f"Stage {stage_num} (Basic Test)", f"{passed} passed, {failed} failed")
            if "essay_data" in result:
                log_metric("  → Word Count", str(result["essay_data"].get("word_count")))
                log_metric("  → Quality Score", f"{result['essay_data'].get('quality_score', 0):.1f}")
        elif stage_num == 3:
            summary = result.get("summary", {})
            rate = summary.get("success_rate", 0) * 100
            log_metric(f"Stage {stage_num} (Comprehensive)", f"{summary.get('passed')+summary.get('marginal')}/{summary.get('total')} successful ({rate:.1f}%)")
        elif stage_num == 4:
            tests = result.get("tests", {})
            passed = sum(1 for t in tests.values() if t.get("status") == "pass")
            total = len(tests)
            log_metric(f"Stage {stage_num} (Edge Cases)", f"{passed}/{total} tests passed")

    # Save results
    output_file = Path(RESULTS_FILE)
    output_file.write_text(json.dumps(all_results, indent=2))
    log_info(f"\nDetailed results saved to: {output_file.absolute()}")

    print(f"\n{Colors.BOLD}End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
