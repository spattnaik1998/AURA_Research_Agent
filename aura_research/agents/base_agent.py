"""
Base Agent class for AURA multi-agent system
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from enum import Enum


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseAgent(ABC):
    """Abstract base class for all AURA agents"""

    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.IDLE
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None

    @abstractmethod
    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's task

        Args:
            task: Task parameters specific to the agent

        Returns:
            Dictionary containing the agent's results
        """
        pass

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper method that handles execution lifecycle

        Args:
            task: Task parameters

        Returns:
            Execution result with metadata
        """
        self.status = AgentStatus.RUNNING
        self.start_time = datetime.now()

        try:
            self.result = await self.run(task)
            self.status = AgentStatus.COMPLETED
            self.end_time = datetime.now()

            return {
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "status": self.status.value,
                "result": self.result,
                "execution_time": (self.end_time - self.start_time).total_seconds(),
                "timestamp": self.end_time.isoformat()
            }

        except Exception as e:
            self.status = AgentStatus.FAILED
            self.error = str(e)
            self.end_time = datetime.now()

            return {
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "status": self.status.value,
                "error": self.error,
                "execution_time": (self.end_time - self.start_time).total_seconds(),
                "timestamp": self.end_time.isoformat()
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
