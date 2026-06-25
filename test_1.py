import pandas as pd

approved_users = [
    (1, "Hide on bush", "0221", "Unranked", "Unranked", 100, -1, 0, 0, 0),
    (2, "TestUser", "0999", "Unranked", "Unranked", 100, -1, 0, 0, 0),
]

df = pd.DataFrame(approved_users, columns=['ID', 'Riot ID', 'Tag Line', '솔로랭크', '자유랭크', 'Power Score', 'Manual Score', 'Manual Stars', 'is_admin', 'Match Bonus'])

print(df['Tag Line'].tolist())
