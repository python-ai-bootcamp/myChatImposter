#!/bin/bash
#
# Eval Parameter Sweep Script
# Runs evaluations across temperature and reasoning_effort combinations
#
# Usage: ./run_sweep.sh [--temp-min MIN] [--temp-max MAX] [--temp-step STEP] 
#                       [--reasoning-min MIN] [--reasoning-max MAX] 
#                       [--iterations N] [--suite-path PATH]
#
# Example: ./run_sweep.sh --temp-min 0.0 --temp-max 1.0 --temp-step 0.2 --iterations 3

# Default values
TEMP_MIN=0.0
TEMP_MAX=1.0
TEMP_STEP=0.2
SUITE_PATH="./log/llm_recordings/yahav/periodic_group_tracking/"
REASONING_MIN="minimal"
REASONING_MAX="high"
ITERATIONS=1
SEED=""
MODEL=""

# All reasoning effort values in order (from minimal to highest)
ALL_REASONING_EFFORTS=("minimal" "low" "medium" "high")

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "Eval Parameter Sweep Script"
            echo ""
            echo "Usage: ./run_sweep.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --temp-min FLOAT       Minimum temperature (default: 0.0)"
            echo "  --temp-max FLOAT       Maximum temperature (default: 1.0)"
            echo "  --temp-step FLOAT      Temperature step size (default: 0.2)"
            echo "  --reasoning-min VALUE  Minimum reasoning effort (default: minimal)"
            echo "  --reasoning-max VALUE  Maximum reasoning effort (default: high)"
            echo "  --iterations N         Number of iterations per config (default: 1)"
            echo "  --seed INT             Seed for reproducible results (optional)"
            echo "  --model NAME           Override model (e.g. gpt-5-mini)"
            echo "  --suite-path PATH      Path to test suite directory"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Temperature values:"
            echo "  Range: 0.0 to 2.0 (OpenAI allowed range)"
            echo "  0.0       = Deterministic, most focused output"
            echo "  0.3-0.7   = Balanced (good for structured tasks like JSON)"
            echo "  1.0       = Default, moderate creativity"
            echo "  1.0-2.0   = More creative/random"
            echo ""
            echo "Reasoning effort values (in order from lowest to highest):"
            echo "  minimal   = Fastest, least thinking"
            echo "  low       = Quick responses"
            echo "  medium    = Balanced thinking"
            echo "  high      = Most thorough, slowest"
            echo ""
            echo "Examples:"
            echo "  ./run_sweep.sh --temp-min 0.0 --temp-max 0.5 --temp-step 0.1"
            echo "  ./run_sweep.sh --model gpt-5-mini --iterations 3"
            echo "  ./run_sweep.sh --seed 42 --temp-min 0.0 --temp-max 0.0  # Reproducible run"
            exit 0
            ;;
        --temp-min)
            TEMP_MIN="$2"
            shift 2
            ;;
        --temp-max)
            TEMP_MAX="$2"
            shift 2
            ;;
        --temp-step)
            TEMP_STEP="$2"
            shift 2
            ;;
        --reasoning-min)
            REASONING_MIN="$2"
            shift 2
            ;;
        --reasoning-max)
            REASONING_MAX="$2"
            shift 2
            ;;
        --iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --suite-path)
            SUITE_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Filter reasoning efforts based on min/max
REASONING_EFFORTS=()
in_range=false
for effort in "${ALL_REASONING_EFFORTS[@]}"; do
    if [ "$effort" == "$REASONING_MIN" ]; then
        in_range=true
    fi
    if [ "$in_range" == true ]; then
        REASONING_EFFORTS+=("$effort")
    fi
    if [ "$effort" == "$REASONING_MAX" ]; then
        break
    fi
done

