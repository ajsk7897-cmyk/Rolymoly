import gspread

def test():
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key("1HI0dwaA6HJV9g--lpOpprSO_UoFhFXUleFhI4ur2-44")
    ws = sh.worksheet("users")
    
    rows = ws.get_all_values()
    found = False
    for row in rows:
        if '221' in row[2] or '0221' in row[2]:
            print("Found:", row)
            found = True
    if not found:
        print("Not found in users sheet.")

if __name__ == "__main__":
    test()
