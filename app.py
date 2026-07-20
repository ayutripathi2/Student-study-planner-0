
from flask import Flask,render_template,request,redirect, session, flash
from database import connection,cursor
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match"
        
        hashed_password = generate_password_hash(password)

        sql = """
        INSERT INTO users(full_name,email,password)
        VALUES(%s,%s,%s)
        """

        values = (full_name, email, hashed_password)

        cursor.execute(sql, values)

        connection.commit()
         
        flash("Registration successful! Please login.", "success")
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            
            return redirect("/dashboard")

        flash("Invalid email or password.", "danger")
        return redirect("/login")

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    # Get Tasks
    cursor.execute("""
        SELECT id, title, subject, deadline, priority, status
        FROM tasks
        WHERE user_id = %s
        ORDER BY deadline ASC
    """, (session["user_id"],))

    tasks = cursor.fetchall()

    # Total Tasks
    cursor.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = %s
    """, (session["user_id"],))

    total_tasks = cursor.fetchone()[0]

    # Completed Tasks
    cursor.execute("""
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = %s
        AND status = 'Completed'
    """, (session["user_id"],))

    completed_tasks = cursor.fetchone()[0]

    # Pending Tasks
    pending_tasks = total_tasks - completed_tasks

    # Completion %
    if total_tasks == 0:
        completion_percentage = 0
    else:
        completion_percentage = round(
            (completed_tasks / total_tasks) * 100,
            1
        )

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        completion_percentage=completion_percentage
    )
@app.route("/add-task", methods=["GET", "POST"])
def add_task():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]
        subject = request.form["subject"]
        
        deadline = request.form["deadline"]
        priority = request.form["priority"]

        cursor.execute("""
        INSERT INTO tasks
        (user_id,title,subject,deadline,priority)

        VALUES(%s,%s,%s,%s,%s)
        """, (

            session["user_id"],
            title,
            subject,
            
            deadline,
            priority

        ))

        connection.commit()

        return redirect("/dashboard")

    return render_template(
    "add_task.html",
    page_title="Add New Task",
    button_text="Add Task",
    task=None
)

@app.route("/delete-task/<int:task_id>")
def delete_task(task_id):

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute(
        """
        DELETE FROM tasks
        WHERE id=%s
        AND user_id=%s
        """,
        (task_id, session["user_id"])
    )

    connection.commit()

    return redirect("/dashboard")

@app.route("/complete-task/<int:task_id>")
def complete_task(task_id):

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        UPDATE tasks
        SET status='Completed'
        WHERE id=%s
        AND user_id=%s
    """,(task_id,session["user_id"]))

    connection.commit()

    return redirect("/dashboard")
@app.route("/edit-task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]
        subject = request.form["subject"]
       
        deadline = request.form["deadline"]
        priority = request.form["priority"]

        cursor.execute("""
            UPDATE tasks
            SET title=%s,
                subject=%s,
                
                deadline=%s,
                priority=%s
            WHERE id=%s
            AND user_id=%s
        """,(
            title,
            subject,
            
            deadline,
            priority,
            task_id,
            session["user_id"]
        ))

        connection.commit()

        return redirect("/dashboard")

    cursor.execute("""
        SELECT *
        FROM tasks
        WHERE id=%s
        AND user_id=%s
    """,(task_id,session["user_id"]))

    task = cursor.fetchone()

    return render_template(
    "add_task.html",
    page_title="Edit Task",
    button_text="Update Task",
    task=task
)

@app.route("/tasks")
def tasks():

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT id, title, subject, deadline, priority, status
        FROM tasks
        WHERE user_id=%s
        ORDER BY deadline ASC
    """,(session["user_id"],))

    all_tasks = cursor.fetchall()

    return render_template(
        "tasks.html",
        tasks=all_tasks,
        user_name=session["user_name"]
    )

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT full_name, email
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id=%s
    """, (session["user_id"],))
    total_tasks = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id=%s
        AND status='Completed'
    """, (session["user_id"],))
    completed = cursor.fetchone()[0]

    pending = total_tasks - completed

    return render_template(
        "profile.html",
        user=user,
        total_tasks=total_tasks,
        completed=completed,
        pending=pending
    )
@app.route("/progress")
def progress():

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=%s",
        (session["user_id"],)
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=%s AND status='Completed'",
        (session["user_id"],)
    )
    completed = cursor.fetchone()[0]

    pending = total - completed

    percentage = 0

    if total > 0:
        percentage = round((completed / total) * 100)

    return render_template(
        "progress.html",
        total=total,
        completed=completed,
        pending=pending,
        percentage=percentage
    )
if __name__ == "__main__":
    app.run(debug=True)