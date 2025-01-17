# ECOM189-big-data-and-machine-learning

[![Project Status: In Progress](https://img.shields.io/badge/Project%20Status-In%20Progress-green.svg)](https://github.com/yourusername/ECOM189-big-data-and-machine-learning)

A repository for the EMAP ECOM184 Big Data and Machine Learning module

## Project Overview

This project includes tools for fetching and analyzing Prime Minister's Questions (PMQ) debates using the They Work For You API.

## Prerequisites

- Python 3.12 or higher
- API key from They Work For You

## Dependencies

The project uses uv for dependency management.

For mac, use:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For Windows, use:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Setup

1. Clone the repository
2. Create a `.env` file in the root directory with your API key:

    ```bash
    THEY_WORK_FOR_YOU_API_KEY=your_api_key_here
    ```

3. Run the scripts:

    If you use `uv run` in a project, i.e. a directory with a pyproject.toml, it will install the current project before running the script. This means you only need to use `uv run`, and then you can run the script directly. E.g.,

    ```bash
    uv run src/main.py
    ```
