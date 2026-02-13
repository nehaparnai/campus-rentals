from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "campus_trust_key_99" # In production, use an environment variable

# -------------------------
# DATABASE UTILITIES
# -------------------------
def get_db_connection():
    # Using absolute path can sometimes prevent issues in different environments
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row  
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        trust_score INTEGER DEFAULT 100
    )""")

    # 2. Micro-Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        location TEXT,
        reward REAL NOT NULL,
        posted_by TEXT,
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # 3. Items for Rent (Supply)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        price_per_day REAL NOT NULL,
        owner_name TEXT,
        is_available BOOLEAN DEFAULT 1
    )""")

    # 4. Items Wanted (Demand)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items_wanted (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        max_budget REAL,
        requester_name TEXT,
        urgency TEXT, 
        status TEXT DEFAULT 'open'
    )""")

    conn.commit()
    conn.close()

# -------------------------
# AUTHENTICATION ROUTES
# -------------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if not user:
            conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
            conn.commit()
        
        conn.close()
        session["user"] = name
        session["email"] = email
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("dashboard.html")

# -------------------------
# MICRO-TASK ROUTES
# -------------------------

@app.route("/tasks")
def tasks():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    all_tasks = conn.execute("SELECT * FROM tasks WHERE status='open' ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("browse_tasks.html", tasks=all_tasks)

@app.route("/post_task", methods=["GET", "POST"])
def post_task():
    if "user" not in session: return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (description, location, reward, posted_by) VALUES (?, ?, ?, ?)",
            (request.form["description"], request.form["location"], request.form["reward"], session["user"])
        )
        conn.commit()
        conn.close()
        flash("Task posted successfully!")
        return redirect(url_for("tasks"))
    return render_template("post_task.html")

# -------------------------
# RENTAL & WANTED ROUTES
# -------------------------

@app.route("/items")
def items():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    available_items = conn.execute("SELECT * FROM items WHERE is_available = 1").fetchall()
    conn.close()
    return render_template("browse_items.html", items=available_items)

@app.route("/list_item", methods=["GET", "POST"])
def list_item():
    if "user" not in session: return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute("INSERT INTO items (item_name, price_per_day, owner_name) VALUES (?, ?, ?)",
                     (request.form["item_name"], request.form["price"], session["user"]))
        conn.commit()
        conn.close()
        flash("Item listed for rent!")
        return redirect(url_for("items"))
    return render_template("list_item.html")

@app.route("/wanted")
def wanted():
    if "user" not in session: return redirect(url_for("login"))
    conn = get_db_connection()
    requests = conn.execute("SELECT * FROM items_wanted WHERE status='open'").fetchall()
    conn.close()
    return render_template("items_wanted.html", requests=requests)

@app.route("/post_wanted", methods=["GET", "POST"])
def post_wanted():
    if "user" not in session: return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db_connection()
        conn.execute("INSERT INTO items_wanted (item_name, max_budget, requester_name, urgency) VALUES (?, ?, ?, ?)",
                     (request.form["item_name"], request.form["budget"], session["user"], request.form["urgency"]))
        conn.commit()
        conn.close()
        flash("Your request has been posted to the campus!")
        return redirect(url_for("wanted"))
    return render_template("post_wanted_form.html")

# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)