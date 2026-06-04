#!/usr/bin/env python3
"""
Diablo Predictor Hybrid 4.7 – Telegram Auto-Sender Edition
- Ensemble of 7 prediction strategies
- Dynamic weighting & loss recovery
- Pattern memory (last 3 results -> next)
- Enhanced UI with confidence & streak
- JSON persistence: pattern DB & weights survive restarts
- Telegram auto-sender for predictions & results
"""

import os, sys, time, subprocess, importlib, random, statistics, json
from collections import defaultdict, deque

# -------------------- Auto-install & import --------------------
def install_and_import(package, pip_name=None):
    pip_name = pip_name or package
    try:
        return importlib.import_module(package)
    except ImportError:
        print(f"📦 Installing missing package: {pip_name} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
        return importlib.import_module(package)

requests = install_and_import("requests")
colorama = install_and_import("colorama")
from colorama import Fore, Style, init
init(autoreset=True)

# -------------------- Telegram Configuration --------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8872338458:AAGcXa7UARS3IKexEpicdYts98QcAItFKrg")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "-1003326088861")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# -------------------- Configuration --------------------
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json?ts={}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 10)", "Referer": "https://hgnice.biz"}
STATE_FILE = "diablo_state.json"

CYAN = Fore.CYAN
RED = Fore.RED
GREEN = Fore.GREEN
YELLOW = Fore.YELLOW
MAGENTA = Fore.MAGENTA
RESET = Style.RESET_ALL
BOLD = Style.BRIGHT

