import os
#flask modules
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
#password hashing
from werkzeug.security import check_password_hash, generate_password_hash
#load in env
from dotenv import load_dotenv
#database connection
from database import get_db_connection
#loading the SOS integration functions
from sos_integration import process_sos_matter
#allows the use of field names instead of indexing
from psycopg.rows import dict_row


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

#Writing an audit log entry
def write_audit_log(user_id, action, sos_matter_id=None, details=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_log (
                        user_id,
                        sos_matter_id,
                        action,
                        details
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    user_id,
                    sos_matter_id,
                    action,
                    details
                ))

            conn.commit()

    except Exception as e:
        print(f"Audit log error: {e}")


#Login page 

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

            # Audit log - login
            write_audit_log(
                user_id=user[0],
                action="LOGIN",
                details="User logged in successfully"
            )

            return redirect(url_for("dashboard"))

        # Incorrect login details
        return render_template(
            "login.html",
            error="Invalid email address or password."
        )

    # GET request - show login page
    return render_template("login.html")
    

#route to the matters screen, then the code to pull through the matters from the database
@app.route("/matters")
def matters():

    # Check user is logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Admin can see all matters (including joins between two tables)
    if session.get("is_admin"):
        cur.execute("""
            SELECT
                m.sos_matter_id,
                m.matter_ref,
                m.client_name,
                m.matter_type,
                m.status,
                m.fee_earner,
                o.organisation_name
            FROM matters m
            JOIN organisations o
                ON m.organisation_id = o.organisation_id
            ORDER BY m.matter_ref
        """)

    # Normal users only see their organisation's matters (including joins between two tables)
    else:
        cur.execute("""
            SELECT
                m.sos_matter_id,
                m.matter_ref,
                m.client_name,
                m.matter_type,
                m.status,
                m.fee_earner,
                o.organisation_name
            FROM matters m
            JOIN organisations o
                ON m.organisation_id = o.organisation_id
            WHERE m.organisation_id = %s
            ORDER BY m.matter_ref
        """, (session["organisation_id"],))

    matters = cur.fetchall()

    cur.close()
    conn.close()

    matter_types = {
    "1501": "Sale",
    "1502": "Purchase",
    "1503": "Remortgage",
    "1504": "Transfer of Equity"
    }

    write_audit_log(
                    user_id=session["user_id"],
                    action="VIEW_ALL_MATTER",
                    details="User viewed matter details"
                    )

    return render_template(
        "matters.html",
        matters=matters,
        matter_types=matter_types
    )


#View individual matter 
@app.route("/matter/<string:matter_ref>")
def view_matter(matter_ref):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None

    try:
        conn = get_db_connection()
        #Converts result into python dictonary so we can use names instead of index
        with conn.cursor(row_factory=dict_row) as cur:

            
            # Getting the matter details
            

            if session.get("is_admin"):

                cur.execute(
                    """
                    SELECT
                        sos_matter_id,
                        matter_ref,
                        organisation_id,
                        matter_type,
                        status,
                        client_name,
                        property_address,
                        fee_earner,
                        opened_date,
                        last_updated
                    FROM matters
                    WHERE matter_ref = %s
                    """,
                    (matter_ref,)
                )

            else:

                cur.execute(
                    """
                    SELECT
                        sos_matter_id,
                        matter_ref,
                        organisation_id,
                        matter_type,
                        status,
                        client_name,
                        property_address,
                        fee_earner,
                        opened_date,
                        last_updated
                    FROM matters
                    WHERE matter_ref = %s
                    AND organisation_id = %s
                    """,
                    (
                        matter_ref,
                        session["organisation_id"]
                    )
                )

            matter = cur.fetchone()

            if matter is None:
                return "Matter not found", 404


            
            # Convert SOS code to plain text
            

            matter_types = {
                "1501": "Sale",
                "1502": "Purchase",
                "1503": "Remortgage",
                "1504": "Transfer of Equity"
            }

            matter_type_name = matter_types.get(
                str(matter["matter_type"]),
                str(matter["matter_type"])
            )


            
            # Get milestones for matter type
            
            cur.execute(
                """
                SELECT
                    md.milestone_definition_id,
                    md.milestone_code,
                    md.milestone_name,
                    md.display_order,
                    mm.matter_milestone_id,
                    mm.milestone_date,

                    CASE
                        WHEN mm.matter_milestone_id IS NOT NULL
                        THEN TRUE
                        ELSE FALSE
                    END AS is_completed

                FROM milestone_definitions md

                LEFT JOIN matter_milestones mm
                    ON mm.milestone_definition_id =
                       md.milestone_definition_id
                    AND mm.sos_matter_id = %s

                WHERE md.matter_type = %s
                AND md.is_active = TRUE

                ORDER BY md.display_order
                """,
                (
                    matter["sos_matter_id"],
                    matter_type_name
                )
            )

            milestones = cur.fetchall()


        
        # Progress Calculations
        

        completed_count = sum(
            1
            for milestone in milestones
            if milestone["is_completed"]
        )

        total_count = len(milestones)

        if total_count > 0:

            progress_percentage = round(
                (completed_count / total_count) * 100
            )

        else:

            progress_percentage = 0

           
         # Audit log - individual matter
            write_audit_log(
                user_id=session["user_id"],
                action="VIEW_MATTER",
                sos_matter_id=matter["sos_matter_id"],
                details=f"User viewed matter {matter['matter_ref']}"
            )       
                                    
            
                        
        # Loading page
        

        return render_template(
            "view_matter.html",
            matter=matter,
            matter_type_name=matter_type_name,
            milestones=milestones,
            completed_count=completed_count,
            total_count=total_count,
            progress_percentage=progress_percentage
        )


    except Exception as e:

        print(
            f"Error loading matter {matter_ref}: {e}"
        )

        return (
            f"Error loading matter {matter_ref}: {str(e)}",
            500
        )

    finally:

        if conn:
            conn.close()
# API route used by SOS to create/update matters
@app.route("/api/matters", methods=["POST"])
def receive_matter():

    conn = None

    try:
        #check api key
        auth_header = request.headers.get("Authorization")

        expected_key = os.getenv("SOS_API_KEY")

        if not auth_header or auth_header != f"Bearer {expected_key}":
            return jsonify({
                "success": False,
                "error": "Unauthorised"
            }), 401

        # Get JSON sent by SOS
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data received"
            }), 400

        # Connect to database
        conn = get_db_connection()

        # Pass the SOS data to sos_integration.py
        result = process_sos_matter(conn, data)

        # Send success response back to SOS
        return jsonify({
            "success": True,
            "action": result["action"],
            "sosMatterId": result["sosMatterId"]
        }), 200
#catching error - data error
    except ValueError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
#catching error - server/database error
    except Exception as e:

        if conn:
            conn.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:

        if conn:
            conn.close()

            
#Admin page
@app.route("/admin")
def users():

    #user must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

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
# Audit log - limit to 100 records
    cursor.execute("""
        SELECT
            a.audit_id,
            a.created_at,
            a.action,
            a.sos_matter_id,
            a.details,
            u.email
        FROM audit_log a
        LEFT JOIN users u
            ON a.user_id = u.user_id
            ORDER BY a.created_at DESC
            LIMIT 100
            """)
    audit_entries = cursor.fetchall()
    

    cursor.close()
    conn.close()

    write_audit_log(
                    user_id=session["user_id"],
                    action="VIEW_ADMIN_PAGE",
                    details="User accessed admin page"
                    )
    

    return render_template("admin.html",users=users,audit_entries=audit_entries)


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



