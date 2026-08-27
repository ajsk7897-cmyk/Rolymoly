import json
import os
import tempfile
import time

STATE_FILE = "shared_auction_state.json"

def load_auction_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None

def save_auction_state(state):
    # Atomic write to prevent concurrent write issues
    # Create temp file in the same directory to ensure atomic replace works
    dir_name = os.path.dirname(os.path.abspath(STATE_FILE)) if os.path.dirname(os.path.abspath(STATE_FILE)) else "."
    fd, temp_path = tempfile.mkstemp(dir=dir_name)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, STATE_FILE)

def clear_auction_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def update_bid(team_idx, bid_points):
    state = load_auction_state()
    if state and state.get('auction_phase') == 'BIDDING':
        if 'current_bids' not in state:
            state['current_bids'] = {}
            
        # 현재 최고가 확인
        valid_bids = [b['amount'] for b in state['current_bids'].values() if b['status'] == 'BID']
        max_bid = max(valid_bids) if valid_bids else 0
            
        state['current_bids'][str(team_idx)] = {
            'status': 'BID',
            'amount': bid_points,
            'time': time.time()
        }
        
        # 새로운 최고가일 경우 타이머 연장
        extend_time = state.get('extend_time', 0)
        if bid_points > max_bid and extend_time > 0:
            current_time = time.time()
            new_end = current_time + extend_time
            if new_end > state.get('bid_end_time', 0):
                state['bid_end_time'] = new_end
                
        save_auction_state(state)

def update_pass(team_idx):
    state = load_auction_state()
    if state and state.get('auction_phase') == 'BIDDING':
        if 'current_bids' not in state:
            state['current_bids'] = {}
        state['current_bids'][str(team_idx)] = {
            'status': 'PASS',
            'amount': 0,
            'time': time.time()
        }
        save_auction_state(state)
