# AI Vocabulary Assistant

A premium vocabulary learning platform foundation built with Flask, MySQL, and Jinja2.

## Setup

1. Create a virtual environment

```bash
python -m venv venv
```

2. Activate the environment

```bash
# Windows
venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create a `.env` file from `.env.example`

```bash
copy .env.example .env
```

5. Run the app

```bash
python app.py
```

6. Open in your browser

[http://127.0.0.1:5000](http://127.0.0.1:5000/)

## Features

- Automatic MySQL database and table creation
- Registration, login, logout
- Protected dashboard and app pages
- Elegant UI foundation with a calm academic design
- Placeholder pages for Search Agent, Review, Quiz, Statistics, Sources, and Settings

## Notes

- Tavily / LLM / OpenClaw are intentionally not implemented yet.
- The app is designed as a stable foundation for future AI features.

## Agent setup (Tavily + LLM)

To enable the Example Search Agent, add the following variables to your `.env` file:

```
TAVILY_API_KEY=your_tavily_key_here
LLM_API_KEY=your_llm_key_here
LLM_BASE_URL=your_llm_base_url_here
LLM_MODEL=your_model_here
```

Testing the agent manually (after creating and logging into an account):

1. Open the Search Agent page.
2. Enter commands such as:

```
add sanction
add abandon
add acquire
```

The agent will search authentic English news sources via Tavily, extract an example sentence, ask the LLM to generate structured vocabulary data, and save results into the database. Visit the `Vocabulary` and `Sources` pages to confirm saved entries.

If you do not configure the keys, the agent will return friendly errors and will not save fabricated sources or URLs.
