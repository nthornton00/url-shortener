# URL Shortener

A full-stack URL shortening service built with FastAPI (REST APIs), PostgreSQL and JWT authentication.
Shorten long URLs, track clicks, and manage your links through a simple, clean dark-themed UI.

## Live Demo
https://url-shortener-production-bce7.up.railway.app/

## Tech Stack

- **Backend:** Python, FastAPI, REST API
- **Database:** PostgreSQL, SQLAlchemy
- **Authentication:** JWT tokens, bcrypt password hashing
- **Frontend:** HTML, CSS, JavaScript
- **Testing:** Pytest
- **Security:** Rate limiting, input validation, environment variables

## Features

- User registration and login with JWT authentication
- Shorten any valid URL with optional custom short codes
- Automatic redirect when visiting a short link
- Update or delete your existing links
- Track click statistics per link
- Rate limiting to prevent API abuse
- Input validation that rejects invalid URLs
- Protected endpoints — users only see their own links

## Project Structure
```
url-shortener/
├── main.py          # FastAPI app and all endpoints
├── auth.py          # JWT tokens and password hashing
├── models.py        # Database table definitions
├── database.py      # PostgreSQL connection
├── test_main.py     # Pytest test suite
├── index.html       # Frontend UI
├── requirements.txt # Project dependencies
└── .env.example     # Example environment variables
```

## Getting Started

**1. Clone the repository:**
```
git clone https://github.com/nthornton00/url-shortener.git
cd url-shortener
```

**2. Create a virtual environment:**
```
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

**3. Install dependencies:**
```
pip install -r requirements.txt
```

**4. Create a `.env` file:**
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/url_shortener
SECRET_KEY=your-secret-key-here
```

**5. Create the database in PostgreSQL:**
```
psql -U postgres -c "CREATE DATABASE url_shortener;"
```

**6. Start the server:**
```
python -m uvicorn main:app --reload
```

**7. Open the app:**
```
http://127.0.0.1:8000/ui
```

## REST API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/register` | No | Create a new account |
| POST | `/login` | No | Login and receive JWT token |
| POST | `/shorten` | Yes | Create a short URL |
| GET | `/links` | Yes | Get all your links |
| PUT | `/shorten/{code}` | Yes | Update a short URL |
| DELETE | `/shorten/{code}` | Yes | Delete a short URL |
| GET | `/shorten/{code}/stats` | No | Get click statistics |
| GET | `/{code}` | No | Redirect to original URL |

## Running Tests
```
pytest test_main.py -v
```

## Security

- Passwords hashed with bcrypt — never stored in plain text
- JWT tokens expire after 30 minutes
- Sensitive credentials stored in `.env` file
- Rate limiting on URL creation endpoint
- Users can only manage their own links
```

Also create a new file called `.env.example` in your project folder:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/url_shortener
SECRET_KEY=your-secret-key-here

## Known Limitations

- **Session persistence:** When refreshing the browser, the user is automatically logged out. This is because JWT tokens are stored 
in JavaScript memory. In a production environment this would be resolved by storing 
tokens in httpOnly cookies, which persist across refreshes and are more secure as 
they cannot be accessed by JavaScript.