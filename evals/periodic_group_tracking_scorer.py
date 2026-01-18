"""
Periodic Group Tracking Scorer

Scores LLM responses against expected action items.

Scoring logic:
- Binary task matching: ALL 4 criteria must match
- Triplet score: matchedTasks / totalExpectedTasks
- Suite score: average of all triplet scores
"""

import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


def messages_match(expected_messages: List[Dict], response_messages: List[Dict]) -> bool:
    """
    Check bidirectional containment of relevant_task_messages.
    
    Both lists must contain the same messages (order independent).
    Matching is done on originating_time, sender, and content.
    """
    if not expected_messages and not response_messages:
        return True
    
    if len(expected_messages) != len(response_messages):
        return False
    
    def normalize(msg: Dict) -> tuple:
        return (
            msg.get("originating_time", "").strip(),
            msg.get("sender", "").strip(),
            msg.get("content", "").strip()
        )
    
    expected_set = set(normalize(m) for m in expected_messages)
    response_set = set(normalize(m) for m in response_messages)
    
    return expected_set == response_set


def task_matches(expected: Dict, response: Dict) -> bool:
    """
    Check if a single expected task matches a response task.
    ALL 4 criteria must match for a successful match.
    
    Criteria:
    1. timestamp_deadline exact match
    2. task_title regex search (pattern can match anywhere in response)
    3. task_description regex search (pattern can match anywhere in response)
    4. relevant_task_messages bidirectional containment
    """
    # 1. timestamp_deadline exact match
    if expected.get("timestamp_deadline") != response.get("timestamp_deadline"):
        return False
    
    # 2. task_title regex search (match anywhere in string)
    task_title_pattern = expected.get("task_title", "")
    response_title = response.get("task_title", "")
    try:
        if not re.search(task_title_pattern, response_title, re.IGNORECASE | re.DOTALL):
            return False
    except re.error:
        # Invalid regex, fall back to exact match
        if task_title_pattern != response_title:
            return False
    
    # 3. task_description regex search (match anywhere in string)
    task_desc_pattern = expected.get("task_description", "")
    response_desc = response.get("task_description", "")
    try:
        if not re.search(task_desc_pattern, response_desc, re.IGNORECASE | re.DOTALL):
            return False
    except re.error:
        # Invalid regex, fall back to exact match
        if task_desc_pattern != response_desc:
            return False
    
    # 4. relevant_task_messages bidirectional containment
    expected_messages = expected.get("relevant_task_messages", [])
    response_messages = response.get("relevant_task_messages", [])
    if not messages_match(expected_messages, response_messages):
        return False
    
    return True


def score_triplet(expected: List[Dict], response: List[Dict]) -> float:
    """
    Score a single triplet (prompt/response/expected).
    
    Score = matchedTasks / totalExpectedTasks
    Each expected task can only match one response task (no double counting).
    
    Returns:
        float: Score between 0.0 and 1.0
    """
    if not expected:
        return 1.0  # No expected items = perfect score
    
    matched = 0
    used_response_indices = set()
    
    for exp_item in expected:
        for i, resp_item in enumerate(response):
            if i not in used_response_indices and task_matches(exp_item, resp_item):
                matched += 1
                used_response_indices.add(i)
                break
    
    return matched / len(expected)


