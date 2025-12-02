#!/usr/bin/env python3
"""
Script to update error codes to single letter format (X##.###)
and convert ValueError/RuntimeError to proper exceptions
"""
import re
import os

# Error code mapping: old -> new (single letter format)
ERROR_CODE_MAPPING = {
    # Application base errors
    "APP00": "A00",
    
    # Domain errors  
    "DOM00": "D00",
    
    # Data/Element errors
    "DAT10": "E00",
    "E100": "E00",
    "L1201": "E00.001",
    "L1202": "E00.002", 
    "L1203": "E00.003",
    "L1204": "E00.004",
    "L1205": "E00.005",
    "L1206": "E00.006",
    "L1207": "E00.007",
    
    # Form errors
    "FRM00": "F00",
    "D100-001": "F00.001",
    "D100-002": "F00.002",
    
    # Query errors
    "Q01-00383": "Q00.001",
    "Q01-49939": "Q00.002", 
    "Q01-3939": "Q00.003",
    "Q100-502": "Q00.502",
    "Q101-503": "Q00.503",
    "Q102-501": "Q00.501",
    "Q4031212": "Q00.004",
    "Q4031213": "Q00.005",
    "Q4031215": "Q00.006",
    "Q4031216": "Q00.007",
    
    # Navis/Workflow errors
    "P010.01": "P00.001",
    "P010.02": "P00.002",
    "P010.03": "P00.003",
    "P010.05": "P00.005",
    "P010.07": "P00.007",
    "P010.08": "P00.008",
    "P010.09": "P00.009",
    "P01005": "P00.005",
    "P01010": "P00.010",
    "P01016": "P00.016",
    "P011.01": "P00.011",
    "P011.02": "P00.012",
    "P011.03": "P00.013",
    "P011.04": "P00.014",
    "P011.05": "P00.015",
    "P01107": "P00.017",
    "P012.01": "P00.021",
    "P01301": "P00.031",
    "P01302": "P00.032",
    "P018.81": "P00.081",
    "P018.82": "P00.082",
    "P018.83": "P00.083",
    "P102.01": "P00.101",
    "P102.02": "P00.102",
    
    # Other mappings
    "D10011": "D00.011",
    "D10012": "D00.012",
    "E412.49": "D00.201",
    "403648": "D00.301",
    "412649": "D00.201",
}

def update_error_code(match):
    """Replace error code in string"""
    code = match.group(1)
    if code in ERROR_CODE_MAPPING:
        return f'"{ERROR_CODE_MAPPING[code]}"'
    # Try partial match for codes like "D100-501"
    for old, new in ERROR_CODE_MAPPING.items():
        if code.startswith(old) or old in code:
            return f'"{code.replace(old, new)}"'
    return match.group(0)

if __name__ == "__main__":
    print("Error code update script")
    print("Run this manually to update remaining error codes")