# -------------------- Telegram Sender --------------------
def send_telegram(text):
    """Send a message to the configured Telegram channel."""
    try:
        payload = {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        resp = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            print(f"{GREEN}📨 Telegram: message sent{RESET}")
        else:
            print(f"{RED}📨 Telegram: failed – {resp.text[:120]}{RESET}")
    except Exception as e:
        print(f"{RED}📨 Telegram error: {e}{RESET}")

def send_prediction_telegram(period, prediction):
    """Send prediction in the specified format."""
    message = f"Period: [{period}] | Prediction: [{prediction}]"
    send_telegram(message)

def send_result_telegram(period, status):
    """Send result in the specified format."""
    message = f"Period: [{period}] | Result: [{status}]"
    send_telegram(message)

# -------------------- Helper: Big/Small --------------------
def big_small(num):
    try:
        return "BIG" if int(num) >= 5 else "SMALL"
    except:
        return "Unknown"

# -------------------- Pattern Memory (with persistence support) --------------------
class PatternMemory:
    """Stores patterns of last 3 results and the next outcome."""
    def __init__(self, depth=3):
        self.depth = depth
        self.db = defaultdict(lambda: {"BIG": 0, "SMALL": 0})

    def update(self, history):
        if len(history) < self.depth + 1:
            return
        key = tuple(history[-(self.depth+1):-1])
        next_val = history[-1]
        self.db[key][next_val] += 1

    def predict(self, recent):
        if len(recent) < self.depth:
            return None, 0.0
        key = tuple(recent[-self.depth:])
        counts = self.db.get(key)
        if not counts or sum(counts.values()) == 0:
            return None, 0.0
        total = sum(counts.values())
        best = max(counts, key=counts.get)
        confidence = counts[best] / total
        return best, confidence

    def to_dict(self):
        return {"depth": self.depth,
                "db": {",".join(k): v for k, v in self.db.items()}}

    @classmethod
    def from_dict(cls, d):
        obj = cls(depth=d.get("depth", 3))
        for k_str, counts in d.get("db", {}).items():
            obj.db[tuple(k_str.split(","))] = counts
        return obj

# -------------------- Master Methods --------------------
def master_methods(period_int, last_ints):
    methods = {}
    n = period_int
    lst = last_ints if last_ints else [0]

    # Method 1
    base = ((n * 73) - (n % 43)) % 10
    hist_factor = sum(lst) % 10
    math_mod = (n ** 2) % 9
    stat_mean = int(statistics.mean(lst[-5:])) % 10 if len(lst) >= 5 else 0
    m1 = (base + hist_factor + math_mod + stat_mean) % 10
    methods["M1"] = "BIG" if m1 >= 5 else "SMALL"

    # Method 2
    shift = (n % 7) + (len(lst) % 3)
    trend_factor = (sum(lst[-3:]) if len(lst) >= 3 else sum(lst)) % 10
    m2 = (n + shift + trend_factor) % 10
    methods["M2"] = "BIG" if m2 >= 5 else "SMALL"

    # Method 3
    mirror = int(str(n)[::-1]) % 10 if len(str(n)) > 1 else n % 10
    rev_factor = (mirror + (sum(lst[-4:]) if len(lst) >= 4 else 0)) % 10
    m3 = (rev_factor * 3 + n) % 10
    methods["M3"] = "BIG" if m3 >= 5 else "SMALL"

    # Method 4
    weights = [0.2, 0.15, 0.25, 0.1, 0.3]
    if len(lst) >= 5:
        weighted_sum = sum(int(x) * w for x, w in zip(lst[-5:], weights))
    else:
        weighted_sum = sum(lst) * 0.5
    m4 = int(weighted_sum + n % 5) % 10
    methods["M4"] = "BIG" if m4 >= 5 else "SMALL"

    # Method 5
    avg_last = int(statistics.mean(lst)) % 10 if lst else 0
    chaos = (n * 97 + sum(lst) * 31) % 10
    m5 = (avg_last + chaos + n) % 10
    methods["M5"] = "BIG" if m5 >= 5 else "SMALL"

    return methods

# -------------------- Stable Logic --------------------
def stable_logic(period_number, last_results):
    recent = last_results[-10:]
    if not recent:
        return random.choice(["BIG", "SMALL"])
    labeled = [big_small(r) for r in recent]
    big_c = labeled.count("BIG")
    small_c = labeled.count("SMALL")
    if big_c > small_c:
        hist_pred = "BIG"
    elif small_c > big_c:
        hist_pred = "SMALL"
    else:
        hist_pred = "BIG" if int(period_number[-1]) >= 5 else "SMALL"

    last3_period = int(period_number[-3:])
    digit_sum = sum(int(d) for d in str(last3_period))
    period_pred = "BIG" if digit_sum % 2 == 0 else "SMALL"

    if hist_pred == period_pred:
        base = "SMALL" if hist_pred == "BIG" else "BIG"
    else:
        base = hist_pred
    return base

# -------------------- Core Predictor 4.7 --------------------
class Hybrid47:
    def __init__(self):
        self.history_nums = []
        self.history_labels = []
        self.pattern_memory = PatternMemory(depth=3)

        self.weights = {
            "M1": 1.0, "M2": 1.0, "M3": 1.0, "M4": 1.0, "M5": 1.0,
            "Stable": 1.0, "Pattern": 1.0, "Random": 1.0
        }

        self.last_predictions = {}
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.method_accuracy = defaultdict(list)

    def save_state(self, filename=STATE_FILE):
        try:
            state = {
                "pattern_memory": self.pattern_memory.to_dict(),
                "weights": self.weights,
                "consecutive_losses": self.consecutive_losses
            }
            with open(filename, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"{RED}⚠️  Could not save state: {e}{RESET}")

    def load_state(self, filename=STATE_FILE):
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, "r") as f:
                state = json.load(f)
            if "pattern_memory" in state:
                self.pattern_memory = PatternMemory.from_dict(state["pattern_memory"])
            if "weights" in state:
                for k in self.weights:
                    self.weights[k] = state["weights"].get(k, 1.0)
            if "consecutive_losses" in state:
                self.consecutive_losses = state.get("consecutive_losses", 0)
            print(f"{GREEN}📂 State loaded from {filename}{RESET}")
            return True
        except Exception as e:
            print(f"{RED}⚠️  Could not load state (starting fresh): {e}{RESET}")
            return False

    def add_result(self, number, period):
        num = int(number)
        label = big_small(num)
        self.history_nums.append(num)
        self.history_labels.append(label)

        self.pattern_memory.update(self.history_labels)

        if self.last_predictions:
            correct_methods = []
            for method, pred in self.last_predictions.items():
                if pred == label:
                    self.method_accuracy[method].append(1)
                    correct_methods.append(method)
                else:
                    self.method_accuracy[method].append(0)
            for m in self.weights:
                recent = self.method_accuracy[m][-10:] if m in self.method_accuracy else []
                if recent:
                    acc = sum(recent) / len(recent)
                    self.weights[m] = 0.5 + acc * 0.5
                else:
                    self.weights[m] = 0.7

            if correct_methods:
                self.consecutive_wins += 1
                self.consecutive_losses = 0
            else:
                self.consecutive_losses += 1
                self.consecutive_wins = 0

            self.last_predictions = {}

        if len(self.history_nums) > 100:
            self.history_nums.pop(0)
            self.history_labels.pop(0)

        self.save_state()

    def predict(self, period_str):
        period_int = int(period_str)
        last_ints = self.history_nums[:]

        master_preds = master_methods(period_int, last_ints)
        stable_pred = stable_logic(period_str, [str(x) for x in last_ints])

        pattern_pred, pattern_conf = self.pattern_memory.predict(self.history_labels)
        if pattern_pred is None:
            pattern_pred = random.choice(["BIG", "SMALL"])
            pattern_conf = 0.0

        random_pred = random.choice(["BIG", "SMALL"])

        all_preds = {
            **master_preds,
            "Stable": stable_pred,
            "Pattern": pattern_pred,
            "Random": random_pred
        }

        vote = {"BIG": 0.0, "SMALL": 0.0}
        method_vote_details = {}
        for method, pred in all_preds.items():
            w = self.weights.get(method, 0.7)
            vote[pred] += w
            method_vote_details[method] = (pred, w)

        if self.consecutive_losses >= 3:
            predicted = "BIG" if vote["BIG"] > vote["SMALL"] else "SMALL"
            final = "SMALL" if predicted == "BIG" else "BIG"
            confidence = abs(vote["BIG"] - vote["SMALL"]) / (vote["BIG"] + vote["SMALL"])
            recovery = True
        else:
            final = "BIG" if vote["BIG"] > vote["SMALL"] else "SMALL"
            confidence = abs(vote["BIG"] - vote["SMALL"]) / (vote["BIG"] + vote["SMALL"])
            recovery = False

        if self.consecutive_losses >= 5:
            for m in self.weights:
                self.weights[m] = 1.0
            self.consecutive_losses = 0

        self.last_predictions = all_preds

        return final, confidence, method_vote_details, recovery

