#!/usr/bin/env python3
import tomllib
import redis
import json
import os
import glob
import sys
from pathlib import Path

def process_model_file(r, model_file):
    """Process a single model TOML file and update Redis"""
    # Determine provider from path
    path_parts = Path(model_file).parts
    if 'providers' not in path_parts or 'models' not in path_parts:
        print(f"Skipping {model_file}: Not a valid model path")
        return False
    
    # Extract provider name from path
    provider_idx = path_parts.index('providers')
    provider_name = path_parts[provider_idx + 1]
    
    # Find the 'models' part in the path
    models_idx = path_parts.index('models')
    
    # Extract model group and name
    if len(path_parts) > models_idx + 2:
        model_group_name = path_parts[models_idx + 1]
        model_name = Path(path_parts[-1]).stem
    else:
        model_group_name = "default"
        model_name = Path(path_parts[-1]).stem
    
    try:
        with open(model_file, 'rb') as f:
            model_data = tomllib.load(f)
        
        # Store model data
        key = f"model:ratio:{provider_name}:{model_group_name}:{model_name}"
        r.set(key, json.dumps(model_data))
        print(f"Stored model data for {key}")
        return True
    except Exception as e:
        print(f"Error processing model file {model_file}: {e}")
        return False


def main():
    # Connect to Redis
    r = redis.Redis(
        host=os.environ.get('REALTIMEX_AI_LLM_REDIS_HOST', 'rta.rtworkspace.com'),
        password=os.environ.get('REALTIMEX_AI_LLM_REDIS_PASSWORD', ''),
        port=int(os.environ.get('REALTIMEX_AI_LLM_REDIS_PORT', 6379)),
        db=int(os.environ.get('REALTIMEX_AI_LLM_REDIS_DB', 0))
    )
    
    # Get changed files from environment variable
    changed_files = os.environ.get('CHANGED_FILES', '').strip()
    
    if changed_files:
        # Process only changed files
        files_to_process = changed_files.split()
        print(f"Processing {len(files_to_process)} changed TOML files")
    else:
        # Fallback to processing all files
        print("No changed files specified, processing all TOML files")
        provider_files = glob.glob('providers/*/provider.toml')
        model_files = glob.glob('providers/*/models/**/*.toml', recursive=True)
        files_to_process = provider_files + model_files
    
    success_count = 0
    for file_path in files_to_process:
        if not file_path.endswith('.toml'):
            continue
            
        if '/models/' in file_path:
            if process_model_file(r, file_path):
                success_count += 1

    
    print(f"Successfully processed {success_count} out of {len(files_to_process)} TOML files")

if __name__ == "__main__":
    main()