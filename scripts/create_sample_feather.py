#!/usr/bin/env python3
"""
Script to create a sample feather file for testing the analyze_feather.py script.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def create_sample_feather():
    """Create a sample feather file with various data types for testing."""
    
    # Create sample data with different data types
    np.random.seed(42)  # For reproducible results
    
    data = {
        'index': range(1, 101),  # Index column as required
        'barcode_id': [f'BC_{i:04d}' for i in range(1, 101)],
        'sequence': [''.join(np.random.choice(['A', 'T', 'G', 'C'], size=8)) for _ in range(100)],
        'quality_score': np.random.uniform(20, 40, 100),
        'read_count': np.random.randint(100, 10000, 100),
        'is_valid': np.random.choice([True, False], 100, p=[0.8, 0.2]),
        'sample_type': np.random.choice(['DNA', 'RNA', 'Protein'], 100),
        'batch_id': np.random.choice(['B001', 'B002', 'B003'], 100),
        'processing_date': pd.date_range('2024-01-01', periods=100, freq='D')[:100],
        'concentration': np.random.lognormal(2, 1, 100)
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Add some null values to demonstrate null handling
    df.loc[5:9, 'quality_score'] = np.nan
    df.loc[15:17, 'concentration'] = np.nan
    
    # Create output directory if it doesn't exist
    output_dir = Path('data')
    output_dir.mkdir(exist_ok=True)
    
    # Save as feather file
    output_path = output_dir / 'sample_barcodes.feather'
    df.to_feather(output_path)
    
    print(f"Sample feather file created: {output_path}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    return output_path

if __name__ == "__main__":
    create_sample_feather()