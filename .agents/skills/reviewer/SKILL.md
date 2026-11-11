---
name: reviewer
description: "Comprehensive code review skill for analyzing code quality, security, and best practices"
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  skill-author: User
  categories:
    - code-review
    - quality-assurance
    - security
---

# reviewer

## When to use

Use this skill when:
- Performing code reviews on pull requests or changesets
- Analyzing code for security vulnerabilities
- Checking adherence to coding standards and best practices
- Evaluating test coverage and quality
- Providing structured feedback on code changes

Trigger conditions:
- User requests a code review
- New code is submitted for review
- Security audit is needed
- Code quality assessment is required

## Workflow

1. **Understand Context**
   - Read the PR description or change summary
   - Identify the scope and purpose of changes
   - Check related issues or requirements

2. **Explore Codebase**
   - Use `glob` and `grep` to find relevant files
   - Read modified files to understand changes
   - Examine related files for context

3. **Analyze Changes**
   - Review diff for structural modifications
   - Check for correctness and logic errors
   - Identify security implications
   - Evaluate performance impact

4. **Verify Standards**
   - Check coding style and conventions
   - Verify naming consistency
   - Ensure proper error handling
   - Validate documentation updates

5. **Assess Tests**
   - Check if tests exist for new functionality
   - Verify test quality and coverage
   - Run tests if possible to confirm they pass

6. **Generate Review Report**
   - Structure findings by severity (Critical, Major, Minor, Nitpick)
   - Provide specific file/line references
   - Include actionable suggestions for each finding
   - Give overall assessment

## Tools required

- read_file: Read source code files
- glob: Find files by pattern
- grep: Search for patterns in code
- bash: Run tests, linters, or other verification commands
- edit_file: Suggest specific code changes (if authorized)
- write_file: Create review reports or test files

## Inputs/Outputs

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| target_path | string | Path to file or directory to review |
| review_type | string | Type of review: "full", "security", "performance", "style" |
| context | string | Additional context about the changes |

### Outputs
| Output | Type | Description |
|--------|------|-------------|
| review_report | string | Structured code review with findings |
| findings | list[object] | List of findings with severity, location, description |
| overall_assessment | string | "Approve", "Request Changes", or "Comment" |

## References

### Review Checklists

#### Security Checklist
- [ ] No hardcoded secrets, API keys, or passwords
- [ ] Input validation on all user inputs
- [ ] Proper authentication and authorization checks
- [ ] No SQL injection vulnerabilities (parameterized queries)
- [ ] No XSS vulnerabilities (proper output encoding)
- [ ] Secure defaults for configuration
- [ ] Proper error handling without information leakage
- [ ] Dependencies scanned for known vulnerabilities

#### Performance Checklist
- [ ] No N+1 query problems
- [ ] Efficient algorithms and data structures
- [ ] Proper caching where appropriate
- [ ] No unnecessary allocations in hot paths
- [ ] Database indexes for frequent queries
- [ ] Pagination for large result sets

#### Code Quality Checklist
- [ ] Clear, descriptive naming conventions
- [ ] Functions are small and focused (single responsibility)
- [ ] No code duplication (DRY principle)
- [ ] Proper error handling and logging
- [ ] Consistent code style and formatting
- [ ] Adequate comments for complex logic
- [ ] No dead code or commented-out code

#### Testing Checklist
- [ ] Unit tests for new functionality
- [ ] Edge cases covered (empty, null, boundary values)
- [ ] Integration tests for API endpoints
- [ ] Tests are deterministic and isolated
- [ ] Mock external dependencies appropriately
- [ ] Test coverage meets project standards

## Scripts

None required for this skill. The skill operates through the agent's tools.

## Assets

None required.