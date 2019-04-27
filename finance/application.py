import os
import random
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session,url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required,lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method=="POST":
        name = request.form.get("username")
        password = request.form.get("password")
        cfmpass = request.form.get("cfmpass")
        if not name:
            return apology("Hey user , enter your name",403)
        elif not password or not cfmpass:
            return apology("Hey dumbo , enter your password",403)
        elif password != cfmpass:
            return apology("Oh my dumplings ! Passwords do not match",402)


        hash = generate_password_hash(password)
        new_id = db.execute("INSERT INTO users (username,hash) VALUES(:x,:hash)",x=name,hash=hash)
        if not new_id:
            return apology("Buddy , choose a different user name",400)

        flash("Welcome  ")   #NOT WORKING
        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("bro , invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/index")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/index")
@login_required
def index():
    users = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
    stocks = db.execute(
        "SELECT symbol, price_per_share, SUM(shares) as total_shares FROM transactions WHERE useri_id = :user_id GROUP BY symbol HAVING total_shares > 0", user_id=session["user_id"])

    cash_remaining = users[0]["cash"]
    total = cash_remaining

    return render_template("index.html", quotes=quotes, stocks=stocks, total=total, cash_remaining=cash_remaining)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method=="POST":
        quote=lookup(request.form.get("symbol"))
        if not quote:
            return apology("invalid symbol haha pal",403)
        return render_template("quoted.html",quote=quote)
    else:
        return render_template("quote.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))

        # Check if the symbol exists
        if quote == None:
            return apology("invalid symbol", 400)

        shares = int(request.form.get("shares"))

        # Check if # of shares requested was right
        if not shares or shares <= 0:
            return apology("can't buy less than or equal to 0 shares", 400)

        # Query database for username
        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # How much $$$ the user still has in their account
        cash_remaining = rows[0]["cash"]
        price_per_share = quote["price"]

        # Calculate the price of requested shares
        total_price = price_per_share * shares

        if total_price > cash_remaining:
            return apology("not enough fund to buy this , poor guy!!")

        # Book keeping (TODO: should be wrapped with a transaction)
        db.execute("UPDATE users SET cash = cash - :price WHERE id = :user_id", price=total_price, user_id=session["user_id"])
        db.execute("INSERT INTO transactions (useri_id, symbol, shares, price_per_share) VALUES(:user_id, :symbol, :shares, :price)",
                   user_id=session["user_id"],
                   symbol=request.form.get("symbol"),
                   shares=shares,
                   price=price_per_share)

        flash("Bought!")

        return redirect("/index")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT symbol,shares,price_per_share,created_at FROM transactions WHERE useri_id=:x ORDER BY created_at ASC",x=session["user_id"])
    if rows:
        return render_template("history.html",rows=rows)
    else:
        return apology("nothing to show here")




@app.route("/more")
def more():
    return render_template("more.html") 


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        quote=lookup(request.form.get("symbol"))
        share=int(request.form.get("shares"))
        if not quote or not share or share<=0:
            return apology("invalid input")
        money =db.execute("SELECT cash FROM users WHERE id=:x",x=session["user_id"])
        rows=db.execute("SELECT SUM(shares) AS total_shares FROM transactions WHERE useri_id=:x AND symbol=:symbol GROUP BY symbol",x=session["user_id"],symbol=request.form.get("symbol"))
        if not rows:
            return apology("none")
        if share>rows[0]["total_shares"]:
            return apology("not sufficient shares available")
        total_price=(quote["price"] * share)

        db.execute("UPDATE users SET cash=cash + :x WHERE id=:z",x=total_price,z=session["user_id"] )
        db.execute("INSERT INTO transactions (useri_id,symbol,shares,price_per_share) VALUES(:x,:y,:z,:q)", x =session["user_id"],y=request.form.get("symbol"),z=-share,q=quote["price"])
        flash("Sold !!")
        return redirect("/index")
    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)



@app.route("/chat",methods=["GET","POST"])
@login_required
def chat():
    ask = request.form.get("ask")
    if ask=="what is stock marketing":
        msg="The stock market refers to public markets that exist for issuing, buying and selling stocks that trade on a stock exchange or over-the-counter. Stocks, also known as equities, represent fractional ownership in a company, and the stock market is a place where investors can buy and sell ownership of such investible assets. "
    elif ask=="why should i invest":
        msg="Because you seem intelligent to me !!"
    elif ask=="what is a stock":
        msg="A stock is a general term used to describe the ownership certificates of any company."
    elif ask=="what is the purpose of stock marketing":
        msg="The stock market serves two very important purposes. The first is to provide capital to companies that they can use to fund and expand their businesses. The secondary purpose the stock market serves is to give investors – those who purchase stocks – the opportunity to share in the profits of publicly-traded companies."
    elif ask=="what is quote":
        msg="A stock quote is the price of a stock as quoted on an exchange. A basic quote for a specific stock provides information, such as its bid and ask price, last-traded price and volume traded."
    
    elif ask=="bye":
        return render_template("quote.html")    
    else:
        msg=" Welcome to the World of Stock Marketing . Ask me anything ."
    return render_template("chat.html")


@app.route("/add",methods=["GET","POST"])
@login_required
def add_cash():
    if request.method == "POST":
        atm=request.form.get("atm")
        pin=request.form.get("pin")
        amount=int(request.form.get("amount"))
        if not atm or not pin or not amount:
            return apology("invalid details",403)
        if len(atm)!=4 or len(pin)!=4:
            return apology("invalid account information",403)
        if amount<=0 or amount>10000:
            return apology("you can't add that much !!")
        db.execute("UPDATE users SET cash=cash+ :amount WHERE id=:x",amount=amount,x=session["user_id"])
        flash("Cash Added!!")
        code=random.randint(1,51)
        return render_template("scratch.html",code=code)
    else:
        return render_template("add.html")

@app.route("/scratch",methods=["GET","POST"])
@login_required
def scratch():
    if request.method =="POST":
        code=int(request.form.get("code"))
        if code<=0:
            return apology("invalid input")
        if code==22:
            db.execute("UPDATE users SET cash=cash+ :amount WHERE id=:x",amount=code,x=session["user_id"])
            flash("Coupon Cash Added")
        else:
            flash("Better Luck Next Time")
        return redirect("/quote")
    else:
        return render_template("scratch.html")