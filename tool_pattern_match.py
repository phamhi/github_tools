#!/usr/bin/env python3

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Set, List

def read_patterns(pattern_file: Path) -> List[str]:
    """Read patterns from file into a list.
    
    Args:
        pattern_file (Path): Path to the file containing regex patterns, one per line
        
    Returns:
        List[str]: A list of regex patterns read from the file
        
    Raises:
        SystemExit: If the pattern file cannot be read or contains invalid regex
    """
    try:
        with open(pattern_file, 'r') as f:
            patterns = [line.strip() for line in f if line.strip()]
            # Validate all patterns are valid regex
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    logging.error(f"Invalid regular expression '{pattern}': {e}")
                    sys.exit(1)
            return patterns
    except IOError as e:
        logging.error(f"Failed to read pattern file: {e}")
        sys.exit(1)

def process_input(input_file: Path, patterns: List[str]) -> None:
    """Process input file and check each line against regex patterns.
    
    Args:
        input_file (Path): Path to the input file to process
        patterns (List[str]): List of regex patterns to match against
        
    Returns:
        None: Outputs matching lines to stdout
    """
    try:
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                matched = False
                for pattern in patterns:
                    if re.search(pattern, line):
                        matched = True
                        break
                if matched:
                    logging.debug(f"Match found: {line}")
                    print(line)
    except IOError as e:
        logging.error(f"Failed to read input file: {e}")
        sys.exit(1)

def main():
    """Main entry point of the script.
    
    Parses command line arguments, sets up logging, and orchestrates the
    pattern matching process.
    """
    parser = argparse.ArgumentParser(description='Pattern matching utility')
    parser.add_argument('-i', '--input', type=Path, required=True,
                      help='Input file path')
    parser.add_argument('-p', '--pattern', type=Path, required=True,
                      help='Pattern file path')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=log_level
    )

    logging.debug("Reading patterns...")
    patterns = read_patterns(args.pattern)
    logging.debug(f"Loaded patterns: {patterns}")

    logging.debug("Processing input file...")
    process_input(args.input, patterns)

if __name__ == "__main__":
    main()
