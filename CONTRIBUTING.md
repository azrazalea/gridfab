# Contributing to GridFab

Thank you for your interest in contributing to GridFab! This document outlines the process for contributing to the project and the expectations we have for all contributors.

## Code of Conduct

We have adopted the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md). Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating. By participating, you are expected to uphold this code.

## Licensing

GridFab is licensed under the [GNU Affero General Public License v3.0 (AGPLv3)](LICENSE.md).

**Important**: By submitting contributions to this project, you agree that your contributions will be licensed under the AGPLv3. Please make sure you have read and understood the license before contributing.

## How to Contribute

### Reporting Bugs

Before submitting a bug report:
- Check the issue tracker to see if the bug has already been reported
- Ensure you're using the latest version of the software
- Confirm it's actually a bug and not an intended behavior

When submitting a bug report, please include:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior vs. actual behavior
- Screenshots if applicable
- Your environment details (OS, Python version)
- Any additional context that might help

### Suggesting Features

Feature suggestions are welcome! When suggesting a feature:
- Provide a clear description of the feature
- Explain why this feature would be useful to the project
- Consider how it would impact the existing codebase
- Discuss possible implementations if you have ideas

### Pull Requests

1. **Fork the Repository**: Create your own fork of the project
2. **Create a Branch**: Create a branch for your feature or bugfix
3. **Make Changes**: Implement your changes, following the project's code style
4. **Write Tests**: Add tests for your changes if applicable
5. **Update CHANGELOG.md**: Add entries under `[Unreleased]` using [Keep a Changelog](https://keepachangelog.com/) categories
6. **Update INSTRUCTIONS.md**: If your change adds, removes, or modifies any user-facing behavior (commands, GUI features, file formats, config options), update INSTRUCTIONS.md to reflect it
7. **Documentation**: Update any other documentation to reflect your changes
8. **Submit PR**: Submit a pull request with a clear description of the changes

## Development Setup

```bash
git clone https://github.com/azrazalea/gridfab.git
cd gridfab
pip install -e ".[dev]"
python -m pytest
```

## Development Guidelines

### Code Style

- Follow the established code style in the project
- Use meaningful variable and function names
- Keep functions small and focused on a single responsibility
- Don't add docstrings, comments, or type annotations to code you didn't change

### Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers in commit messages when applicable
- Make small, focused commits rather than large, sweeping changes
- Update CHANGELOG.md with every commit
- Update INSTRUCTIONS.md when user-facing behavior changes

### Testing

- Write tests for new features and bug fixes
- Ensure all tests pass before submitting a pull request
- Don't break existing functionality

```bash
python -m pytest          # Run all tests
python -m pytest -v       # Verbose output
```

### Key Architecture Rules

- **Text-as-truth**: `grid.txt` IS the artwork. Never break backward compatibility with this format.
- **CLI-first**: Every editing operation must be available via CLI.
- **Minimal dependencies**: Python 3.10+ stdlib + Pillow only.

See [CLAUDE.md](CLAUDE.md) for the full development guide.

## Getting Help

If you need help or have questions:
- Check the documentation
- Look for similar issues in the issue tracker
- Email azrazalea@gmail.com

## Review Process

All submissions require review. We strive to review pull requests within 1 week when possible. During review, we may suggest changes or improvements before merging.

---

Thank you for contributing to GridFab! Your efforts help make this project better for everyone.
