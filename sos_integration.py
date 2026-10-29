#import date and time
from datetime import datetime

def parse_sos_date(value):
    #convert SOS date to python date

    if value is None or value.strip() == "":
        return None

    return datetime.strptime(value, "%d/%m/%Y").date()


def process_sos_matter(conn, data):
    # Validate required fields
    sos_matter_id = data.get("sosMatterId")

    if not sos_matter_id:
        raise ValueError("sosMatterId is required")

    # Extract SOS data
    matter_status = data.get("matterStatus")

    client_care_issued = parse_sos_date(
        data.get("clientCareIssued")
    )

    initial_documents_received = parse_sos_date(
        data.get("initialDocumentsReceived")
    )

    id_completed = parse_sos_date(
        data.get("idCompleted")
    )

    note = data.get("note")

    searches_pack_copies = parse_sos_date(
        data.get("searchesPackCopies")
    )

    last_updated = parse_sos_date(
        data.get("lastUpdated")
    )

    mortgage_or_redemption = parse_sos_date(
        data.get("mortgageORedemption")
    )

    exchange_notice_toe = parse_sos_date(
        data.get("exchangeNoticeTOE")
    )

    completion_date = parse_sos_date(
        data.get("completionDate")
    )

    matter_opened_date = parse_sos_date(
        data.get("matterOpenedDate")
    )

    fee_earner = data.get("feeEarner")

    # Check whether matter exists

    cur = conn.cursor()

    cur.execute("""
        SELECT sos_matter_id
        FROM matters
        WHERE sos_matter_id = %s
    """, (sos_matter_id,))

    existing_matter = cur.fetchone()

    # Update existing matter
  
    if existing_matter:

        cur.execute("""
            UPDATE matters
            SET
                matter_status = %s,
                client_care_issued = %s,
                initial_documents_received = %s,
                id_completed = %s,
                note = %s,
                searches_pack_copies = %s,
                last_updated = %s,
                mortgage_or_redemption = %s,
                exchange_notice_toe = %s,
                completion_date = %s,
                matter_opened_date = %s,
                fee_earner = %s
            WHERE sos_matter_id = %s
        """, (
            matter_status,
            client_care_issued,
            initial_documents_received,
            id_completed,
            note,
            searches_pack_copies,
            last_updated,
            mortgage_or_redemption,
            exchange_notice_toe,
            completion_date,
            matter_opened_date,
            fee_earner,
            sos_matter_id
        ))

        action = "updated"

    # Insert new matter
    

    else:

        cur.execute("""
            INSERT INTO matters (
                sos_matter_id,
                matter_status,
                client_care_issued,
                initial_documents_received,
                id_completed,
                note,
                searches_pack_copies,
                last_updated,
                mortgage_or_redemption,
                exchange_notice_toe,
                completion_date,
                matter_opened_date,
                fee_earner
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """, (
            sos_matter_id,
            matter_status,
            client_care_issued,
            initial_documents_received,
            id_completed,
            note,
            searches_pack_copies,
            last_updated,
            mortgage_or_redemption,
            exchange_notice_toe,
            completion_date,
            matter_opened_date,
            fee_earner
        ))

        action = "created"


    conn.commit()

    cur.close()

    return {
        "action": action,
        "sosMatterId": sos_matter_id
    }