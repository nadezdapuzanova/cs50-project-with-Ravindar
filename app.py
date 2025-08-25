import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = int(session["user_id"])
    rows = db.execute("SELECT username,cash FROM users WHERE id = ? ;",user_id)
    if len(rows) > 1:
        return apology("Does this user exists",400)
    username = rows[0]["username"]
    cash = rows[0]["cash"]
    rows = db.execute("SELECT symbol,SUM(shares) AS total_shares FROM transactions WHERE user_id=? GROUP BY symbol HAVING shares > 0;",user_id)
    symbols = [key["symbol"] for key in rows]
    stocks = {}
    total_value = 0
    for i,u in enumerate(symbols):
        price = lookup(u)["price"]
        stocks[i] = {}
        stocks[i]["symbol"] = u
        stocks[i]["price"] = float(price)
        stocks[i]["shares"] = int(rows[i]["total_shares"])
        stocks[i]["value"] = stocks[i]["shares"] * stocks[i]["price"]
        total_value += stocks[i]["value"]
    # print("stocks",stocks)
    return render_template("index.html",username=username,stocks=stocks,cash=cash,total_value=total_value)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol,shares = request.form.get("symbol"),request.form.get("shares")
        symbol = symbol.upper()
        if not symbol:
            return apology("Enter a symbol",400)
        if not lookup(symbol):
            return apology("Enter a valid symbol",400)
        if not shares:
            return apology("Enter number of shares",400)
        if not shares.isdigit() or int(shares) <= 0 :
            return apology("Enter only positive and integer number of shares",400)
        print(lookup(symbol)["price"])
        print(float(lookup(symbol)["price"]))
        price_of_share = float(lookup(symbol)["price"])
        print(shares,type(shares))
        needed_money = float(lookup(symbol)["price"]) * int(shares)
        print(session,type(session))
        print("needed_money",needed_money)
        user_id = session["user_id"]
        print("user_id",user_id,type(user_id))
        rows = db.execute("SELECT cash FROM users WHERE id=?",(user_id))
        if len(rows) != 1:
            return apology("mutiple user has mutipe cash")
        money = rows[0]["cash"]
        if money < needed_money:
            return apology("users has only {{ money }} but needed {{ needed_money }}",400)
        else:
            left_money = money - needed_money
            db.execute("UPDATE users SET cash = ? WHERE id= ?;",left_money,user_id)
            db.execute("INSERT INTO transactions( user_id, symbol, price, shares) VALUES(?,?,?,?) ;",user_id, symbol, price_of_share, shares)
            flash(f" successfully buyed shares { shares } of { symbol } company ")
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = int(session["user_id"])
    rows = db.execute("SELECT symbol,price,shares,timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp",user_id)

    return render_template("history.html",stocks = rows)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")
    # User reached route via GT (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # if user make a post request
    if request.method == "POST":
        symbol = request.form.get("symbol")
        result = lookup(symbol)
        if not result:
            return apology("Enter a valid symbol again",400)
        else:
           return render_template("quoted.html",name=result["name"],price=result["price"],symbol=result["symbol"])

    else:
        return render_template("quote.html",)
    return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        username,password,confirmation = request.form.get("username"),request.form.get("password"),request.form.get("confirmation")


        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)
        elif not confirmation:
            return apology("must provide confirmation",400)
        elif password != confirmation:
            return apology("password must be same",400)
        else:
            rows = db.execute("SELECT id FROM users WHERE username = ?",username)
            if len(rows) > 0:
                return apology("username already exists",400)
            else:
                try:
                    db.execute("INSERT INTO users(username,hash) VALUES(?,?);",username,generate_password_hash(password))
                except Exception as E:
                    return apology(f"{E}",400)
            return redirect("/"),200
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = int(session["user_id"])
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = int(request.form.get("shares"))
        if not symbol:
            return apology("select a company symbol",400)
        if not shares :
            return apology(" Enter number of shares",400)
        else:
            rows = db.execute("SELECT SUM(shares) as total_shares FROM transactions WHERE user_id = ? and symbol = ? GROUP BY symbol HAVING total_shares > 0;",user_id,symbol)
            shares_has = rows[0]["total_shares"]
            if shares_has < shares:
                return apology("Not enough shares to sell", 400)
            else:
                price = float(lookup(symbol)["price"])
                total_cost = price * float(shares)
                # update user cash
                # add row to transactions
                rows = db.execute("SELECT cash FROM users WHERE id = ?",user_id)
                user_money = float(rows[0]["cash"])
                left_money = user_money + total_cost
                db.execute("UPDATE users SET cash = ? WHERE id = ?;",left_money,user_id)
                db.execute("INSERT INTO transactions (user_id,symbol,price,shares) VALUES (?,?,?,?);",user_id,symbol.upper(),price,-shares)

                flash(f"successfully sell {{ usd(-shares) }} from {{ symbol }} company ")

        return redirect("/")
    else:
        rows = db.execute("SELECT symbol,SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0;",user_id)
        li = [key["symbol"] for key in rows]
        return render_template("sell.html",li=li)
