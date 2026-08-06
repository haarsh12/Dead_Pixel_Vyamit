#!/bin/bash
# Bash Test Runner for Linux/Mac
# Runs all backend tests

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}MyKirana Backend Test Suite${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${BLUE}[INFO] Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}[WARNING] Virtual environment not found${NC}"
    echo -e "${YELLOW}[INFO] Using system Python${NC}"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}[ERROR] .env file not found!${NC}"
    echo -e "${YELLOW}[INFO] Copy .env.example to .env and configure${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO] Environment file found${NC}"

# Run tests
echo ""
echo -e "${BLUE}Running all tests...${NC}"
echo ""

python test_all.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Some tests failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