# -------------------- UI Helpers --------------------
def header():
    print(f"\n{CYAN}{BOLD}⚔️  DIABLO PREDICTOR 4.7 · TELEGRAM AUTO-SENDER ⚔️{RESET}")
    print(f"{CYAN}◆{'═'*40}◆{RESET}")

def show_prediction(period, prediction, confidence, method_details, recovery):
    print(f"\n{CYAN}🎯 Period{RESET} ➜ {RED}{period}{RESET}")
    print(f"{CYAN}🔮 Prediction{RESET} ➜ {GREEN if prediction=='BIG' else YELLOW}{prediction}{RESET}  "
          f"{CYAN}Confidence:{RESET} {BOLD}{confidence:.0%}{RESET}")
    if recovery:
        print(f"{MAGENTA}⚠️  LOSS STREAK RECOVERY – inverted prediction{RESET}")
    sorted_methods = sorted(method_details.items(), key=lambda x: x[1][1], reverse=True)
    print(f"{CYAN}📊 Method influence (top 5):{RESET}")
    for i, (method, (pred, w)) in enumerate(sorted_methods[:5], 1):
        color = GREEN if pred == prediction else RED
        print(f"   {i}. {method}: {color}{pred}{RESET} (weight {w:.2f})")

def show_result(actual, prediction, correct, streak_wins, streak_losses):
    status = f"{GREEN}✅ VICTORY{RESET}" if correct else f"{RED}❌ DEFEAT{RESET}"
    emoji = "🏆" if correct else "💀"
    print(f"\n{CYAN}🎲 Actual{RESET} ➜ {YELLOW}{actual}{RESET} | {status} {emoji}")
    if streak_wins > 0:
        print(f"{GREEN}🔥 Win streak: {streak_wins}{RESET}")
    if streak_losses > 0:
        print(f"{RED}🌊 Loss streak: {streak_losses}{RESET}")
    print(f"{CYAN}{'◆'*42}{RESET}")

