
from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "todo-secret-key"

DATABASE = "todo.db"
ALLOWED_USER="Marushka"

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

# ---------- SESSION TIMEOUT (ONLY ONE) ----------

@app.before_request
def session_timeout():
    # Skip timeout for login, static, timeout page, AND API routes
    if request.endpoint is None:
        return

    if request.endpoint.startswith("api_"):
        return

    if request.endpoint in ("login", "static", "session_timeout_page"):
        return

    if "user" in session:
        now = datetime.now().timestamp()

        if "last_activity" in session:
            idle_time = now - session["last_activity"]

            if idle_time > 10:
                flash("Session timed out due to inactivity. Please login again.")
                session.clear()
                return redirect(url_for("session_timeout_page"))

        session["last_activity"] = now


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

        if username==ALLOWED_USER:
            session["user"] = username
            session["last_activity"] = datetime.now().timestamp()  # ✅ FIXED KEY
            session["recently_added"] = ""
            session["recently_deleted"] = ""
            return redirect(url_for("index"))
        else:
            flash("Unauthorized user. Access denied.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/session-timeout")
def session_timeout_page():
    return render_template("session_timeout_page.html")


# ---------- API ROUTES ----------

@app.route("/api/tasks", methods=["GET"])
def api_get_tasks():
    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()

    task_list = []
    for task in tasks:
        task_list.append({
            "id": task["id"],
            "title": task["title"]
        })

    return jsonify(task_list), 200


@app.route("/api/tasks/<int:id>", methods=["GET"])
def api_get_task(id):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (id,)).fetchone()
    conn.close()

    if task:
        return jsonify({
            "id": task["id"],
            "title": task["title"]
        }), 200
    else:
        return jsonify({"error": "Task not found"}), 404


@app.route("/api/tasks", methods=["POST"])
def api_create_task():
    data = request.get_json()

    if not data or "title" not in data:
        return jsonify({"error": "Title is required"}), 400

    conn = get_db()
    conn.execute("INSERT INTO tasks (title) VALUES (?)", (data["title"],))
    conn.commit()
    conn.close()

    return jsonify({"message": "Task created successfully"}), 201


@app.route("/api/tasks/<int:id>", methods=["PUT"])
def api_update_task(id):
    data = request.get_json()

    if not data or "title" not in data:
        return jsonify({"error": "Title is required"}), 400

    conn = get_db()
    conn.execute("UPDATE tasks SET title = ? WHERE id = ?", (data["title"], id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Task updated successfully"}), 200


@app.route("/api/tasks/<int:id>", methods=["DELETE"])
def api_delete_task(id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Task deleted successfully"}), 200


# ---------- MAIN ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
