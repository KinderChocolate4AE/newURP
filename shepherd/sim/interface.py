"""Pluggable 6-DOF simulator backend interface (THE MEANS).

The research goal (shepherd.game) is sim-agnostic; concrete 6-DOF backends implement
this interface so the backend (WarSim SE3 / Isaac Lab / PX4-ROS2-Gazebo) is swappable
and decided with lab resources. Target = 6-DOF SE3 rigid-body.
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class EnvBackend(ABC):
    """Minimal 6-DOF env contract consumed by shepherd.train / shepherd.eval."""
    @abstractmethod
    def reset(self, seed: int): ...
    @abstractmethod
    def step(self, action): ...        # -> (obs, reward, terminated, truncated, info)
    @abstractmethod
    def observe(self): ...             # role-structured obs (limiters / finisher / adversary)
