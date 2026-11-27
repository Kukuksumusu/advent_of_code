"""Manage the Advent of Code session and download puzzle inputs."""

import os
import re
import sqlite3
from contextlib import closing
from html import unescape
from http.client import HTTPException, HTTPSConnection
from pathlib import Path

HOST = "adventofcode.com"
USER_AGENT = (
    "github.com/Kukuksumusu/advent_of_code_2025 (contact: https://github.com/Kukuksumusu/advent_of_code_2025/issues)"
)


class FetchError(RuntimeError):
    """A puzzle input could not be downloaded."""


class StopFetching(FetchError):
    """Further requests need to wait for a network or session issue to be resolved."""


def session_token_path() -> Path:
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config_home / "aocd" / "token"


def validate_token(value: str) -> str:
    token = value.strip()
    if not token:
        raise StopFetching("Paste the value of the Advent of Code session cookie.")
    if any(not 33 <= ord(char) <= 126 or char in ';,"' for char in token):
        raise StopFetching("The Advent of Code session cookie contains invalid characters.")
    return token


def session_token() -> str:
    token_file = session_token_path()
    token = os.environ.get("AOC_SESSION", "").strip()
    if not token and token_file.is_file():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise StopFetching("Run just auth to save your Advent of Code session, or set AOC_SESSION.")
    return validate_token(token)


def chrome_session_token() -> str:
    try:
        from browser_cookie3 import BrowserCookieError, chrome  # type: ignore[import-not-found,import-untyped]
    except ImportError:
        raise StopFetching("Run just auth to load the Chrome helper, or use just auth-manual.") from None

    try:
        cookies = chrome(domain_name=HOST)
    except (BrowserCookieError, OSError, RuntimeError, sqlite3.Error, ValueError):
        raise StopFetching("Could not read the Advent of Code session from Chrome. Use just auth-manual.") from None

    tokens = {
        cookie.value
        for cookie in cookies
        if cookie.name == "session"
        and cookie.domain.lstrip(".").lower() == HOST
        and cookie.path == "/"
        and isinstance(cookie.value, str)
        and cookie.value
        and not cookie.is_expired()
    }
    if not tokens:
        raise StopFetching("No Advent of Code session found in Chrome. Sign in there, or use just auth-manual.")
    if len(tokens) > 1:
        raise StopFetching("Found multiple Advent of Code sessions in Chrome. Use just auth-manual to choose one.")
    return validate_token(tokens.pop())


def _get(path: str, token: str, content_type: str) -> bytes | None:
    try:
        with closing(HTTPSConnection(HOST, timeout=15)) as connection:
            connection.request(
                "GET",
                path,
                headers={"Cookie": f"session={token}", "User-Agent": USER_AGENT},
            )
            response = connection.getresponse()
            if response.status == 404:
                return None
            if response.status == 429:
                raise StopFetching("Advent of Code is rate limiting requests. Try again later.")
            if response.status in (400, 401, 403) or 300 <= response.status < 400:
                raise StopFetching(
                    f"Advent of Code rejected the request (HTTP {response.status}). Check the session cookie."
                )
            if response.status != 200:
                raise FetchError(f"Advent of Code returned HTTP {response.status}.")
            if response.headers.get_content_type() != content_type:
                raise FetchError("Advent of Code returned an unexpected content type.")
            return response.read()
    except (OSError, HTTPException) as error:
        raise StopFetching(f"Connection to Advent of Code failed: {error}") from error


def session_account(token: str) -> str:
    """Identify the signed-in user via the Advent of Code settings page."""
    data = _get("/settings", token, "text/html")
    page = data.decode("utf-8") if data else ""
    user = re.search(r'<div class="user">(.*?)</div>', page, re.DOTALL)
    if user is None:
        raise FetchError("Could not verify the signed-in account on the Advent of Code settings page.")
    name = re.sub(r'<span class="star-count">.*?</span>', "", user[1], flags=re.DOTALL)
    name = " ".join(unescape(re.sub(r"<[^>]+>", "", name)).split())
    if not name:
        raise FetchError("The Advent of Code settings page did not identify the signed-in account.")
    profile = re.search(r"<span>Link to (https://[^<\s]+)</span>", page)
    return f"{name} ({unescape(profile[1])})" if profile else name


def download_input(year: int, day: int, token: str) -> bytes | None:
    """Return the original input bytes, or None for a day the site says is unavailable."""
    data = _get(f"/{year}/day/{day}/input", token, "text/plain")
    if data == b"":
        raise FetchError("Advent of Code returned an empty input.")
    return data
