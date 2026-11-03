# Package Structure

## Backend
- src/
  - agent.py
  - cli.py
  - config.py
  - permissions.py
  - provider.py
  - system_prompt.py
  - types.py
  - tools/
    - __init__.py
    - bash_tool.py
    - edit_file.py
    - glob_tool.py
    - grep_tool.py
    - read_file.py
    - registry.py
    - write_file.py
- tests/
  - test_tools.py
- pyproject.toml
- README.md
- .env
