# Pull Requests

How to submit changes to Sutras.

## Process

1. **Fork** the repository
2. **Create branch** from `main`
3. **Make changes** following style guidelines
4. **Add tests** for new features
5. **Run checks** with `just pre-commit`
6. **Update docs** if needed
7. **Submit PR** with clear description

## PR Checklist

Before submitting, ensure:

- [ ] Tests pass (`just test`)
- [ ] Code formatted (`just format`)
- [ ] Linting passes (`just lint`)
- [ ] Type checking passes (`just check`)
- [ ] Documentation updated (if applicable)
- [ ] Changelog entry added (if applicable)

## Branch Naming

Use descriptive branch names:

```
feat/add-registry-support
fix/version-parsing-bug
docs/update-cli-reference
```

## PR Description

Include:

- **What** the change does
- **Why** it's needed
- **How** it works (if complex)
- **Testing** done

### Example

```markdown
## Summary

Add support for installing skills from GitHub releases.

## Changes

- New `github:` source format for install command
- Fetch release assets via GitHub API
- Extract and install skill packages

## Testing

- Added tests for GitHub URL parsing
- Added integration test with mock GitHub API
- Tested manually with real GitHub releases
```

## Review Process

1. Maintainers review code and tests
2. Address feedback with new commits
3. Once approved, PR is merged
4. Branch is deleted after merge

## After Merge

- Delete your feature branch
- Pull latest `main` to stay updated
- Celebrate your contribution!
