"""Visible, user-authorized target-computer agent."""

from .client import AgentClient, AgentResult, TargetIdentity
from .executor import WhitelistExecutor

__all__ = ["AgentClient", "AgentResult", "TargetIdentity", "WhitelistExecutor"]

