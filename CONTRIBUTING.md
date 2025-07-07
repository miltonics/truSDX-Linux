# Contributing to TruSDX Linux Driver

Thank you for your interest in contributing to the TruSDX Linux Driver project! This project aims to provide seamless integration between TruSDX radios and JS8Call on Linux systems.

## How to Contribute

### Reporting Issues

- **Check existing issues** first to avoid duplicates
- **Provide detailed information** including:
  - Your Linux distribution and version
  - Python version
  - TruSDX firmware version
  - JS8Call version
  - Complete error messages and logs
  - Steps to reproduce the issue

### Suggesting Features

- Open an issue with the "enhancement" label
- Describe the feature and its benefits
- Explain how it would work with existing functionality
- Consider backward compatibility

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the coding guidelines below
4. **Test thoroughly** - ensure existing functionality still works
5. **Commit with clear messages**:
   ```bash
   git commit -m "Add feature: brief description
   
   Longer explanation of what the change does and why"
   ```
6. **Push to your fork** and create a pull request

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/trusdx-linux-driver.git
   cd trusdx-linux-driver
   ```

2. Install dependencies:
   ```bash
   ./setup.sh
   ```

3. Make your changes and test with:
   ```bash
   python3 trusdx-txrx-AI.py
   ```

## Coding Guidelines

### Python Style
- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings for functions and classes
- Keep functions focused and reasonably sized

### Error Handling
- Use try/except blocks for operations that can fail
- Log errors with appropriate detail level
- Fail gracefully with helpful error messages
- Don't suppress exceptions without good reason

### Testing
- Test with actual hardware when possible
- Verify backward compatibility
- Test edge cases and error conditions
- Document any new testing procedures

### Documentation
- Update README.md if you change functionality
- Update USAGE.md for user-visible changes
- Comment complex code sections
- Keep commit messages clear and descriptive

## Code Review Process

1. **Automated checks** - ensure your code passes any automated tests
2. **Maintainer review** - a maintainer will review your code
3. **Community feedback** - other users may provide input
4. **Integration** - approved changes are merged into main branch

## Communication

- **GitHub Issues** - for bug reports and feature requests
- **Pull Request comments** - for code-specific discussions
- **Commit messages** - for explaining changes

## Amateur Radio Spirit

This project is developed in the spirit of amateur radio - experimentation, learning, and helping fellow hams. Please:

- Be respectful and constructive in discussions
- Share knowledge and help others learn
- Consider the needs of the broader amateur radio community
- Remember that this is volunteer work done for the love of the hobby

## Recognition

Contributors will be acknowledged in the project documentation. Significant contributions may be highlighted in release notes.

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the "question" label
- Reach out through the project's communication channels

Thank you for helping make amateur radio more accessible on Linux!

**73 de Milton**
