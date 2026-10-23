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

#edit user
@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):

    if not session.get("is_admin"):
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        organisation_id = request.form["organisation_id"]
        is_admin = "is_admin" in request.form
        #organisation selected validation
        if not organisation_id:
            return "Please select an organisation", 400

        #if new password was entered - hashing
        if password:
            password_hash = generate_password_hash(password)
        
        cur.execute(
            """
            UPDATE users
            SET email = %s,
                password_hash = %s,
                organisation_id = %s,
                is_admin = %s
            WHERE user_id = %s
            """,
            (email,password_hash, organisation_id, is_admin, user_id)
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("users"))

    # Get the user being edited
    cur.execute(
        "SELECT * FROM users WHERE user_id = %s",
        (user_id,)
    )

    user = cur.fetchone()

    # Get all organisations for the dropdown
    cur.execute(
        "SELECT organisation_id, organisation_name FROM organisations ORDER BY organisation_name"
    )

    organisations = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "edit_user.html",
        user=user,
        organisations=organisations
    )

# Delete user
@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        'DELETE FROM users WHERE user_id = %s',
        (user_id,)
    )

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for("users"))


#create user from admin page
@app.route("/create_user", methods=["GET", "POST"])
def create_user():

    # Make sure user is logged in and is an admin
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Get organisations for the dropdown
    cur.execute("""
        SELECT organisation_id, organisation_name
        FROM organisations
        ORDER BY organisation_name
    """)

    organisations = cur.fetchall()

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        organisation_id = request.form["organisation_id"]

        # Checkbox only appears in the form data when ticked
        is_admin = "is_admin" in request.form

        #hashing the password
        password_hash = generate_password_hash(password)
        #pushing the details into the database
        cur.execute("""
            INSERT INTO users (
                email,
                password_hash,
                organisation_id,
                is_admin
            )
            VALUES (%s, %s, %s, %s)
        """, (
            email,
            password_hash,
            organisation_id,
            is_admin
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect(url_for("users"))

    cur.close()
    conn.close()

    return render_template(
        "create_user.html",
        organisations=organisations
    )

if __name__ == "__main__":
    app.run(debug=True)



