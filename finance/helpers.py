import os
import requests
import urllib

from finance import db
from flask import redirect, render_template, request, session
from functools import wraps
from sqlalchemy.sql import func
from .models import Transaction


def apology(message, code):
    """Render message and error code as an apology to user"""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=escape(message), bottom=("error " + str(code))), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def get_portfolio():
    """Fetch the portfolio of stocks user has."""

    user_id = session.get("user_id")
    purchases = db.session.query(Transaction.company_name, Transaction.company_symbol, func.sum(Transaction.shares).label("shares")).filter_by(user_id=user_id, trans_type="purchase").group_by(Transaction.company_symbol).order_by(Transaction.company_symbol).all()
    sales = db.session.query(Transaction.company_name, Transaction.company_symbol, func.sum(Transaction.shares).label("shares")).filter_by(user_id=user_id, trans_type="sale").group_by(Transaction.company_symbol).order_by(Transaction.company_symbol).all()
    portfolio = []

    for i in range (0, len(purchases)):
        sales_shares = 0

        if i < len(sales) and sales[i]:
            if purchases[i].company_symbol == sales[i].company_symbol:
                sales_shares = sales[i].shares
        portfolio.append({
            "name": purchases[i].company_name,
            "symbol": purchases[i].company_symbol,
            "shares": purchases[i].shares - sales_shares
        })
    return portfolio


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
