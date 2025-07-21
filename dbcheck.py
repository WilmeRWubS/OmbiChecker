import sqlite3
from datetime import datetime

def connect_db(db_path="ombi.db"):
    return sqlite3.connect(db_path)

def get_pending_requests(conn):
    cursor = conn.cursor()

    # Haal gebruikers op
    cursor.execute("SELECT Id, UserName FROM AspNetUsers")
    user_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT Title, ReleaseDate, Status, RequestedDate, RequestedUserId, Approved, Available
        FROM MovieRequests
        WHERE Approved = 0 AND (Available = 0 OR Available IS NULL)
        ORDER BY ReleaseDate ASC
    """)

    output = []
    for title, release, status, req_date, user_id, approved, available in cursor.fetchall():
        username = user_map.get(user_id, "Onbekend")

        # Status vertaling
        status_nl = {
            "Released": "Uitgebracht",
            "Post Production": "Postproductie"
        }.get(status, status)

        # Format release
        if release and "0001" not in release:
            try:
                release_fmt = datetime.strptime(release.split(" ")[0], "%Y-%m-%d").strftime("(%m/%d/%Y)")
            except:
                release_fmt = "(?)"
        else:
            release_fmt = "(?)"

        # Format aanvraagdatum
        if req_date and "0001" not in req_date:
            try:
                req_fmt = datetime.strptime(req_date.split(" ")[0], "%Y-%m-%d").strftime("%b %d, %Y")
            except:
                req_fmt = "-"
        else:
            req_fmt = "-"

        output.append(f"{title} {release_fmt}\t{username}\t{status_nl}\tWacht op goedkeuring\t{req_fmt}")

    return output

def main():
    conn = connect_db()
    results = get_pending_requests(conn)
    conn.close()

    if not results:
        print("Geen nog te verwerken filmverzoeken gevonden.")
    else:
        for row in results:
            print(row)

if __name__ == "__main__":
    main()
