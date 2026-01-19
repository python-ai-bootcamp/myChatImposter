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


def load_config_file(config_path: Path) -> Dict[str, Any]:
    """Load and parse a config JSON file."""
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        print(f"  Warning: Could not parse {config_path.name}")
        return {}


def discover_triplets(suite_path: Path) -> List[Dict[str, Any]]:
    """
    Discover all evaluation triplets in the suite path.
    
    A triplet requires:
    - <epoch>_prompt.txt (required)
    - <epoch>_expected.txt (required for scoring)
    - <epoch>_response.txt (optional, for comparing against existing responses)
    - <epoch>_config.json (optional, for loading recorded LLM settings)
    """
    triplets = []
    
    # Find all prompt files recursively
    for prompt_file in suite_path.rglob("*_prompt.txt"):
        epoch = prompt_file.stem.replace("_prompt", "")
        expected_file = prompt_file.with_name(f"{epoch}_expected.txt")
        response_file = prompt_file.with_name(f"{epoch}_response.txt")
        config_file = prompt_file.with_name(f"{epoch}_config.json")
        
        if not expected_file.exists():
            print(f"  Skipping {prompt_file.name}: no matching _expected.txt")
            continue
        
        triplet = {
            "name": f"{prompt_file.parent.name}/{epoch}",
            "prompt_file": prompt_file,
            "expected_file": expected_file,
            "response_file": response_file if response_file.exists() else None,
            "config_file": config_file if config_file.exists() else None,
            "config": load_config_file(config_file) if config_file.exists() else {}
        }
        triplets.append(triplet)
    
    return triplets



