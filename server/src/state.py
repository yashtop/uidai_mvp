# server/src/state.py
"""
LangGraph State Schema
Defines the state that flows through the agent graph
"""
from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime

class TestRunState(TypedDict, total=False):
    """
    State that flows through the LangGraph pipeline
    Each agent reads from and writes to this state
    """
    # ============================================================
    # INPUT (from user)
    # ============================================================
    run_id: str
    url: str
    test_creation_mode: Literal["ai", "record", "hybrid"]
    execution_mode: Literal["headless", "headed"]
    preset: str  # "quick" | "balanced" | "deep"
    user_story: Optional[str]
    max_heal_attempts: int
    auto_heal: bool
    
    # ============================================================
    # DISCOVERY PHASE
    # ============================================================
    discovery_data: Optional[Dict[str, Any]]
    pages_count: int
    elements_count: int
    
    # ============================================================
    # RECORDING PHASE (record/hybrid modes)
    # ============================================================
    recorded_test_path: Optional[str]
    recording_analysis: Optional[Dict[str, Any]]
    
    # ============================================================
    # STORY PHASE
    # ============================================================
    final_story: str
    story_source: Literal["user_provided", "ai_generated", "recording_enhanced", "fallback"]
    story_model: Optional[str]
    
    # ============================================================
    # SCENARIO PHASE
    # ============================================================
    scenarios: List[Dict[str, Any]]
    scenarios_count: int
    scenario_model: Optional[str]
    
    # ============================================================
    # CODE GENERATION PHASE
    # ============================================================
    generated_tests: List[Dict[str, Any]]
    tests_directory: str
    code_model: Optional[str]
    
    # ============================================================
    # EXECUTION PHASE
    # ============================================================
    execution_result: Optional[Dict[str, Any]]
    tests_passed: int
    tests_failed: int
    tests_total: int
    
    # ============================================================
    # HEALING PHASE
    # ============================================================
    healing_attempts: int
    healing_result: Optional[Dict[str, Any]]
    is_healed: bool
    
    # ============================================================
    # METADATA
    # ============================================================
    phase: str  # Current phase name
    status: str  # "pending" | "running" | "completed" | "failed"
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]