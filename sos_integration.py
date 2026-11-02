# Import date and time
from datetime import datetime


def parse_sos_date(value):
    # Convert SOS DD/MM/YYYY date to Python date

    if value is None or value.strip() == "":
        return None

    return datetime.strptime(value, "%d/%m/%Y").date()


def process_sos_matter(conn, data):

    # Validate required fields
    sos_matter_id = data.get("sosMatterId")

    if not sos_matter_id:
        raise ValueError("sosMatterId is required")

    # Extract matter-level SOS data
    status = data.get("matterStatus")

    opened_date = parse_sos_date(
        data.get("matterOpenedDate")
    )

    fee_earner = data.get("feeEarner")

    last_updated = parse_sos_date(
        data.get("lastUpdated")
    )

    # Check whether matter already exists
    cur = conn.cursor()

    cur.execute("""
        SELECT sos_matter_id
        FROM matters
        WHERE sos_matter_id = %s
    """, (sos_matter_id,))

    existing_matter = cur.fetchone()

    
    # UPDATE EXISTING MATTER

    if existing_matter:

        cur.execute("""
            UPDATE matters
            SET
                status = %s,
                opened_date = %s,
                fee_earner = %s,
                last_updated = %s
            WHERE sos_matter_id = %s
        """, (
            status,
            opened_date,
            fee_earner,
            last_updated,
            sos_matter_id
        ))

        action = "updated"


    # INSERT NEW MATTER
    

    else:

        cur.execute("""
    INSERT INTO matters (
        sos_matter_id,
        matter_ref,
        status,
        last_updated
    )
    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)

    ON CONFLICT (sos_matter_id)
    DO UPDATE SET
        matter_ref = EXCLUDED.matter_ref,
        status = EXCLUDED.status,
        last_updated = CURRENT_TIMESTAMP
""", (
    data["sosMatterId"],
    data["sosMatterId"],
    data.get("matterStatus")
    ))

        action = "created"

    conn.commit()

    cur.close()

    return {
        "action": action,
        "sosMatterId": sos_matter_id
    }
