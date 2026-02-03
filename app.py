from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

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
            recently_added = task  # always update on add

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
    global recently_added, recently_deleted

    if 0 <= index < len(tasks):
        updated_task = request.form.get("updated_task")

        if updated_task:
            old_task = tasks[index]

            # update task
            tasks[index] = updated_task

            # update trackers properly
            recently_deleted = old_task
            recently_added = updated_task  # IMPORTANT FIX

    return redirect(url_for("index"))


@app.route("/delete/<int:index>")
def delete_task(index):
    global recently_deleted, recently_added

    if 0 <= index < len(tasks):
        deleted_task = tasks.pop(index)
        recently_deleted = deleted_task

        # if deleted task was recently added, clear it
        if recently_added == deleted_task:
            recently_added = None

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
