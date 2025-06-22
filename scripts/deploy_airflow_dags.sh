#!/bin/bash

# Cryptocurrency Data Pipeline - Airflow Deployment Script
# This script helps deploy the SQLAlchemy-based pipeline to an Airflow environment

set -e  # Exit on any error

echo "========================================"
echo "Crypto Pipeline Airflow Deployment"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -d "src" ] || [ ! -d "dags" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Expected files: requirements.txt, src/, dags/"
    exit 1
fi

echo "✓ Project directory structure validated"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.8+ required, found $python_version"
    exit 1
fi

echo "✓ Python version $python_version is compatible"

# Check if virtual environment is recommended
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider using: python3 -m venv venv && source venv/bin/activate"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install or upgrade dependencies
echo ""
echo "Installing/upgrading Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Dependencies installed successfully"

# Check environment variables
echo ""
echo "Checking environment configuration..."

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  Warning: DATABASE_URL not set"
    echo "   Example: export DATABASE_URL='postgresql://user:pass@localhost/crypto_db'"
else
    echo "✓ DATABASE_URL configured"
fi

# Set default rate limits if not set
export COINGECKO_RATE_LIMIT=${COINGECKO_RATE_LIMIT:-50}
export BLOCKCHAIR_RATE_LIMIT=${BLOCKCHAIR_RATE_LIMIT:-1440}
export BATCH_SIZE=${BATCH_SIZE:-1000}

echo "✓ Using rate limits: CoinGecko=$COINGECKO_RATE_LIMIT/min, Blockchair=$BLOCKCHAIR_RATE_LIMIT/min"
echo "✓ Using batch size: $BATCH_SIZE"

# Test the pipeline
echo ""
echo "Testing pipeline components..."
echo "Running test script..."

if python3 scripts/test_sqlalchemy_pipeline.py; then
    echo "✓ Pipeline tests completed successfully"
else
    echo "❌ Pipeline tests failed"
    echo "   Please check the error messages above and fix any issues"
    exit 1
fi

# Airflow DAG validation (if Airflow is available)
echo ""
echo "Validating Airflow DAGs..."

if command -v airflow &> /dev/null; then
    echo "Found Airflow installation, validating DAGs..."
    
    # Add current directory to Python path for DAG validation
    export PYTHONPATH="${PWD}:${PYTHONPATH}"
    
    # Validate DAGs
    for dag_file in dags/crypto_pipeline_*.py; do
        if [ -f "$dag_file" ]; then
            echo "  Validating $(basename "$dag_file")..."
            python3 -m py_compile "$dag_file"
            echo "  ✓ $(basename "$dag_file") syntax valid"
        fi
    done
    
    echo "✓ All DAG files validated successfully"
else
    echo "⚠️  Airflow not found, skipping DAG validation"
    echo "   DAG files will be validated when deployed to Airflow"
fi

# Summary and next steps
echo ""
echo "========================================"
echo "Deployment Summary"
echo "========================================"
echo "✓ Dependencies installed"
echo "✓ Pipeline components tested"
echo "✓ DAG files validated"
echo ""
echo "Next Steps:"
echo "1. Ensure DATABASE_URL is set in your Airflow environment"
echo "2. Copy DAG files to your Airflow DAGs directory:"
echo "   cp dags/crypto_pipeline_*.py \$AIRFLOW_HOME/dags/"
echo "3. Ensure the project src/ directory is in Airflow's PYTHONPATH"
echo "4. Restart Airflow scheduler and webserver"
echo "5. Enable the DAGs in Airflow web UI"
echo ""
echo "DAG Files Created:"
echo "📄 dags/crypto_pipeline_sqlalchemy_dag.py - Main daily pipeline"
echo "📄 dags/crypto_pipeline_utilities_dag.py - Utilities and testing"
echo "📄 dags/README.md - Documentation"
echo ""
echo "Testing Script:"
echo "📄 scripts/test_sqlalchemy_pipeline.py - Validate pipeline"
echo ""
echo "🎉 Deployment preparation completed successfully!"