async def execute_prompt(
    user_input: str,
    system_prompt: str,
    model: str,
    temperature: float,
    api_key: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    seed: Optional[int] = None
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
    if reasoning_effort:
        llm_kwargs["reasoning_effort"] = reasoning_effort
    if seed is not None:
        llm_kwargs["seed"] = seed
    
    llm = ChatOpenAI(**llm_kwargs)
    
    # Use direct messages instead of ChatPromptTemplate to avoid {{ escaping issues
    # The recorded prompt is already fully formatted, not a template
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_core.output_parsers import StrOutputParser
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    # Execute directly
    response = await llm.ainvoke(messages)
    return response.content


async def run_evaluation(
    suite_path: Path,
    model: str,
    temperature: float,
    api_key: Optional[str] = None,
    dry_run: bool = False,
    debug: bool = False,
    config_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run evaluation on all triplets in the suite.
    
    Args:
        suite_path: Path to the test suite directory
        model: LLM model to use (CLI default, may be overridden by config)
        temperature: Temperature setting (CLI default, may be overridden by config)
        api_key: Optional API key
        dry_run: If True, only score existing responses without making new LLM calls
        config_overrides: Dict of CLI config overrides (system_prompt, model, etc.)
    
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
    overrides = config_overrides or {}
    
    for triplet in triplets:
        print(f"Processing: {triplet['name']}")
        
        # Parse prompt file
        parsed = parse_prompt_file(triplet["prompt_file"])
        user_input = parsed["user_input"]
        
        # Determine system prompt: CLI override > recorded prompt
        if "system_prompt" in overrides:
            system_prompt = overrides["system_prompt"]
            # Substitute language_code if present in overrides
            if "language_code" in overrides:
                system_prompt = system_prompt.replace("{language_code}", overrides["language_code"])
            print(f"  Using overridden system prompt")
        else:
            system_prompt = parsed["system_prompt"]
            print(f"  Using recorded system prompt")
        
        # Merge configs: script defaults < recorded config < CLI overrides
        recorded_config = triplet.get("config", {})
        
        # Start with recorded config, then apply CLI overrides
        effective_config = dict(recorded_config)
        effective_config.update(overrides)
        
        # Get effective values (fall back to function args which have script defaults)
        effective_model = effective_config.get("model", model)
        effective_temp = effective_config.get("temperature", temperature)
        effective_reasoning = effective_config.get("reasoning_effort")
        effective_seed = effective_config.get("seed")
        
        # Log config sources
        model_source = "override" if "model" in overrides else ("recorded" if "model" in recorded_config else "default")
        temp_source = "override" if "temperature" in overrides else ("recorded" if "temperature" in recorded_config else "default")
        reasoning_str = f", reasoning={effective_reasoning}" if effective_reasoning else ""
        seed_str = f", seed={effective_seed}" if effective_seed is not None else ""
        print(f"  Config: model={effective_model} ({model_source}), temp={effective_temp} ({temp_source}){reasoning_str}{seed_str}")
        
        # Get API key from config (recorded or override)
        effective_api_key = effective_config.get("api_key")
        if effective_api_key == "***MASKED***":
            effective_api_key = None  # Masked key is not usable
        
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
            if debug:
                print(f"  === SYSTEM PROMPT ===")
                print(system_prompt)
                print(f"  === USER INPUT ===")
                print(user_input)
                print(f"  ===")
            print(f"  Executing LLM call...")
            response_text = await execute_prompt(
                user_input=user_input,
                system_prompt=system_prompt,
                model=effective_model,
                temperature=effective_temp,
                api_key=effective_api_key,
                reasoning_effort=effective_reasoning,
                seed=effective_seed
            )
            if debug:
                print(f"  === LLM RESPONSE ===")
                print(response_text)
                print(f"  ===")
        
        # Parse response and expected
        response_tasks = parse_response_json(response_text)
        expected_tasks = load_expected_file(triplet["expected_file"])
        
        # Score
        detailed = score_triplet_detailed(expected_tasks, response_tasks, debug=debug)
        detailed["name"] = triplet["name"]
        results.append({
            "expected": expected_tasks,
            "response": response_tasks,
            "name": triplet["name"],
            **detailed
        })
        
        print(f"  Expected: {len(expected_tasks)}, Matched: {detailed['matched']}, Score: {detailed['score']:.2f}")
        
        # Print debug info for failed matches
        if debug:
            for detail in detailed.get("match_details", []):
                if not detail.get("matched") and "failure_reasons" in detail:
                    print(f"    [FAILED] Expected task {detail['expected_idx']}: {detail.get('expected_task', 'Unknown')}")
                    for failure in detail["failure_reasons"]:
                        print(f"      vs Response {failure['response_idx']}:")
                        for reason in failure["reasons"]:
                            print(f"        - {reason}")
    
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
            "overrides_applied": list(overrides.keys()) if overrides else []
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
        "--dry-run",
        action="store_true",
        help="Only score existing responses, don't make new LLM calls"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug output showing why matches failed"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output results JSON file"
    )
    
    # List of valid config keys for help text
    valid_config_keys = [
        "model",
        "temperature", 
        "reasoning_effort",
        "seed",
        "provider_name",
        "language_code",
        "api_key_source",
        "system_prompt",
        "system_prompt_file"
    ]
    
    parser.add_argument(
        "--config-override",
        type=str,
        action="append",
        metavar="KEY=VALUE",
        help=f"Override a config parameter. Can be used multiple times. "
             f"Valid keys: {', '.join(valid_config_keys)}. "
             f"Example: --config-override model=gpt-4o --config-override system_prompt_file=./new_prompt.txt"
    )
    
    args = parser.parse_args()
    
    # Parse config overrides into a dict
    config_overrides = {}
    if args.config_override:
        for override in args.config_override:
            if "=" not in override:
                parser.error(f"Invalid config override format: '{override}'. Use KEY=VALUE format.")
            key, value = override.split("=", 1)
            if key not in valid_config_keys:
                parser.error(f"Invalid config key: '{key}'. Valid keys: {', '.join(valid_config_keys)}")
            # Try to convert to appropriate type
            if key == "temperature":
                try:
                    value = float(value)
                except ValueError:
                    parser.error(f"Invalid value for temperature: '{value}'. Must be a number.")
            elif key == "seed":
                try:
                    value = int(value)
                except ValueError:
                    parser.error(f"Invalid value for seed: '{value}'. Must be an integer.")
            config_overrides[key] = value
    
    # Handle system_prompt_file: load file content into system_prompt
    if "system_prompt_file" in config_overrides:
        prompt_file = Path(config_overrides["system_prompt_file"])
        if not prompt_file.exists():
            parser.error(f"System prompt file not found: {prompt_file}")
        config_overrides["system_prompt"] = prompt_file.read_text(encoding='utf-8')
        del config_overrides["system_prompt_file"]
    
    # Run evaluation - model/temperature come from config_overrides or use defaults
    results = asyncio.run(run_evaluation(
        suite_path=args.suite_path,
        model=config_overrides.get("model", "gpt-4o"),
        temperature=config_overrides.get("temperature", 0.3),
        dry_run=args.dry_run,
        debug=args.debug,
        config_overrides=config_overrides
    ))
    
    # Output results
    if args.output:
        args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"Results saved to {args.output}")
    
    return 0 if results.get("suite_score", 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
