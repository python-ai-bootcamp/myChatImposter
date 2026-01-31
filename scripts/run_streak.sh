temperature=$1

streak=0; while :; do bla=$(PYTHONIOENCODING=utf-8 python -m evals.run_evals --suite-path ./log/llm_recordings/yahav/periodic_group_tracking/ --config-override temperature=${temperature} --config-override model=gpt-5-mini --debug 2>&1); score=$(echo "$bla" | awk '/SUITE SCORE:/ {print $3; found=1} END {if(!found) exit 1}'); echo "streak=$streak score=$score"; [ "$score" != "1.00" ] && { echo "$bla"; echo "final_streak=$streak"; break; }; streak=$((streak+1)); done
