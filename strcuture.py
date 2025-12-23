#!/usr/bin/env python3
import os

def print_directory_tree(startpath, exclude_dirs={'venv', 'node_modules', '__pycache__', '.git', '.next', 'build', 'dist', 'data/'}):
    print("📁 Project Directory Structure")
    print("=" * 50)
    
    for root, dirs, files in os.walk(startpath):
        # Remove excluded directories from dirs list (modifies in-place)
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')

if __name__ == "__main__":
    print_directory_tree('.')