def show_history_table(history, last_n=5):
    print(f"\n{CYAN}📜 Recent performance:{RESET}")
    print(f"{CYAN}{'Period':<14} {'Pred.':<8} {'Result':<8} {'Status':<12}{RESET}")
    for entry in history[-last_n:]:
        p = entry['period']
        pred = entry['predict']
        res = big_small(entry['result']) if entry['result'] else "?"
        status = "WIN" if entry['status'] == "WIN" else "LOSS"
        color = GREEN if status == "WIN" else RED
        print(f"{p:<14} {pred:<8} {res:<8} {color}{status:<12}{RESET}")

# -------------------- Data Fetching --------------------
def fetch_data():
    try:
        ts = int(time.time() * 1000)
        url = API_URL.format(ts)
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        result = response.json()
        if 'data' in result and 'list' in result['data']:
            formatted = []
            for item in result['data']['list']:
                formatted.append({
                    "issueNumber": item.get("issueNumber"),
                    "number": item.get("number")
                })
            return formatted
    except Exception as e:
        print(f"{CYAN}⚠️  Fetch error: {e}{RESET}")
    return []

# -------------------- Main Loop --------------------
def run():
    predictor = Hybrid47()
    predictor.load_state()

    seen_periods = set()
    prediction_info = None
    history_log = []

    header()
    print(f"{CYAN}Initialising persistent ensemble with Telegram auto-sender...{RESET}")
    print(f"{CYAN}📨 Telegram channel: {TELEGRAM_CHANNEL_ID}{RESET}")
    time.sleep(1.5)

    while True:
        data = fetch_data()
        if not data:
            time.sleep(3)
            continue

        latest = data[0]
        curr_period = latest.get("issueNumber", "")
        curr_number = latest.get("number", "")

        if curr_number and curr_period not in seen_periods:
            predictor.add_result(curr_number, curr_period)
            seen_periods.add(curr_period)

        # Check if a pending prediction matches this period
        if prediction_info and prediction_info["period"] == curr_period:
            actual_label = big_small(curr_number)
            correct = prediction_info["prediction"] == actual_label
            status = "WIN" if correct else "LOSS"
            history_log.append({
                "period": curr_period,
                "predict": prediction_info["prediction"],
                "result": curr_number,
                "status": status
            })
            show_result(actual_label, prediction_info["prediction"], correct,
                        predictor.consecutive_wins, predictor.consecutive_losses)
            # 📨 Send result to Telegram
            send_result_telegram(curr_period, status)
            show_history_table(history_log)
            prediction_info = None

        # Make a new prediction for the next period
        if not prediction_info and curr_period.isdigit():
            next_period = str(int(curr_period) + 1)
            if next_period not in seen_periods:
                pred, conf, details, recovery = predictor.predict(next_period)
                prediction_info = {
                    "period": next_period,
                    "prediction": pred,
                    "confidence": conf,
                    "details": details,
                    "recovery": recovery
                }
                show_prediction(next_period[-5:], pred, conf, details, recovery)
                # 📨 Send prediction to Telegram
                send_prediction_telegram(next_period, pred)

        time.sleep(3)

if __name__ == "__main__":
    run()
