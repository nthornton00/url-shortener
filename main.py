from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import random
import string

from database import engine, get_db, Base
import models

from pydantic import BaseModel, HttpUrl, field_validator, ConfigDict, EmailStr
from fastapi.responses import FileResponse

from auth import hash_password, verify_password, create_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm

from datetime import datetime

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


class URLRequest(BaseModel):
    url: HttpUrl
    custom_code: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        url_str = str(v)
        from urllib.parse import urlparse
        host = urlparse(url_str).hostname
        if not host:
            raise ValueError("Invalid URL")

        # List of valid TLDs
        valid_tlds = [
            "com", "org", "net", "io", "gov", "edu", "co",
            "us", "uk", "ca", "au", "de", "fr", "jp", "sh",
            "ai", "app", "dev", "xyz", "info", "me", "tv"
        ]

        parts = host.split(".")
        tld = parts[-1].lower()

        if tld not in valid_tlds:
            raise ValueError(f"Invalid domain extension '.{tld}' — must be a known TLD like .com or .io")

        return v


class UserRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        # Make sure TLD is at least 2 characters
        domain = v.split("@")[1]
        tld = domain.split(".")[-1]
        if len(tld) < 2:
            raise ValueError("Please enter a valid email address")
        return v


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_code: str
    url: str
    access_count: int
    created_at: datetime
    updated_at: datetime


class URLUpdate(BaseModel):
    url: HttpUrl
    new_code: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        url_str = str(v)
        from urllib.parse import urlparse
        host = urlparse(url_str).hostname
        if not host:
            raise ValueError("Invalid URL")

        valid_tlds = [
            "com", "org", "net", "io", "gov", "edu", "co",
            "us", "uk", "ca", "au", "de", "fr", "jp", "sh",
            "ai", "app", "dev", "xyz", "info", "me", "tv"
        ]

        parts = host.split(".")
        tld = parts[-1].lower()

        if tld not in valid_tlds:
            raise ValueError(f"Invalid domain extension '.{tld}'")

        return v


# This creates the table in PostgreSQL if it doesn't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Allows for rate limiting for REST API
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/ui", include_in_schema=False)
def frontend():
    return FileResponse("index.html")


def generate_code():
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=6))


@app.get("/")
def home():
    return FileResponse("index.html")


@app.post("/register", status_code=201)
def register(data: UserRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": f"Account created for {new_user.email}"}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    # Check user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create and return a token
    token = create_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/shorten", status_code=201)
@limiter.limit("10s/minute")
def shorten_url(request: Request, data: URLRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    long_url = str(data.url)

    # Use custom code if provided, otherwise generate one
    code = data.custom_code if data.custom_code else generate_code()

    # Check if that code is already taken
    existing = db.query(models.URL).filter(models.URL.short_code == code).first()
    if existing:
        raise HTTPException(status_code=409, detail="That short code is already taken")

    # Create a new row in the database
    new_url = models.URL(url=long_url, short_code=code, user_id=current_user.id)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    return {"short_code": code, "url": long_url}


@app.get("/links", response_model=list[LinkResponse])
def get_my_links(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    links = (
        db.query(models.URL)
        .filter(models.URL.user_id == current_user.id)
        .order_by(models.URL.created_at.desc())
        .all()
    )
    return links


@app.get("/shorten/{short_code}/stats")
def get_stats(short_code: str, db: Session = Depends(get_db)):
    url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short code not found")

    return {
        "short_code": short_code,
        "url": url_entry.url,
        "access_count": url_entry.access_count,
        "created_at": url_entry.created_at,
        "updated_at": url_entry.updated_at
    }


@app.put("/shorten/{short_code}")
def update_url(short_code: str, data: URLUpdate, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short code not found")

    # Update URL
    url_entry.url = str(data.url)

    # If new code provided use it, if empty generate a random one
    if data.new_code:
        # Check if that code is already taken by another link
        existing = db.query(models.URL).filter(models.URL.short_code == data.new_code).first()
        if existing and existing.id != url_entry.id:
            raise HTTPException(status_code=409, detail="That short code is already taken")
        url_entry.short_code = data.new_code
    else:
        # Generate a fresh random code
        url_entry.short_code = generate_code()

    db.commit()
    db.refresh(url_entry)

    return {"short_code": url_entry.short_code, "url": url_entry.url}


@app.delete("/shorten/{short_code}", status_code=204)
def delete_url(short_code: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short code not found")

    db.delete(url_entry)
    db.commit()

    return None

@app.delete("/user", status_code=204)
def delete_account(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Delete all links belonging to the user first
    db.query(models.URL).filter(models.URL.user_id == current_user.id).delete()
    # Then delete the user
    db.delete(current_user)
    db.commit()
    return None


@app.get("/{short_code}")
def redirect(short_code: str, db: Session = Depends(get_db)):
    url_entry = db.query(models.URL).filter(models.URL.short_code == short_code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short code not found")

    url_entry.access_count += 1
    db.commit()

    return RedirectResponse(url=url_entry.url)
