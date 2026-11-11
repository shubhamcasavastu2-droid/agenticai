#!/usr/bin/env python3
"""
Document Generator Skill - Process markdown files in docs/ directory
"""

import os
from pathlib import Path
from typing import Dict, List, Any


def process_docs(docs_path: str = "docs", process_content: bool = True) -> Dict[str, Any]:
    """
    Check for docs folder, create if missing, and process all .md files.
    
    Args:
        docs_path: Path to the docs directory
        process_content: Whether to read and process file content
        
    Returns:
        Dictionary with processing results
    """
    docs_dir = Path(docs_path)
    created = False
    
    # Check if docs directory exists, create if not
    if not docs_dir.exists():
        docs_dir.mkdir(parents=True, exist_ok=True)
        created = True
        print(f"Created docs directory: {docs_path}")
    else:
        print(f"Docs directory already exists: {docs_path}")
    
    # Find all .md files in docs directory
    md_files = list(docs_dir.glob("*.md"))
    
    files_processed = []
    file_contents = {}
    
    for md_file in md_files:
        files_processed.append(str(md_file))
        if process_content:
            try:
                content = md_file.read_text(encoding='utf-8')
                file_contents[str(md_file)] = content
                print(f"Processed: {md_file}")
            except Exception as e:
                print(f"Error reading {md_file}: {e}")
                file_contents[str(md_file)] = f"Error: {e}"
    
    # Generate summary
    summary = f"Found {len(md_files)} markdown file(s) in {docs_path}"
    if created:
        summary += " (directory was created)"
    
    return {
        "docs_exists": True,
        "created": created,
        "files_processed": files_processed,
        "file_count": len(md_files),
        "summary": summary,
        "file_contents": file_contents if process_content else {}
    }


def main():
    """Main entry point for the script."""
    import sys
    
    # Allow custom docs path via command line argument
    docs_path = sys.argv[1] if len(sys.argv) > 1 else "docs"
    process_content = "--no-content" not in sys.argv
    
    result = process_docs(docs_path, process_content)
    
    print("\n" + "="*50)
    print("DOCUMENT GENERATOR RESULTS")
    print("="*50)
    print(f"Directory: {docs_path}")
    print(f"Created: {result['created']}")
    print(f"Files found: {result['file_count']}")
    print(f"Files processed: {result['files_processed']}")
    print(f"Summary: {result['summary']}")
    
    if result['file_contents']:
        print("\n--- File Contents ---")
        for filepath, content in result['file_contents'].items():
            print(f"\n[{filepath}]")
            print(content[:500] + ("..." if len(content) > 500 else ""))


if __name__ == "__main__":
    main()