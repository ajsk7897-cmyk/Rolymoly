import gspread

def test():
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key("1HI0dwaA6HJV9g--lpOpprSO_UoFhFXUleFhI4ur2-44")
    ws = sh.worksheet("users")
    
    rows = ws.get_all_values()
    print("Users in sheet:")
    for row in rows[-5:]:  # Print last 5 rows
        print(row)

if __name__ == "__main__":
    test()
