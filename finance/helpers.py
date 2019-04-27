import requests
import os
import csv
import urllib.parse
import urllib.request

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def lookup(symbol):
    """Look up quote for symbol."""

    # Reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # Reject symbol if it contains comma
    if "," in symbol:
        return None
    # return {
    #         "price": 1253.76,
    #         "symbol": symbol.upper()
    # }

    # Query Alpha Vantage for quote
    # https://www.alphavantage.co/documentation/
    try:

        # GET CSV
        url = "https://www.alphavantage.co/query?apikey={}&datatype=csv&function=TIME_SERIES_WEEKLY&symbol={}".format("66KN7GDP1KR9R8TK",symbol)
        webpage = urllib.request.urlopen(url)

        # Parse CSV
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

        # Ignore first row
        next(datareader)
        # Parse second row
        row = next(datareader)

        # Ensure stock exists
        try:
            price = float(row[4])
        except:
            None

        # Return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
        return {
            "price": price,
            "symbol": symbol.upper()
        }

    except:
        return None

def usd(value):
    """Format value as USD."""
    return "$ {0:.2f}".format(value)
