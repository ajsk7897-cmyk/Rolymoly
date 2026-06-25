import database
import json

def check():
    sh = database.get_sheet()
    ws = sh.worksheet("users")
    raw = ws.get_all_values()
    print("RAW VALUES FROM SHEET:")
    for row in raw:
        print(row)
    
    print("\nRECORDS WITH NUMERICISE IGNORE:")
    records = ws.get_all_records(numericise_ignore=['tag_line', 'birthdate'])
    for r in records:
        print(r)

if __name__ == "__main__":
    check()
