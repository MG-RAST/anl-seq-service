#!/usr/bin/env python3
"""
Script to work with feather file index values.

Usage:
    python analyze_feather.py <feather_file_path> --list-index
    python analyze_feather.py <feather_file_path> --check-value <value>

This script provides two main functions:
- List all index values
- Check if a specific value exists in the index
"""

import sys
import pandas as pd
import argparse
from pathlib import Path


def list_index_values(file_path):
    """
    List all index values from a feather file.
    
    Args:
        file_path (str): Path to the feather file
    
    Returns:
        list: List of all index values
    """
    try:
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' not found.")
            return None
            
        # Read the feather file and set index
        df = pd.read_feather(file_path).set_index('index')
        
        # Get all index values
        index_values = df.index.tolist()
        
        print(f"Index values from: {file_path}")
        print(f"Total count: {len(index_values)}")
        print("-" * 40)
        
        for i, value in enumerate(index_values, 1):
            print(f"{i:4d}. {value}")
        
        return index_values
        
    except KeyError:
        print("Error: No 'index' column found in the feather file.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def check_value_in_index(file_path, value):
    """
    Check if a specific value exists in the index.
    
    Args:
        file_path (str): Path to the feather file
        value: Value to check for in the index
    
    Returns:
        bool: True if value exists in index, False otherwise
    """
    try:
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' not found.")
            return False
            
        # Read the feather file and set index
        df = pd.read_feather(file_path).set_index('index')
        
        # Check if value exists in index
        exists = value in df.index
        
        print(f"Checking for value '{value}' in index of: {file_path}")
        print(f"Result: {'FOUND' if exists else 'NOT FOUND'}")
        
        return exists
        
    except KeyError:
        print("Error: No 'index' column found in the feather file.")
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False


def search_partial_matches(file_path, search_term):
    """
    Search for index values that contain the search term as a substring.
    
    Args:
        file_path (str): Path to the feather file
        search_term (str): Term to search for within index values
    
    Returns:
        list: List of index values that contain the search term
    """
    try:
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' not found.")
            return None
            
        # Read the feather file and set index
        df = pd.read_feather(file_path).set_index('index')
        
        # Convert index to string for searching
        index_strings = df.index.astype(str)
        
        # Find matches that contain the search term
        matches = [idx for idx in index_strings if search_term in str(idx)]
        
        print(f"Searching for '{search_term}' in index values of: {file_path}")
        print(f"Found {len(matches)} matches:")
        print("-" * 40)
        
        if matches:
            for i, match in enumerate(matches, 1):
                print(f"{i:4d}. {match}")
        else:
            print("No matches found.")
        
        return matches
        
    except KeyError:
        print("Error: No 'index' column found in the feather file.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Work with feather file index values.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python analyze_feather.py data/file.feather --list-index
    python analyze_feather.py data/file.feather --check-value "some_value"
    python analyze_feather.py data/file.feather --search-partial "1.8.1"
        """
    )
    
    parser.add_argument(
        'file_path',
        help='Path to the feather file'
    )
    
    parser.add_argument(
        '--list-index',
        action='store_true',
        help='List all index values'
    )
    
    parser.add_argument(
        '--check-value',
        help='Check if a specific value exists in the index'
    )
    
    parser.add_argument(
        '--search-partial',
        help='Search for index values that contain the specified substring'
    )
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Ensure at least one operation is specified
    if not args.list_index and args.check_value is None and args.search_partial is None:
        print("Error: Please specify one of --list-index, --check-value, or --search-partial")
        parser.print_help()
        sys.exit(1)
    
    # List index values
    if args.list_index:
        index_values = list_index_values(args.file_path)
        sys.exit(0 if index_values is not None else 1)
    
    # Check for specific value
    if args.check_value is not None:
        exists = check_value_in_index(args.file_path, args.check_value)
        sys.exit(0 if exists else 1)
    
    # Search for partial matches
    if args.search_partial is not None:
        matches = search_partial_matches(args.file_path, args.search_partial)
        sys.exit(0 if matches is not None else 1)


if __name__ == "__main__":
    main()