---
name: document-generator
description: "Skill for generating and processing documentation files in the docs/ directory"
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  skill-author: User
  categories:
    - documentation
    - file-processing
---

# document-generator

## When to use

Use this skill when:
- You need to ensure the docs/ directory exists
- You need to process all .md files in the docs/ directory
- You want to generate documentation reports or summaries

Trigger conditions:
- User requests documentation processing
- New .md files are added to docs/
- Documentation generation is needed

## Workflow

1. **Check docs directory**
   - Verify if docs/ directory exists
   - Create docs/ directory if missing

2. **Process markdown files**
   - Find all .md files in docs/ directory
   - Read and process each file
   - Generate summary or report

3. **Output results**
   - Return list of processed files
   - Provide summary of content

## Tools required

- read_file: Read markdown files
- glob: Find .md files in docs/
- bash: Create directory if needed
- write_file: Write processing results

## Inputs/Outputs

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| docs_path | string | Path to docs directory (default: "docs") |
| process_content | boolean | Whether to process file content (default: true) |

### Outputs
| Output | Type | Description |
|--------|------|-------------|
| docs_exists | boolean | Whether docs directory exists |
| created | boolean | Whether docs directory was created |
| files_processed | list[string] | List of processed .md files |
| file_count | integer | Number of .md files found |
| summary | string | Summary of processing results |

## Scripts

- process_docs.py: Main script for processing documentation

## Assets

None required.