from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# In-memory storage
tasks = []
recently_added = None
recently_deleted = None


@app.route("/", methods=["GET", "POST"])
def index():
    global recently_added

    if request.method == "POST":
        task = request.form.get("task")
        if task:
            tasks.append(task)
            recently_added = task
        return redirect(url_for("index"))

    return render_template(
        "index.html",
        tasks=tasks,
        total_tasks=len(tasks),
        recently_added=recently_added,
        recently_deleted=recently_deleted
    )


@app.route("/update/<int:index>", methods=["POST"])
def update_task(index):
    if 0 <= index < len(tasks):
        updated_task = request.form.get("updated_task")
        if updated_task:
            tasks[index] = updated_task
    return redirect(url_for("index"))


@app.route("/delete/<int:index>")
def delete_task(index):
    global recently_deleted

    if 0 <= index < len(tasks):
        recently_deleted = tasks.pop(index)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
