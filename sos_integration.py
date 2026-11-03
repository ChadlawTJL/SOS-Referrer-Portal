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
    matter_type = data.get("mattertype")
    client_name = data.get("clientname")
    property_address = data.get("propertyaddress")

    opened_date = parse_sos_date(
        data.get("matterOpenedDate")
    )

    fee_earner = data.get("feeEarner")

    last_updated = parse_sos_date(
        data.get("lastUpdated")
    )

    # Get SOS referrer organisation reference
    org_ref = str(data.get("orgref", "")).strip()

    if not org_ref:
        raise ValueError("orgef is required")

    # Check whether organisation exists in portal database
    cur = conn.cursor()

    cur.execute("""
        SELECT organisation_id
        FROM organisations
        WHERE sos_referrer_id = %s
    """, (org_ref,))

    organisation = cur.fetchone()

    if not organisation:
        raise ValueError(
            "No organisation found for SOS referrer reference: {}".format(org_ref)
        )

    # Get portal organisation ID
    organisation_id = organisation[0]

    # Check whether matter already exists
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
                organisation_id = %s,
                client_name = %s,
                property_address = %s,
                matter_type = %s,
                status = %s,
                opened_date = %s,
                fee_earner = %s,
                last_updated = %s
            WHERE sos_matter_id = %s
        """, (
            organisation_id,
            client_name,
            property_address,
            matter_type,
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
                organisation_id,
                client_name,
                propert_address,
                matter_type,
                status,
                opened_date,
                fee_earner,
                last_updated
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            sos_matter_id,
            sos_matter_id,
            organisation_id,
            client_name,
            property_address,
            matter_type,
            status,
            opened_date,
            fee_earner,
            last_updated
        ))

        action = "created"

    conn.commit()

    cur.close()

    return {
        "action": action,
        "sosMatterId": sos_matter_id
    }
