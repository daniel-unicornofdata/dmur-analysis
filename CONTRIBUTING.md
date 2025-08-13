# Contributing to DMUR Analysis Toolkit

Thank you for your interest in contributing to the DMUR Analysis Toolkit! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Virtual environment tool (venv, conda, or similar)

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/dmur-analysis.git
   cd dmur-analysis
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify installation**:
   ```bash
   pytest tests/
   ```

## Development Workflow

### Branch Management

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: Individual feature branches
- **hotfix/***: Critical bug fixes

### Making Changes

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following code style guidelines

3. **Run tests**:
   ```bash
   pytest tests/
   ```

4. **Check code quality**:
   ```bash
   black src/ tests/
   isort src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: descriptive commit message"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python Style

- **Formatter**: Use `black` for code formatting
- **Import sorting**: Use `isort` for import organization
- **Line length**: 100 characters maximum
- **Type hints**: Required for all public functions
- **Docstrings**: Google-style docstrings for all modules, classes, and functions

### Example Function

```python
def calculate_density(coordinates: np.ndarray, bandwidth: float = 0.002) -> np.ndarray:
    """
    Calculate business density using kernel density estimation.
    
    Args:
        coordinates: Array of (lat, lon) coordinates
        bandwidth: KDE bandwidth parameter
        
    Returns:
        Density values at grid points
        
    Raises:
        ValueError: If coordinates array is empty
    """
    if len(coordinates) == 0:
        raise ValueError("Coordinates array cannot be empty")
    
    # Implementation here
    return density_values
```

### Testing Guidelines

- **Coverage**: Maintain >80% test coverage
- **Test types**: Unit tests for all core functions
- **Fixtures**: Use pytest fixtures for test data
- **Mocking**: Mock external APIs and file I/O

### Documentation

- **Docstrings**: All public APIs must have comprehensive docstrings
- **README updates**: Update README for new features
- **Examples**: Provide usage examples for new functionality

## Contribution Types

### Bug Reports

When reporting bugs, please include:

- **Environment**: Python version, OS, package versions
- **Steps to reproduce**: Minimal code example
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full traceback if applicable

### Feature Requests

For new features, please provide:

- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Other solutions you've considered
- **Implementation ideas**: If you have technical suggestions

### Code Contributions

#### Areas for Contribution

1. **Algorithm improvements**:
   - Better boundary detection methods
   - Enhanced DMUR scoring components
   - Performance optimizations

2. **Data sources**:
   - Additional business data providers
   - Real estate data integrations
   - Demographic data sources

3. **Visualizations**:
   - New chart types
   - Interactive dashboard components
   - 3D visualizations

4. **Documentation**:
   - Tutorial improvements
   - API documentation
   - Usage examples

#### Technical Requirements

- **Backward compatibility**: Don't break existing APIs
- **Performance**: New features shouldn't significantly slow down analysis
- **Testing**: All new code must include tests
- **Documentation**: Update relevant documentation

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/dmur_analysis

# Run specific test file
pytest tests/unit/test_downtown_analyzer.py

# Run with specific markers
pytest -m "not integration"
```

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_business_fetcher.py
│   ├── test_downtown_analyzer.py
│   └── test_dmur_calculator.py
├── integration/            # Integration tests
│   └── test_full_workflow.py
└── conftest.py            # Shared fixtures
```

### Writing Tests

- **Descriptive names**: Test names should describe what they test
- **Single responsibility**: One test per function behavior
- **Edge cases**: Test boundary conditions and error cases
- **Fixtures**: Use fixtures for common test data

## Release Process

### Version Numbers

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

1. Update version in `setup.py` and `src/dmur_analysis/__init__.py`
2. Update `CHANGELOG.md` with release notes
3. Run full test suite: `pytest tests/`
4. Update documentation if needed
5. Create release PR to main branch
6. Tag release: `git tag v1.0.0`
7. Create GitHub release with notes

## Community Guidelines

### Code of Conduct

- **Be respectful**: Treat all community members with respect
- **Be constructive**: Provide helpful feedback and suggestions
- **Be collaborative**: Work together to improve the project
- **Be inclusive**: Welcome contributors from all backgrounds

### Communication

- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Email**: contact@dmur-analysis.com for private matters

### Recognition

Contributors will be recognized in:

- `CONTRIBUTORS.md` file
- Release notes for significant contributions
- GitHub contributor graphs

## Getting Help

- **Documentation**: Check the [docs](docs/) first
- **Examples**: Look at [examples](examples/) for usage patterns
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Ask questions in GitHub discussions

Thank you for contributing to the DMUR Analysis Toolkit!