#!/usr/bin/env python3
"""
LLM Evaluation Runner for Periodic Group Tracking

Usage:
    python -m evals.run_evals --suite-path ./log/llm_recordings/yahav/periodic_group_tracking --model gpt-4o --temperature 0.3
    python -m evals.run_evals --suite-path ./log/llm_recordings/yahav/periodic_group_tracking --system-prompt-file ./prompts/v2.txt
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.periodic_group_tracking_scorer import (
    score_triplet_detailed,
    score_suite,
    load_expected_file,
    parse_response_json
)


def parse_prompt_file(prompt_path: Path) -> Dict[str, str]:
    """
    Parse a recorded prompt file to extract system prompt and user input.
    
    Returns:
        Dict with 'system_prompt' and 'user_input' keys
    """
    content = prompt_path.read_text(encoding='utf-8')
    
    result = {
        'system_prompt': '',
        'user_input': '',
        'history': ''
    }
    
    # Parse sections
    sections = content.split('===')
    current_section = None
    
    for i, section in enumerate(sections):
        section = section.strip()
        if section == 'SYSTEM PROMPT':
            current_section = 'system_prompt'
        elif section == 'USER INPUT':
            current_section = 'user_input'
        elif section == 'HISTORY':
            current_section = 'history'
        elif current_section and section:
            result[current_section] = section
    
    return result


def discover_triplets(suite_path: Path) -> List[Dict[str, Any]]:
    """
    Discover all evaluation triplets in the suite path.
    
    A triplet requires:
    - <epoch>_prompt.txt (required)
    - <epoch>_expected.txt (required for scoring)
    - <epoch>_response.txt (optional, for comparing against existing responses)
    """
    triplets = []
    
    # Find all prompt files recursively
    for prompt_file in suite_path.rglob("*_prompt.txt"):
        epoch = prompt_file.stem.replace("_prompt", "")
        expected_file = prompt_file.with_name(f"{epoch}_expected.txt")
        response_file = prompt_file.with_name(f"{epoch}_response.txt")
        
        if not expected_file.exists():
            print(f"  Skipping {prompt_file.name}: no matching _expected.txt")
            continue
        
        triplet = {
            "name": f"{prompt_file.parent.name}/{epoch}",
            "prompt_file": prompt_file,
            "expected_file": expected_file,
            "response_file": response_file if response_file.exists() else None
        }
        triplets.append(triplet)
    
    return triplets


async def execute_prompt(
    user_input: str,
    system_prompt: str,
    model: str,
    temperature: float,
    api_key: Optional[str] = None
) -> str:
    """
    Execute a prompt using the LLM.
    
    Returns the LLM response text.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    # Setup LLM
    llm_kwargs = {
        "model": model,
        "temperature": temperature
    }
    if api_key:
        llm_kwargs["api_key"] = api_key
    
    llm = ChatOpenAI(**llm_kwargs)
    
    # Create chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    chain = prompt | llm | StrOutputParser()
    
    # Execute
    result = await chain.ainvoke({"input": user_input})
    return result


