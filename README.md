# URL Shortener

A full-stack URL shortening service built with FastAPI and PostgreSQL.
Paste a long URL and get a short link back. Tracks how many times each link is clicked.

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, SQLAlchemy
- **Frontend:** HTML, CSS, JavaScript

## Features

- Shorten any valid URL
- Retrieve original URL from short code
- Update the destination of an existing short link
- Delete a short link
- Track how many times a link has been clicked

## How to Run

1. Make sure PostgreSQL is running and create a database:
```
   CREATE DATABASE url_shortener;
```

2. Install dependencies:
```
   pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
```

3. Update the `DATABASE_URL` in `database.py` with your PostgreSQL password

4. Start the server:
```
   python -m uvicorn main:app --reload
```

5. Open the app:
```
   http://127.0.0.1:8000/ui
```

## API Endpoints

| Method | Endpoint                      | Description           |
|--------|-------------------------------|-----------------------|
| POST   | `/shorten`                    | Create a short URL    |
| GET    | `/{short_code}`               | Retrieve original URL |
| PUT    | `/shorten/{short_code}`       | Update a short URL    |
| DELETE | `/shorten/{short_code}`       | Delete a short URL    |
| GET    | `/shorten/{short_code}/stats` | Get click statistics  |