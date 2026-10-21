import os

from flask import Flask, render_template, request, redirect, url_for, session
#password hashing
from werkzeug.security import check_password_hash, generate_password_hash
#load in env
from dotenv import load_dotenv
#database connection
from database import get_db_connection

load_dotenv()
app = Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY")

#route to the dashboard
@app.route("/")
def dashboard():
    # User hasn't logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        role=session["is_admin"]
    )


@app.route("/login", methods=["GET", "POST"])
def login():
# If the user submits the login form
    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find the user using their email address
        cursor.execute("""
            SELECT
                user_id,
                email,
                password_hash,
                is_admin,
                organisation_id
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        # Check user exists and password matches stored hash
        if user and check_password_hash(user[2], password):

            # Save logged-in user's information in the session
            session["user_id"] = user[0]
            session["email"] = user[1]
            session["is_admin"] = user[3]
            session["organisation_id"] = user[4]

            return redirect(url_for("dashboard"))

        # Incorrect login details
        return render_template(
            "login.html",
            error="Invalid email address or password."
        )

    # GET request - show login page
    return render_template("login.html")
    

#route to the matters screen, then the code to pull through the matters from the datbase
@app.route("/matters")
def matters():
    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM matters;")
    matters = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("matter.html", matters=matters)


@app.route("/admin")
def users():

    #user must be logged in
    if "user_id" not in session:
        return redirect(url_for("Login"))

    #user must be an administrator
    if not session.get("is_admin"):
        return redirect(url_for("dashboard"))

    #return table of users
    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute("""
        SELECT
            user_id,
            email,
            is_admin,
            organisation_id
        FROM users
        ORDER BY email;
    """)

    users=cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin.html",users=users)

#creating user from admin page
@app.route("/admin/user/create",methods=["GET","POST"])
def create_user():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if not session.get("is_admin"):
        return redirect(url_for("dashboard"))
    if request.method== "POST":

        email=request.form["email"]
        password = request.form["password"]
        organisation_id=request.form["organisation_id"]
        is_admin="is_admin" in request.form
        #hasing the password
        password_hash=generate_password_hash(password)

        conn=get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (
                email,
                password_hash,
                is_admin,
                organisation_id
            )
            VALUES (%s, %s, %s, %s);
        """, (
            email,
            password_hash,
            is_admin,
            organisation_id
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("admin"))

    return render_template("create_user.html")

@app.route("/admin/user/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):

    # Check the user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Check the logged-in user is an admin
    if not session.get("is_admin"):
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # If the edit form has been submitted
    if request.method == "POST":

        email = request.form["email"]
        organisation_id = request.form["organisation_id"]

        # True if checkbox is ticked, otherwise False
        is_admin = "is_admin" in request.form

        cursor.execute("""
            UPDATE users
            SET email = %s,
                organisation_id = %s,
                is_admin = %s
            WHERE user_id = %s
        """, (
            email,
            organisation_id,
            is_admin,
            user_id
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("users"))

    # GET request - retrieve the existing user
    cursor.execute("""
        SELECT
            user_id,
            email,
            is_admin,
            organisation_id
        FROM users
        WHERE user_id = %s
    """, (user_id,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("edit_user.html", user=user)

if __name__ == "__main__":
    app.run(debug=True)