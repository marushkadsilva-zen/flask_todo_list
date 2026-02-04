from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "todo-secret-key"

DATABASE = "todo.db"


# ---------- DB HELPERS ----------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_title TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


def log_history(title, action):
    conn = get_db()
    conn.execute(
        "INSERT INTO task_history (task_title, action, timestamp) VALUES (?, ?, ?)",
        (title, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


# ---------- ROUTES ----------

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    if request.method == "POST":
        task = request.form.get("task")

        if task:
            conn.execute("INSERT INTO tasks (title) VALUES (?)", (task,))
            conn.commit()

            session["recently_added"] = task
            log_history(task, "ADDED")

        conn.close()
        return redirect(url_for("index"))

    tasks = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()

    return render_template(
        "index.html",
        tasks=tasks,
        total_tasks=len(tasks),
        recently_added=session.get("recently_added"),
        recently_deleted=session.get("recently_deleted"),
        username=session.get("user")
    )


@app.route("/update/<int:id>", methods=["POST"])
def update_task(id):
    if "user" not in session:
        return redirect(url_for("login"))

    updated_task = request.form.get("updated_task")

    if updated_task:
        conn = get_db()

        old_task = conn.execute(
            "SELECT title FROM tasks WHERE id = ?", (id,)
        ).fetchone()

        if old_task:
            old_title = old_task["title"]

            conn.execute(
                "UPDATE tasks SET title = ? WHERE id = ?",
                (updated_task, id)
            )
            conn.commit()

            session["recently_deleted"] = old_title
            session["recently_added"] = updated_task

            log_history(old_title, "UPDATED_OLD")
            log_history(updated_task, "UPDATED_NEW")

        conn.close()

    return redirect(url_for("index"))


@app.route("/delete/<int:id>")
def delete_task(id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    task = conn.execute(
        "SELECT title FROM tasks WHERE id = ?", (id,)
    ).fetchone()

    if task:
        title = task["title"]

        conn.execute("DELETE FROM tasks WHERE id = ?", (id,))
        conn.commit()

        session["recently_deleted"] = title
        log_history(title, "DELETED")

    conn.close()
    return redirect(url_for("index"))


@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    history_data = conn.execute(
        "SELECT * FROM task_history ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("history.html", history=history_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")

        if username:
            session["user"] = username
            session["recently_added"] = ""
            session["recently_deleted"] = ""
            return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- MAIN ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
