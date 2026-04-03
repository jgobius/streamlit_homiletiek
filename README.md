# Streamlit Homiletiek

A Streamlit web application that assists with sermon preparation and worship service analysis (*preekanalyses*). The tool generates contextual analyses based on the church, location, and date of a service, helping preachers align their sermons with the liturgical context.

## Features

- **User authentication** — register, log in, and log out with JWT-based session management
- **Sermon analyses** — create and manage analyses per service, including:
  - Bible texts (*bijbelteksten*)
  - Commentaries (*commentaren*)
  - Hymn suggestions (*liedsuggesties*)
  - Liturgical year positioning (*liturgisch jaar*)
  - Postille
  - Structural exegesis (*structuralistische exegese*)
  - Theology (*theologie*)
- **Church management** — add and manage church congregations
- **Dashboard** — overview of all sermon analyses

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | [Streamlit](https://streamlit.io/) |
| Data validation | [Pydantic](https://docs.pydantic.dev/) |
| Auth | JWT (`PyJWT`) |
| HTTP client | `requests` |
| Data handling | `pandas` |

## Project Structure

```
streamlit_homiletiek/
├── main.py                        # App entry point & page routing
├── page_navigation/               # Streamlit pages
│   ├── welcome.py
│   ├── login.py / logout.py / register.py
│   ├── analyses/                  # Create & view analyses
│   ├── analysis_results/          # Individual analysis views
│   └── churches/                  # Church management
├── src/
│   ├── api/                       # API handler & JWT management
│   ├── models/                    # Pydantic data models
│   └── utils/                     # Shared utility functions
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- A running backend API (providing authentication and analysis endpoints)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd streamlit_homiletiek

# Install dependencies
pip install -r requirements.txt
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
```

### Configuration

The app reads secrets from a `.streamlit/secrets.toml` file. Create this folder and file before running the app:

```bash
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

Then populate `.streamlit/secrets.toml` with the following keys:

```toml
# Base URL of the Django/DRF backend API (no trailing slash)
API_BASE_URL = "http://localhost:8000"

# Base URL of the AI agent API used for structured scripture lookups
API_AGENT_URL = "http://localhost:8001"
```

| Key | Description |
|-----|-------------|
| `API_BASE_URL` | Root URL of the backend REST API (auth, registration, analysis endpoints) |
| `API_AGENT_URL` | Root URL of the agent API used for retrieving structured scripture data |

> **Note:** `.streamlit/secrets.toml` contains sensitive credentials and should be added to `.gitignore`.

### Running the App

```bash
streamlit run main.py
```

The app will be available at `http://localhost:8501` by default.

## Requirements

See [requirements.txt](requirements.txt) for the full pinned dependency list. Core dependencies:

- `streamlit >= 1.53.0`
- `pydantic >= 2.12.5`
- `pyjwt >= 2.10.1`
- `requests >= 2.32.5`
- `pandas >= 2.3.3`
- `email-validator >= 2.3.0`
