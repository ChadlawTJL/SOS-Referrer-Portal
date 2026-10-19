import os

from flask import Flask, render_template, request, redirect, url_for, session
#password hashing
from werkzeug.security import check_password_hash
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
        role=session["role"]
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
                role,
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
            session["role"] = user[3]
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

    return render_template("matters.html", matters=matters)


@app.route("/users")
def users():
    return render_template("users.html")


if __name__ == "__main__":
    app.run(debug=True)