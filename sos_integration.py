# Import date and time
from datetime import datetime, date


# Matter type codes from SOS
MATTER_TYPES = {
    "1501": "Sale",
    "1502": "Purchase",
    "1503": "Remortgage",
    "1504": "Transfer of Equity"
}


# Maps the JSON fields received from SOS to the milestone codes
# in milestone_definitions
MILESTONE_JSON_FIELDS = {
    "idCompleted": "ID_COMPLETED",
    "clientCareIssued": "CLIENT_CARE_ISSUED",
    "initialDocumentsReceived": "INITIAL_DOCUMENTS_RECEIVED",

    "searchesOrdered": "SEARCHES_ORDERED",
    "contractPackSent": "CONTRACT_PACK_SENT",
    "officeCopiesObtained": "OFFICE_COPIES_OBTAINED",

    "mortgageOffer": "MORTGAGE_OFFER",
    "initialRedemptionStatement": "INITIAL_REDEMPTION_STATEMENT",

    "exchangeDate": "EXCHANGE_DATE",
    "notice": "NOTICE",
    "transferProduced": "TRANSFER_PRODUCED",

    "completionDate": "COMPLETION_DATE"
}


def parse_sos_date(value):
    # Convert SOS date to Python date

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()

    # Defining empty requests
    empty_values = {
        "",
        "none",
        "null",
        "0",
        "00/00/0000"
    }

    if value.lower() in empty_values:
        return None

    supported_formats = (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S"
    )

    for date_format in supported_formats:

        try:
            return datetime.strptime(
                value,
                date_format
            ).date()

        except ValueError:
            continue

    raise ValueError(
        f"Unsupported SOS date format: {value}"
    )


def process_milestones(
    cur,
    sos_matter_id,
    matter_type_name,
    data
):
    # Process milestone dates received from SOS

    for json_field, milestone_code in MILESTONE_JSON_FIELDS.items():

        # Skip fields which are not present in the JSON request
        if json_field not in data:
            continue

        # Find the matching milestone definition using both
        # the matter type and milestone code
        cur.execute("""
            SELECT milestone_definition_id
            FROM milestone_definitions
            WHERE matter_type = %s
              AND milestone_code = %s
              AND is_active = TRUE
        """, (
            matter_type_name,
            milestone_code
        ))

        milestone_definition = cur.fetchone()

        # The milestone may apply to a different matter type
        if not milestone_definition:
            continue

        milestone_definition_id = milestone_definition[0]

        # Convert the SOS milestone value into a Python date
        milestone_date = parse_sos_date(
            data.get(json_field)
        )

        # If the date has been removed from SOS,
        # remove the completed milestone from the portal
        if milestone_date is None:

            cur.execute("""
                DELETE FROM matter_milestones
                WHERE sos_matter_id = %s
                  AND milestone_definition_id = %s
            """, (
                sos_matter_id,
                milestone_definition_id
            ))

            continue

        # Insert the milestone or update its existing date
        cur.execute("""
            INSERT INTO matter_milestones (
                sos_matter_id,
                milestone_definition_id,
                milestone_date
            )
            VALUES (%s, %s, %s)

            ON CONFLICT (
                sos_matter_id,
                milestone_definition_id
            )

            DO UPDATE SET
                milestone_date = EXCLUDED.milestone_date
        """, (
            sos_matter_id,
            milestone_definition_id,
            milestone_date
        ))


def process_sos_matter(conn, data):

    cur = None

    try:
        # Validate required fields
        sos_matter_id = data.get("sosMatterId")

        if not sos_matter_id:
            raise ValueError("sosMatterId is required")

        # Extract matter-level SOS data
        status = data.get("matterStatus")
        matter_type = str(
            data.get("mattertype", "")
        ).strip()

        client_name = data.get("clientname")
        property_address = data.get("propertyaddress")

        opened_date = parse_sos_date(
            data.get("matterOpenedDate")
        )

        fee_earner = data.get("feeEarner")

        last_updated = parse_sos_date(
            data.get("lastUpdated")
        )

        # Convert the SOS matter type code to its portal name
        matter_type_name = MATTER_TYPES.get(
            matter_type
        )

        if not matter_type_name:
            raise ValueError(
                f"Unsupported matter type: {matter_type}"
            )

        # Get SOS referrer organisation reference
        org_ref = str(
            data.get("orgref", "")
        ).strip()

        if not org_ref:
            raise ValueError("orgref is required")

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
                "No organisation found for SOS referrer "
                "reference: {}".format(org_ref)
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
                    property_address,
                    matter_type,
                    status,
                    opened_date,
                    fee_earner,
                    last_updated
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
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


        # Create, update or remove the matter milestones
        process_milestones(
            cur=cur,
            sos_matter_id=sos_matter_id,
            matter_type_name=matter_type_name,
            data=data
        )

        # Commit the matter and milestone changes together
        conn.commit()

        return {
            "action": action,
            "sosMatterId": sos_matter_id
        }

    except Exception:

        # Roll back the matter and milestone changes if anything fails
        conn.rollback()
        raise

    finally:

        if cur:
            cur.close()