"""
Health Check Service
Provides comprehensive system health monitoring for the AURA Research Agent
"""

import os
import time
import psutil
from typing import Dict, Any
from datetime import datetime


# Track service startup time
_service_start_time = time.time()


class HealthService:
    """
    Comprehensive health check service monitoring API keys, database,
    disk space, memory, and service uptime.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern for health service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize health service."""
        self.start_time = _service_start_time

    # ==================== API Key Checks ====================

    def check_api_keys(self) -> Dict[str, Any]:
        """
        Verify all required API keys are configured.

        Returns:
            Dictionary with key names and configuration status
        """
        api_keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "SERPER_API_KEY": os.getenv("SERPER_API_KEY"),
            "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY"),
            "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
        }

        status = {}
        for key_name, key_value in api_keys.items():
            if key_value:
                # Mask the actual value, show only if present
                status[key_name] = "configured"
            else:
                status[key_name] = "missing"

        # Overall status
        missing_keys = [k for k, v in status.items() if v == "missing"]
        if missing_keys:
            return {
                "status": "warning",
                "message": f"Missing keys: {', '.join(missing_keys)}",
                "keys": status
            }

        return {
            "status": "healthy",
            "message": "All API keys configured",
            "keys": status
        }

    # ==================== Database Checks ====================

    def check_database(self) -> Dict[str, Any]:
        """
        Test database connectivity and measure latency.

        Returns:
            Dictionary with connection status and latency
        """
        try:
            from ..database.connection import get_db_connection

            # Measure connection latency
            start_time = time.time()
            db_connection = get_db_connection()
            conn = db_connection.connect()
            latency_ms = (time.time() - start_time) * 1000

            if conn:
                return {
                    "status": "healthy",
                    "connected": True,
                    "latency_ms": round(latency_ms, 2),
                    "database": "AURA_Research",
                    "message": f"Connected ({latency_ms:.0f}ms)"
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "message": "Connection test failed"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "message": f"Database connection error: {str(e)}"
            }

    # ==================== Disk Space Checks ====================

    def check_disk_space(self) -> Dict[str, Any]:
        """
        Monitor disk space usage.

        Returns:
            Dictionary with disk usage statistics
        """
        try:
            # Get disk usage for root partition
            disk_info = psutil.disk_usage('/')
            usage_percent = disk_info.percent

            # Determine status
            if usage_percent > 95:
                status = "critical"
                message = f"Critical: {usage_percent}% disk used"
            elif usage_percent > 90:
                status = "warning"
                message = f"Warning: {usage_percent}% disk used"
            else:
                status = "healthy"
                message = f"Healthy: {usage_percent}% disk used"

            return {
                "status": status,
                "disk_used_percent": usage_percent,
                "disk_total_gb": round(disk_info.total / (1024**3), 2),
                "disk_used_gb": round(disk_info.used / (1024**3), 2),
                "disk_free_gb": round(disk_info.free / (1024**3), 2),
                "message": message
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e),
                "message": f"Failed to check disk space: {str(e)}"
            }

    # ==================== Memory Checks ====================

    def check_memory(self) -> Dict[str, Any]:
        """
        Monitor memory usage.

        Returns:
            Dictionary with memory statistics
        """
        try:
            # Get process memory
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 ** 2)

            # Get system memory
            memory_info = psutil.virtual_memory()
            usage_percent = memory_info.percent

            # Determine status
            if usage_percent > 95:
                status = "critical"
                message = f"Critical: {usage_percent}% memory used"
            elif usage_percent > 85:
                status = "warning"
                message = f"Warning: {usage_percent}% memory used"
            else:
                status = "healthy"
                message = f"Healthy: {usage_percent}% memory used"

            return {
                "status": status,
                "memory_used_percent": usage_percent,
                "memory_total_gb": round(memory_info.total / (1024**3), 2),
                "memory_used_gb": round(memory_info.used / (1024**3), 2),
                "memory_free_gb": round(memory_info.available / (1024**3), 2),
                "process_memory_mb": round(process_memory_mb, 2),
                "message": message
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e),
                "message": f"Failed to check memory: {str(e)}"
            }

    # ==================== Uptime Check ====================

    def check_uptime(self) -> Dict[str, Any]:
        """
        Get service uptime.

        Returns:
            Dictionary with uptime information
        """
        uptime_seconds = time.time() - self.start_time
        uptime_minutes = uptime_seconds / 60
        uptime_hours = uptime_minutes / 60

        return {
            "status": "running",
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_minutes": round(uptime_minutes, 2),
            "uptime_hours": round(uptime_hours, 2),
            "started_at": datetime.fromtimestamp(self.start_time).isoformat(),
            "message": f"Running for {int(uptime_hours)}h {int(uptime_minutes % 60)}m"
        }

    # ==================== Overall Health ====================

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status (all checks).

        Returns:
            Dictionary with full health status and all subsystem checks
        """
        api_keys = self.check_api_keys()
        database = self.check_database()
        disk = self.check_disk_space()
        memory = self.check_memory()
        uptime = self.check_uptime()

        # Determine overall status
        statuses = [
            api_keys.get("status", "unknown"),
            database.get("status", "unknown"),
            disk.get("status", "unknown"),
            memory.get("status", "unknown"),
        ]

        if "critical" in statuses or "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "api_keys": api_keys,
                "database": database,
                "disk_space": disk,
                "memory": memory,
                "uptime": uptime,
            }
        }

    # ==================== Readiness Check ====================

    def get_readiness_status(self) -> Dict[str, Any]:
        """
        Get quick readiness check (for load balancers).
        Only checks critical dependencies, not all diagnostics.

        Returns:
            Dictionary with readiness status (minimal checks)
        """
        try:
            # Check only critical items: API keys and database
            api_keys = self.check_api_keys()
            database = self.check_database()

            # Ready if both are configured and connected
            is_ready = (
                api_keys.get("status") == "healthy" and
                database.get("status") == "healthy"
            )

            return {
                "ready": is_ready,
                "timestamp": datetime.utcnow().isoformat(),
                "api_keys": api_keys.get("status", "unknown"),
                "database": database.get("status", "unknown"),
                "message": "Ready to accept requests" if is_ready else "Service not ready"
            }
        except Exception as e:
            return {
                "ready": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "message": f"Readiness check failed: {str(e)}"
            }


# Singleton instance
_health_service = None


def get_health_service() -> HealthService:
    """
    Get the singleton health service instance.

    Returns:
        HealthService instance
    """
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
