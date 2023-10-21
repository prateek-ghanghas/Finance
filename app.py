import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date

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
    rows = db.execute("SELECT * FROM users")
    if not rows:
        return redirect("/login")

    symbol = db.execute("SELECT symbol FROM infom  WHERE user_id = ? GROUP BY symbol",session["user_id"])
    length = len(symbol)
    shares = db.execute("SELECT SUM(shares) as shares FROM infom WHERE user_id = ? GROUP BY symbol",session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])
    buy_price = db.execute("SELECT price FROM infom WHERE user_id = ? GROUP BY symbol", session["user_id"])
    cash = cash[0]["cash"]
    current_price_list = []
    symbol_list = []
    shares_list = []
    buy_expense = 0
    current_value_of_shares = 0
    for i in range(length):
        data = lookup(symbol[i]["symbol"])
        price = data["price"]
        symbol_list.append(symbol[i]["symbol"])
        shares_list.append(shares[i]["shares"])

        current_price_list.append(price)
        buy_expense += (shares[i]["shares"] * buy_price[i]["price"])
        current_value_of_shares += (current_price_list[i] * shares_list[i])


    balance = cash - buy_expense
    after_profit =  current_value_of_shares + balance



    flash("Bought!")
    return render_template("index.html",symbol = symbol_list, shares = shares_list,length = length,price = current_price_list,balance = balance, total = after_profit)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        data = lookup(symbol)
        if data == None:
            return apology("invalid symbol")

        if int(request.form.get("shares")) <= 0:
            return apology("invalid shares value")
        shares = request.form.get("shares")
        price = data["price"]
        db.execute("INSERT INTO infom (symbol,shares,price,user_id) VALUES (?,?,?,?)",symbol.upper(),shares,price,session["user_id"])
        db.execute("INSERT INTO infom2 (symbol,shares,price,user_id) VALUES (?,?,?,?)",symbol.upper(),shares,price,session["user_id"])
        return redirect("/")


    else:

        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    data_buy = db.execute("SELECT symbol, shares, price, date FROM infom2 WHERE user_id = ?", session["user_id"])
    data_sold = db.execute("SELECT symbol , shares, price, time FROM sold WHERE user_id = ?", session["user_id"])
    return render_template("history.html",bought = data_buy,sold = data_sold)



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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
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
    if request.method == "POST":
        symbol = request.form.get("symbol")
        data = lookup(symbol)
        if data == None:
            return apology("some error occured/invalid symbol")
        data["price"] = usd(data["price"])

        return render_template("quoted.html",somedata = data)



    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
     """Register user"""

     if request.method == "POST":
         if not request.form.get("username"):
            return apology("must provide username")

         # Ensure password was submitted
         elif not request.form.get("password"):
            return apology("must provide password")
         elif request.form.get("confirmation") != request.form.get("password"):
            return apology("password do not match")

         pw =  generate_password_hash(request.form.get("password"))

         row = db.execute("SELECT * FROM users WHERE username = ?",request.form.get("username"))

         if row:
            return apology("username already exist!")
         else:
            db.execute("INSERT INTO users (username,hash) VALUES (?,?)",request.form.get("username"),pw)
            return redirect("/")
     else:
         return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    shares = db.execute("SELECT SUM(shares) as shares FROM infom WHERE user_id = ? GROUP BY symbol",session["user_id"])
    symbol = db.execute("SELECT symbol FROM infom  WHERE user_id = ? GROUP BY symbol",session["user_id"])

    symbol_list = []
    shares_list = []

    for i in range(len(symbol)):
            symbol_list.append(symbol[i]["symbol"])
            shares_list.append(shares[i]["shares"])
    count = {}
    for i in range(len(symbol)):
             count[symbol_list[i]] = shares_list[i]

    if request.method == "POST":
         if int(request.form.get("shares")) < 0:
             return apology("invalid shares value")

         shares_owned = db.execute("SELECT SUM(shares) as shares FROM infom WHERE user_id = ? AND symbol = ?",session["user_id"],request.form.get("symbol"))
         bought_price = db.execute("SELECT SUM(price) as price FROM infom WHERE user_id = ? AND symbol = ?",session["user_id"],request.form.get("symbol"))
         bought_price = bought_price[0]["price"]
         current_price = lookup(request.form.get("symbol"))
         current_price = current_price["price"]
         shares_owned = shares_owned[0]["shares"]
         cash = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])
         cash = cash[0]["cash"]
         cash = cash - (bought_price * shares_owned) + (current_price * int(request.form.get("shares"))) + (bought_price * (shares_owned -  int(request.form.get("shares"))))
         db.execute("UPDATE users SET cash = ? WHERE id = ?",cash,session["user_id"])
         db.execute("INSERT INTO sold (symbol, shares, price,user_id) VALUES (?,?,?,?)",request.form.get("symbol"),request.form.get("shares"),current_price,session["user_id"])


         if request.form.get("symbol") not in symbol_list:
                 return apology("stock not owned")
         if count[request.form.get("symbol")] < int(request.form.get("shares")):
                return apology("out of shares")



         if count[request.form.get("symbol")] == int(request.form.get("shares")):
             db.execute("DELETE FROM infom WHERE symbol = ? and user_id = ?",request.form.get("symbol"),session["user_id"])
         elif count[request.form.get("symbol")] > int(request.form.get("shares")):
             db.execute("UPDATE infom SET shares = ? WHERE user_id = ? AND symbol = ?",(shares_owned -  int(request.form.get("shares"))),session["user_id"],request.form.get("symbol"))




         return redirect("/")

    else:
        return render_template("sell.html", symbols = symbol_list)



