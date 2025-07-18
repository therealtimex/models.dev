#!/usr/bin/env python3
import tomllib
import redis
import json
import os
import glob
from pathlib import Path

def main():
    # Connect to Redis
    r = redis.Redis(
        host=os.environ.get('REALTIMEX_AI_LLM_REDIS_HOST', 'rta.rtworkspace.com'),
        password=os.environ.get('REALTIMEX_AI_LLM_REDIS_PASSWORD', ''),
        port=int(os.environ.get('REALTIMEX_AI_LLM_REDIS_PORT', 6379)),
        db=int(os.environ.get('REALTIMEX_AI_LLM_REDIS_DB', 0))
    )
    
    # Find all provider directories
    provider_dirs = glob.glob('providers/*/')
    
    for provider_dir in provider_dirs:
        provider_path = os.path.join(provider_dir, 'provider.toml')
        provider_name = os.path.basename(os.path.dirname(provider_dir))
        
        # Skip if provider.toml doesn't exist
        if not os.path.exists(provider_path):
            continue
            
        # Process provider.toml
        try:
            with open(provider_path, 'rb') as f:
                provider_data = tomllib.load(f)
                
            # Store provider data
            # r.set(f"provider:{provider_name}", json.dumps(provider_data))
            # print(f"Stored provider data for {provider_name}")
            
            # Find all model files for this provider
            model_files = glob.glob(os.path.join(provider_dir, 'models/**/*.toml'), recursive=True)
            
            for model_file in model_files:
                # Parse path to extract model group and name
                rel_path = os.path.relpath(model_file, os.path.join(provider_dir, 'models'))
                path_parts = Path(rel_path).parts
                
                if len(path_parts) > 1:
                    model_group_name = path_parts[0]
                    model_name = Path(path_parts[-1]).stem
                else:
                    model_group_name = "default"
                    model_name = Path(path_parts[0]).stem
                
                # Process model file
                try:
                    with open(model_file, 'rb') as f:
                        model_data = tomllib.load(f)
                    
                    # Store model data
                    key = f"model:ratio:{provider_name}:{model_group_name}:{model_name}"
                    r.set(key, json.dumps(model_data))
                    print(f"Stored model data for {key}")
                    
                except Exception as e:
                    print(f"Error processing model file {model_file}: {e}")
                    
        except Exception as e:
            print(f"Error processing provider {provider_name}: {e}")

if __name__ == "__main__":
    main()