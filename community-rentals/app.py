from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "campus_trust_key_99"

# -------------------------
# DATABASE
# -------------------------

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        trust_score INTEGER DEFAULT 100
    )
    """)

    # MICRO TASKS (UPDATED)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT,
        reward REAL NOT NULL,
        posted_by TEXT,
        accepted_by TEXT,
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ITEMS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        price_per_day REAL NOT NULL,
        owner_name TEXT,
        is_available BOOLEAN DEFAULT 1
    )
    """)

    conn.commit()
    conn.close()

# -------------------------
# AUTH
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
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    user = conn.execute(
        "SELECT trust_score FROM users WHERE name=?",
        (session["user"],)
    ).fetchone()
    conn.close()

    trust = user["trust_score"] if user else 100

    return render_template("dashboard.html", trust=trust)

# -------------------------
# MICRO TASKS
# -------------------------

@app.route("/tasks")
def tasks():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    all_tasks = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return render_template("browse_tasks.html", tasks=all_tasks)


@app.route("/post_task", methods=["GET", "POST"])
def post_task():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tasks (title, description, location, reward, posted_by) VALUES (?, ?, ?, ?, ?)",
            (
                request.form["title"],
                request.form["description"],
                request.form["location"],
                request.form["reward"],
                session["user"]
            )
        )
        conn.commit()
        conn.close()

        flash("Task posted successfully!")
        return redirect(url_for("tasks"))

    return render_template("post_task.html")


@app.route("/accept_task/<int:task_id>")
def accept_task(task_id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE tasks SET status='accepted', accepted_by=? WHERE id=? AND status='open'",
        (session["user"], task_id)
    )
    conn.commit()
    conn.close()

    flash("Task accepted!")
    return redirect(url_for("tasks"))


@app.route("/complete_task/<int:task_id>")
def complete_task(task_id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    task = conn.execute(
        "SELECT * FROM tasks WHERE id=?",
        (task_id,)
    ).fetchone()

    if task and task["accepted_by"] == session["user"]:
        conn.execute(
            "UPDATE tasks SET status='completed' WHERE id=?",
            (task_id,)
        )

        conn.execute(
            "UPDATE users SET trust_score = trust_score + 5 WHERE name=?",
            (session["user"],)
        )

        conn.commit()

    conn.close()

    flash("Task completed! Trust increased.")
    return redirect(url_for("tasks"))

# -------------------------
# RENTAL ITEMS (SIMPLE)
# -------------------------

@app.route("/items")
def items():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    return render_template("browse_items.html", items=items)


@app.route("/list_item", methods=["GET", "POST"])
def list_item():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO items (item_name, description, category, price_per_day, owner_name) VALUES (?, ?, ?, ?, ?)",
            (
                request.form["item_name"],
                request.form["description"],
                request.form["category"],
                request.form["price"],
                session["user"]
            )
        )
        conn.commit()
        conn.close()

        flash("Item listed successfully!")
        return redirect(url_for("items"))

    return render_template("list_item.html")

# -------------------------
# RUN
# -------------------------

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
