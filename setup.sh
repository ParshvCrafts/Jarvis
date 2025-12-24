#!/bin/bash
# JARVIS One-Command Setup Script (Unix/macOS/Linux)
# Usage: ./setup.sh
# Or with options: ./setup.sh --tier core --skip-venv

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() { echo -e "\n${CYAN}============================================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}============================================================${NC}\n"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_err() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "  $1"; }

# Defaults
SKIP_VENV=false
TIER="full"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-venv) SKIP_VENV=true; shift ;;
        --tier) TIER="$2"; shift 2 ;;
        --help|-h)
            echo "JARVIS Setup Script"
            echo ""
            echo "Usage: ./setup.sh [options]"
            echo ""
            echo "Options:"
            echo "  --skip-venv    Skip virtual environment creation"
            echo "  --tier TIER    Requirements tier: minimal, core, full, dev (default: full)"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./setup.sh                    # Full setup with venv"
            echo "  ./setup.sh --tier core        # Core features only"
            echo "  ./setup.sh --skip-venv        # Use existing Python environment"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

print_header "JARVIS Setup Script"
echo "Setting up JARVIS - Your Personal AI Assistant"

# Check Python
print_header "Checking Python"
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    print_err "Python not found. Please install Python 3.10+"
    exit 1
fi

VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR=$($PYTHON -c 'import sys; print(sys.version_info.major)')
MINOR=$($PYTHON -c 'import sys; print(sys.version_info.minor)')

if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
    print_success "Python $VERSION detected"
else
    print_err "Python 3.10+ required, found $VERSION"
    exit 1
fi

# Create virtual environment
if [ "$SKIP_VENV" = false ]; then
    print_header "Creating Virtual Environment"
    
    if [ -d "venv" ]; then
        print_warn "Virtual environment already exists"
        read -p "Recreate? (y/N) " response
        if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
            rm -rf venv
            $PYTHON -m venv venv
            print_success "Virtual environment recreated"
        else
            print_info "Using existing virtual environment"
        fi
    else
        $PYTHON -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate venv
    print_info "Activating virtual environment..."
    source venv/bin/activate
fi

# Upgrade pip
print_header "Upgrading pip"
pip install --upgrade pip --quiet
print_success "pip upgraded"

# Install requirements
print_header "Installing Dependencies ($TIER tier)"

REQ_FILE="requirements.txt"
if [ "$TIER" != "full" ]; then
    REQ_FILE="requirements-$TIER.txt"
fi

if [ -f "$REQ_FILE" ]; then
    print_info "Installing from $REQ_FILE..."
    pip install -r "$REQ_FILE" --quiet
    print_success "Dependencies installed"
else
    print_err "Requirements file not found: $REQ_FILE"
    exit 1
fi

# Verify critical dependencies
print_header "Verifying Dependencies"
CRITICAL_PACKAGES="loguru pydantic dotenv yaml"
MISSING=0

for pkg in $CRITICAL_PACKAGES; do
    # Handle package name differences
    import_name=$pkg
    if [ "$pkg" = "dotenv" ]; then
        import_name="dotenv"
    fi
    
    if $PYTHON -c "import $import_name" 2>/dev/null; then
        print_success "$pkg installed"
    else
        print_err "$pkg missing"
        MISSING=1
    fi
done

if [ $MISSING -eq 1 ]; then
    print_err "Some critical packages are missing. Please check installation."
    exit 1
fi

# Create directories
print_header "Creating Directories"
for dir in data data/screenshots data/browser_data logs cache; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Created $dir/"
    else
        print_info "$dir/ already exists"
    fi
done

# Create config from example if needed
print_header "Setting Up Configuration"
if [ ! -f "config/settings.yaml" ]; then
    if [ -f "config/settings.yaml.example" ]; then
        cp config/settings.yaml.example config/settings.yaml
        print_success "Created config/settings.yaml from example"
    else
        print_warn "No settings.yaml.example found"
    fi
else
    print_info "config/settings.yaml already exists"
fi

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env from example"
        print_warn "Please edit .env and add your API keys!"
    else
        print_warn "No .env.example found"
    fi
else
    print_info ".env already exists"
fi

# Run first-time setup
print_header "Running First-Time Setup"
$PYTHON -c "from src.core.setup_wizard import run_first_time_setup; run_first_time_setup()" 2>/dev/null || print_info "First-time setup will run on first JARVIS start"

# Validate installation
print_header "Validating Installation"
$PYTHON run.py --check-config

print_header "Setup Complete!"
cat << 'EOF'
JARVIS is ready to use!

Next steps:
1. Edit .env and add your API keys:
   - GROQ_API_KEY (required for LLM)
   - Other optional keys

2. Start JARVIS:
   ./start.sh            # Full voice mode
   ./start-text.sh       # Text-only mode
   python run.py         # Direct run

3. Say "Hey Jarvis" to wake up!

For help: python run.py --help
EOF
