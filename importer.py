import mysql.connector as mysql

db = mysql.connect(
    host='localhost',
    port=3306,
    user="",
    passwd="",
    database='cls',
)

equipment = ["Laptop", "Desktop", "Tablet", "Phone", "Other", "A.I.O", "Mac", "Multiple"]
booked_by = ["Neil", "Matt", "Dan"]

cursor = db.cursor()

cursor.execute("SELECT `ti_id`, `eq_id`, `bb_id`, `ast_id`, `loc_id`, `ts_id`, `ti_name`, `ti_phone_number`,"
               "`ti_email`, `ti_date`, `ti_password`, `ti_details`, `ti_quote`, `ti_charger`, `ti_case`, `ti_other`,"
               "`ti_workdone`, `ti_created`, `ti_updated`, `ti_to_do_by`, `ti_rebuild_current_os`,"
               "`ti_rebuild_wanted_os`"
               " FROM tickets WHERE `ts_id` != 6 ORDER BY `ti_id` DESC LIMIT 5")


def map_ticket(ticket):
    return {
        "id": ticket[0],
        "equipment": equipment[ticket[1]],
        "booked_by": booked_by[ticket[2]]
    }


tickets = list(map(map_ticket, cursor.fetchall()))
print(tickets)