def score_triplet_detailed(expected: List[Dict], response: List[Dict], debug: bool = False) -> Dict[str, Any]:
    """
    Score a triplet with detailed results for debugging.
    
    Returns:
        Dict with score, matched count, expected count, and match details
    """
    if not expected:
        return {
            "score": 1.0,
            "matched": 0,
            "expected_count": 0,
            "match_details": []
        }
    
    matched = 0
    used_response_indices = set()
    match_details = []
    
    for exp_idx, exp_item in enumerate(expected):
        found_match = False
        failure_reasons = []
        
        for i, resp_item in enumerate(response):
            if i in used_response_indices:
                continue
                
            # Check each criterion and collect failure reasons
            reasons = []
            
            # 1. timestamp_deadline
            if exp_item.get("timestamp_deadline") != resp_item.get("timestamp_deadline"):
                reasons.append(f"timestamp_deadline: expected '{exp_item.get('timestamp_deadline')}' vs response '{resp_item.get('timestamp_deadline')}'")
            
            # 2. task_title regex
            title_pattern = exp_item.get("task_title", "")
            resp_title = resp_item.get("task_title", "")
            try:
                if not re.search(title_pattern, resp_title, re.IGNORECASE | re.DOTALL):
                    reasons.append(f"task_title: pattern '{title_pattern}' not found in '{resp_title}'")
            except re.error:
                if title_pattern != resp_title:
                    reasons.append(f"task_title: '{title_pattern}' != '{resp_title}' (invalid regex, exact match failed)")
            
            # 3. task_description regex
            desc_pattern = exp_item.get("task_description", "")
            resp_desc = resp_item.get("task_description", "")
            try:
                if not re.search(desc_pattern, resp_desc, re.IGNORECASE | re.DOTALL):
                    pattern_display = desc_pattern[:50] + ('...' if len(desc_pattern) > 50 else '')
                    reasons.append(f"task_description: pattern '{pattern_display}' not found")
            except re.error:
                if desc_pattern != resp_desc:
                    reasons.append(f"task_description: exact match failed (invalid regex)")
            
            # 4. messages match
            exp_msgs = exp_item.get("relevant_task_messages", [])
            resp_msgs = resp_item.get("relevant_task_messages", [])
            if not messages_match(exp_msgs, resp_msgs):
                reasons.append(f"relevant_task_messages: {len(exp_msgs)} expected vs {len(resp_msgs)} in response")
            
            if not reasons:
                matched += 1
                used_response_indices.add(i)
                match_details.append({
                    "expected_idx": exp_idx,
                    "response_idx": i,
                    "matched": True
                })
                found_match = True
                break
            else:
                failure_reasons.append({"response_idx": i, "reasons": reasons})
        
        if not found_match:
            detail = {
                "expected_idx": exp_idx,
                "response_idx": None,
                "matched": False,
                "expected_task": exp_item.get("task_title", "Unknown")
            }
            if debug and failure_reasons:
                detail["failure_reasons"] = failure_reasons
            match_details.append(detail)
    
    return {
        "score": matched / len(expected),
        "matched": matched,
        "expected_count": len(expected),
        "response_count": len(response),
        "match_details": match_details
    }


def score_suite(triplets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Score an entire test suite.
    
    Args:
        triplets: List of dicts, each containing:
            - "expected": List of expected tasks
            - "response": List of response tasks
            - "name": Optional name/identifier
    
    Returns:
        Dict with suite_score, triplet_scores, and summary
    """
    if not triplets:
        return {
            "suite_score": 0.0,
            "triplet_count": 0,
            "triplet_scores": []
        }
    
    triplet_scores = []
    total_score = 0.0
    
    for triplet in triplets:
        expected = triplet.get("expected", [])
        response = triplet.get("response", [])
        name = triplet.get("name", "Unknown")
        
        detailed = score_triplet_detailed(expected, response)
        detailed["name"] = name
        triplet_scores.append(detailed)
        total_score += detailed["score"]
    
    return {
        "suite_score": total_score / len(triplets),
        "triplet_count": len(triplets),
        "triplet_scores": triplet_scores
    }


def load_expected_file(path: Path) -> List[Dict]:
    """Load expected tasks from a JSON file."""
    content = path.read_text(encoding='utf-8')
    return json.loads(content)


def parse_response_json(response_text: str) -> List[Dict]:
    """
    Parse LLM response text to extract JSON array.
    Handles cases where the response may have extra text around the JSON.
    """
    # Try direct parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON array in the text
    # Look for pattern starting with [ and ending with ]
    match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    return []
