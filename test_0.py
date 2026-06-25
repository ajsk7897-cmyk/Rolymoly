import gspread

def test():
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key("1HI0dwaA6HJV9g--lpOpprSO_UoFhFXUleFhI4ur2-44")
    ws = sh.worksheet("users")
    
    # 1. Append a test row
    print("Appending test row with '0999'...")
    ws.append_row([9999, "TestUser", "'0999", "1999-01-01", "PENDING", "Unranked", "Unranked", 0, -1, 0, 0, "2026-06-19", 0], value_input_option='USER_ENTERED')
    
    # 2. Fetch the last row using get_all_values
    rows = ws.get_all_values()
    last_row = rows[-1]
    print("Fetched last row using get_all_values():")
    print(last_row)
    
    # Clean up
    print("Deleting test row...")
    ws.delete_rows(len(rows))

if __name__ == "__main__":
    test()
