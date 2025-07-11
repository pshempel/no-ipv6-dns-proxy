#!/bin/bash
# test_server.sh - Shell wrapper for DNS proxy testing
# Handles conda environment activation if needed

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}DNS Proxy Test Runner${NC}"
echo "====================="

# Check if we should use conda environment
if [ -f "priv_tools/project_run.sh" ]; then
    echo -e "${YELLOW}Using conda environment via project_run.sh${NC}"
    RUNNER="priv_tools/project_run.sh python"
else
    echo "Using system Python"
    RUNNER="python3"
fi

# Default test configuration
DEFAULT_CONFIG="/tmp/dns-proxy-test.cfg"

# Parse command line options
CONFIG_FILE="$DEFAULT_CONFIG"
LOG_LEVEL="INFO"
RUN_TESTS=false
CREATE_ONLY=false
CUSTOM_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --run-tests)
            RUN_TESTS=true
            shift
            ;;
        --create-config-only)
            CREATE_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -c, --config FILE      Use custom config file (default: $DEFAULT_CONFIG)"
            echo "  -l, --log-level LEVEL  Set log level (DEBUG, INFO, WARNING, ERROR)"
            echo "  --run-tests            Run DNS query tests after starting"
            echo "  --create-config-only   Only create config file and exit"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Run with default config on port 15353"
            echo "  $0"
            echo ""
            echo "  # Run with debug logging and tests"
            echo "  $0 -l DEBUG --run-tests"
            echo ""
            echo "  # Use custom config"
            echo "  $0 -c ~/my-dns-test.cfg"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check for required dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"

# Check Python
if ! $RUNNER -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    echo -e "${RED}Error: Python 3.9+ is required${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 3.9+"

# Check Twisted
if ! $RUNNER -c "import twisted" 2>/dev/null; then
    echo -e "${RED}Error: Twisted not found. Run: pip install -r requirements.txt${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Twisted"

# Check dig for testing
if command -v dig &> /dev/null; then
    echo -e "${GREEN}✓${NC} dig (for testing)"
else
    echo -e "${YELLOW}⚠${NC}  dig not found (install bind9-utils for testing)"
fi

# Build command
CMD="$RUNNER test_server.py -c $CONFIG_FILE -l $LOG_LEVEL"

if [ "$RUN_TESTS" = true ]; then
    CMD="$CMD --run-tests"
fi

if [ "$CREATE_ONLY" = true ]; then
    CMD="$CMD --create-config-only"
fi

# Create config directory if needed
CONFIG_DIR=$(dirname "$CONFIG_FILE")
if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

echo -e "\n${YELLOW}Starting DNS proxy test server...${NC}"
echo "Command: $CMD"
echo ""

# Run the server
exec $CMD