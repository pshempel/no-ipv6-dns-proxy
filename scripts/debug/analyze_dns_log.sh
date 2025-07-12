#!/bin/bash
# Analyze DNS log for errors

LOG_FILE="/tmp/dns.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    echo "Run the server first with: priv_tools/project_run.sh python test_with_log.py"
    exit 1
fi

echo "DNS Log Analysis"
echo "================"
echo ""

echo "1. Error Summary:"
echo "-----------------"
grep -i "error\|exception\|traceback\|servfail" "$LOG_FILE" | tail -20

echo ""
echo "2. Netflix Query Details:"
echo "------------------------"
grep -B5 -A20 "logs\.netflix" "$LOG_FILE" | tail -50

echo ""
echo "3. CNAME Flattening Events:"
echo "---------------------------"
grep -i "flatten\|cname" "$LOG_FILE" | grep -i "netflix" | tail -20

echo ""
echo "4. Last 30 lines of log:"
echo "------------------------"
tail -30 "$LOG_FILE"