async def run_evaluation(
    suite_path: Path,
    model: str,
    temperature: float,
    system_prompt_override: Optional[str] = None,
    language_code: Optional[str] = None,
    use_recorded_prompt: bool = False,
    api_key: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run evaluation on all triplets in the suite.
    
    Args:
        suite_path: Path to the test suite directory
        model: LLM model to use
        temperature: Temperature setting
        system_prompt_override: Custom system prompt (if None and not use_recorded_prompt, use default)
        language_code: Language code to substitute in prompt
        use_recorded_prompt: If True, use the system prompt from recorded files
        api_key: Optional API key
        dry_run: If True, only score existing responses without making new LLM calls
    
    Returns:
        Evaluation results with scores
    """
    print(f"\n{'='*60}")
    print(f"LLM Evaluation Runner")
    print(f"{'='*60}")
    print(f"Suite path: {suite_path}")
    print(f"Model: {model}")
    print(f"Temperature: {temperature}")
    print(f"Dry run: {dry_run}")
    print(f"{'='*60}\n")
    
    # Discover triplets
    print("Discovering test triplets...")
    triplets = discover_triplets(suite_path)
    print(f"Found {len(triplets)} triplets with expected files\n")
    
    if not triplets:
        return {"error": "No valid triplets found", "suite_score": 0.0}
    
    # Process each triplet
    results = []
    
    for triplet in triplets:
        print(f"Processing: {triplet['name']}")
        
        # Parse prompt file
        parsed = parse_prompt_file(triplet["prompt_file"])
        user_input = parsed["user_input"]
        
        # Determine system prompt
        if use_recorded_prompt:
            system_prompt = parsed["system_prompt"]
        elif system_prompt_override:
            system_prompt = system_prompt_override
            if language_code:
                system_prompt = system_prompt.replace("{language_code}", language_code)
        else:
            system_prompt = parsed["system_prompt"]
        
        # Get response
        if dry_run and triplet["response_file"]:
            # Use existing response
            response_text = triplet["response_file"].read_text(encoding='utf-8')
            print(f"  Using existing response from {triplet['response_file'].name}")
        elif dry_run:
            print(f"  Skipping (dry run, no existing response)")
            continue
        else:
            # Execute new LLM call
            print(f"  Executing LLM call...")
            response_text = await execute_prompt(
                user_input=user_input,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                api_key=api_key
            )
        
        # Parse response and expected
        response_tasks = parse_response_json(response_text)
        expected_tasks = load_expected_file(triplet["expected_file"])
        
        # Score
        detailed = score_triplet_detailed(expected_tasks, response_tasks)
        detailed["name"] = triplet["name"]
        results.append({
            "expected": expected_tasks,
            "response": response_tasks,
            "name": triplet["name"],
            **detailed
        })
        
        print(f"  Expected: {len(expected_tasks)}, Matched: {detailed['matched']}, Score: {detailed['score']:.2f}")
    
    # Calculate suite score
    if not results:
        return {"error": "No results", "suite_score": 0.0}
    
    suite_score = sum(r["score"] for r in results) / len(results)
    
    print(f"\n{'='*60}")
    print(f"SUITE SCORE: {suite_score:.2f} (average of {len(results)} triplets)")
    print(f"{'='*60}\n")
    
    return {
        "suite_score": suite_score,
        "triplet_count": len(results),
        "triplet_scores": results,
        "config": {
            "model": model,
            "temperature": temperature,
            "use_recorded_prompt": use_recorded_prompt
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Run LLM evaluations for periodic group tracking")
    
    parser.add_argument(
        "--suite-path",
        type=Path,
        required=True,
        help="Path to the test suite directory containing triplets"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="LLM model to use (default: gpt-4o)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Temperature setting (default: 0.3)"
    )
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="Path to file containing system prompt override"
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        help="Inline system prompt override"
    )
    parser.add_argument(
        "--language-code",
        type=str,
        help="Language code to substitute in prompt"
    )
    parser.add_argument(
        "--use-recorded-prompt",
        action="store_true",
        help="Use system prompts from recorded files (baseline comparison)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only score existing responses, don't make new LLM calls"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output results JSON file"
    )
    
    args = parser.parse_args()
    
    # Determine system prompt override
    system_prompt_override = None
    if args.system_prompt_file:
        system_prompt_override = args.system_prompt_file.read_text(encoding='utf-8')
    elif args.system_prompt:
        system_prompt_override = args.system_prompt
    
    # Run evaluation
    results = asyncio.run(run_evaluation(
        suite_path=args.suite_path,
        model=args.model,
        temperature=args.temperature,
        system_prompt_override=system_prompt_override,
        language_code=args.language_code,
        use_recorded_prompt=args.use_recorded_prompt,
        dry_run=args.dry_run
    ))
    
    # Output results
    if args.output:
        args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"Results saved to {args.output}")
    
    return 0 if results.get("suite_score", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
