# agents/evaluation/evaluation_agent.py
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
import time
import uuid

class EvaluationAgent:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def start_log(self, agent_name: str, action: str) -> str:
        """Mark the start of an agent action; returns a log_id"""
        log_id = str(uuid.uuid4())
        entry = {
            "log_id": log_id,
            "agent": agent_name,
            "action": action,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "end_time": None,
            "duration": None,
            "status": "in_progress",
            "reason": None
        }
        self.logs.append(entry)
        return log_id

    def end_log(self, log_id: str, status: str = "success", reason: str | None = None):
        """Mark the end of an action with status and optional reason"""
        for entry in self.logs:
            if entry["log_id"] == log_id:
                entry["end_time"] = datetime.utcnow().isoformat() + "Z"
                try:
                    start = datetime.fromisoformat(entry["start_time"].replace("Z", ""))
                    end = datetime.fromisoformat(entry["end_time"].replace("Z", ""))
                    entry["duration"] = round((end - start).total_seconds(), 3)
                except Exception:
                    entry["duration"] = None
                entry["status"] = status
                entry["reason"] = reason
                break

    def summary(self) -> Dict[str, Any]:
        total = len(self.logs)
        success = sum(1 for e in self.logs if e["status"] == "success")
        fail = sum(1 for e in self.logs if e["status"] != "success")
        avg_time = round(
            sum(e["duration"] or 0 for e in self.logs) / success, 3
        ) if success else None

        # Count by agent
        agent_stats: Dict[str, Dict[str, Any]] = {}
        for e in self.logs:
            ag = e["agent"]
            if ag not in agent_stats:
                agent_stats[ag] = {"calls": 0, "success": 0, "fail": 0}
            agent_stats[ag]["calls"] += 1
            if e["status"] == "success":
                agent_stats[ag]["success"] += 1
            else:
                agent_stats[ag]["fail"] += 1

        return {
            "total_calls": total,
            "success": success,
            "fail": fail,
            "avg_duration_sec": avg_time,
            "per_agent": agent_stats,
            "recent_logs": self.logs[-5:]  # last 5 actions
        }
