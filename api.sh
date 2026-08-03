#!/bin/bash

# ClipGenesis API Server Startup Script

echo "🚀 Starting ClipGenesis API Server"

# Set up CUDA/cuDNN environment
source "$(dirname "$0")/setup_cuda_env.sh"

# Start the API server
python main.py 