#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting TraceFox Backend Development Server...${NC}"

# Navigate to project root
cd "$PROJECT_ROOT"

# Check for virtual environment
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ Activating 'venv' virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}✓ Activating '.venv' virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  No virtual environment found (checked 'venv' and '.venv').${NC}"
    echo -e "${YELLOW}   Running with system python. Use 'python3 -m venv venv' to create one if needed.${NC}"
fi

# Check if dependencies are installed (simple check)
if python3 -c "import fastapi" &> /dev/null; then
    echo -e "${GREEN}✓ FastAPI detected.${NC}"
else
    echo -e "${YELLOW}⚠️  FastAPI not found. Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
fi

# Add project root to PYTHONPATH to ensure service imports work
export PYTHONPATH=$PROJECT_ROOT:$PYTHONPATH

# Run Uvicorn
echo -e "${BLUE}📡 Starting Uvicorn on http://0.0.0.0:8000...${NC}"
uvicorn services.api_gateway.main:app --reload --host 0.0.0.0 --port 8000