if [ ${#REASONING_EFFORTS[@]} -eq 0 ]; then
    echo "ERROR: Invalid reasoning effort range: $REASONING_MIN to $REASONING_MAX"
    echo "Valid values: ${ALL_REASONING_EFFORTS[*]}"
    exit 1
fi

# Results files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Determine project root (one directory up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/log/sweep_results"

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

RAW_RESULTS_FILE="$RESULTS_DIR/sweep_raw_${TIMESTAMP}.csv"
SUMMARY_FILE="$RESULTS_DIR/sweep_summary_${TIMESTAMP}.csv"

echo "temperature,reasoning_effort,model,iteration,suite_score" > "$RAW_RESULTS_FILE"
echo "temperature,reasoning_effort,model,avg_score,min_score,max_score,stdev" > "$SUMMARY_FILE"

echo "============================================================"
echo "Parameter Sweep"
echo "============================================================"
echo "Temperature range: $TEMP_MIN to $TEMP_MAX (step: $TEMP_STEP)"
echo "Reasoning efforts: ${REASONING_EFFORTS[*]}"
echo "Iterations per config: $ITERATIONS"
if [ -n "$SEED" ]; then
    echo "Seed: $SEED"
fi
echo "Suite path: $SUITE_PATH"
echo "Raw results: $RAW_RESULTS_FILE"
echo "Summary: $SUMMARY_FILE"
echo "============================================================"
echo ""

# Generate temperature values using Python (cross-platform)
TEMPS=$(python -c "
import sys
start, end, step = float('$TEMP_MIN'), float('$TEMP_MAX'), float('$TEMP_STEP')
current = start
temps = []
while current <= end + 0.0001:  # small epsilon for float comparison
    temps.append(f'{current:.3f}')
    current += step
print(' '.join(temps))
")

# Convert to array
read -ra TEMP_ARRAY <<< "$TEMPS"

# Run sweep
total_configs=$((${#TEMP_ARRAY[@]} * ${#REASONING_EFFORTS[@]}))
total_runs=$((total_configs * ITERATIONS))
current_run=0
config_num=0

for temp in "${TEMP_ARRAY[@]}"; do
    for effort in "${REASONING_EFFORTS[@]}"; do
        config_num=$((config_num + 1))
        scores=()
        
        for iter in $(seq 1 $ITERATIONS); do
            current_run=$((current_run + 1))
            echo ""
            MODEL_DISPLAY="${MODEL:-recorded}"
            echo "[$current_run/$total_runs] Config $config_num: model=$MODEL_DISPLAY, temp=$temp, effort=$effort (iter $iter/$ITERATIONS)"
            echo "------------------------------------------------------------"
            
            # Build seed override if set
            SEED_OVERRIDE=""
            if [ -n "$SEED" ]; then
                SEED_OVERRIDE="--config-override seed=$SEED"
            fi
            
            # Build model override if set
            MODEL_OVERRIDE=""
            if [ -n "$MODEL" ]; then
                MODEL_OVERRIDE="--config-override model=$MODEL"
            fi
            
            # Run eval and capture output
            output=$(python -m evals.run_evals \
                --suite-path "$SUITE_PATH" \
                --config-override "temperature=$temp" \
                --config-override "reasoning_effort=$effort" \
                $SEED_OVERRIDE \
                $MODEL_OVERRIDE \
                2>&1)
            
            # Extract suite score from output
            suite_score=$(echo "$output" | grep -oP 'SUITE SCORE: \K[0-9.]+' || echo "")
            
            if [ -z "$suite_score" ]; then
                # Try alternative grep for systems without -P
                suite_score=$(echo "$output" | grep "SUITE SCORE:" | sed 's/.*SUITE SCORE: \([0-9.]*\).*/\1/')
            fi
            
            if [ -z "$suite_score" ]; then
                echo "  ERROR: Could not extract score"
                echo "$output"
                suite_score="ERROR"
            else
                echo "  Score: $suite_score"
                scores+=("$suite_score")
            fi
            
            # Append to raw results
            echo "$temp,$effort,${MODEL:-recorded},$iter,$suite_score" >> "$RAW_RESULTS_FILE"
        done
        
        # Calculate stats for this configuration using Python
        if [ ${#scores[@]} -gt 0 ]; then
            stats=$(python -c "
import statistics
scores = [float(x) for x in '${scores[*]}'.split()]
n = len(scores)
avg = statistics.mean(scores)
min_s = min(scores)
max_s = max(scores)
if n > 1:
    stdev = statistics.stdev(scores)
else:
    stdev = 0.0
print(f'{avg:.4f},{min_s:.4f},{max_s:.4f},{stdev:.4f}')
")
            echo "$temp,$effort,${MODEL:-recorded},$stats" >> "$SUMMARY_FILE"
            echo "  Config stats: avg=$(echo $stats | cut -d, -f1), min=$(echo $stats | cut -d, -f2), max=$(echo $stats | cut -d, -f3), stdev=$(echo $stats | cut -d, -f4)"
        else
            echo "$temp,$effort,ERROR,ERROR,ERROR,ERROR" >> "$SUMMARY_FILE"
        fi
    done
done

echo ""
echo "============================================================"
echo "SWEEP COMPLETE"
echo "============================================================"
echo ""
echo "Raw results saved to: $RAW_RESULTS_FILE"
echo "Summary saved to: $SUMMARY_FILE"
echo ""
echo "Summary (sorted by avg_score desc):"
echo "------------------------------------"
# Sort by avg_score (column 3) descending, skip header
{
    head -1 "$SUMMARY_FILE"
    tail -n +2 "$SUMMARY_FILE" | grep -v ERROR | sort -t, -k4 -rn
} | if command -v column &> /dev/null; then
    column -t -s,
else
    cat
fi
echo ""

# Find best configuration
best=$(tail -n +2 "$SUMMARY_FILE" | grep -v ERROR | sort -t, -k4 -rn | head -1)
if [ -n "$best" ]; then
    echo "Best configuration: $best"
else
    echo "No successful runs to determine best configuration"
fi
