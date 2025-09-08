import streamlit as st
import sqlite3
import bcrypt
from streamlit_autorefresh import st_autorefresh

# データベース初期化
def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT,
                    receiver TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# ユーザー登録
def register_user(username, password):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ログイン
def login_user(username, password):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(password.encode(), result[0]):
        return True
    return False

# メッセージ保存
def save_message(sender, receiver, message):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)", (sender, receiver, message))
    conn.commit()
    conn.close()

# メッセージ取得
def get_messages(user, partner):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute('''SELECT sender, message, timestamp FROM messages 
                 WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) 
                 ORDER BY timestamp''',
              (user, partner, partner, user))
    messages = c.fetchall()
    conn.close()
    return messages

# ---------------- Streamlit UI ----------------

st.title("1対1チャットSNS (β版)")

# 🔄 5秒ごとに自動更新
st_autorefresh(interval=5000, key="chat_autorefresh")

# セッション管理
if "username" not in st.session_state:
    st.session_state.username = None
if "partner" not in st.session_state:
    st.session_state.partner = None

menu = ["ログイン", "新規登録"]
choice = st.sidebar.selectbox("メニュー", menu)

# 新規登録
if choice == "新規登録":
    st.subheader("新規登録")
    new_user = st.text_input("ユーザー名")
    new_pass = st.text_input("パスワード", type="password")
    if st.button("登録"):
        if register_user(new_user, new_pass):
            st.success("登録成功！ログインしてください")
        else:
            st.error("このユーザー名は既に使われています")

# ログイン
elif choice == "ログイン":
    st.subheader("ログイン")
    user = st.text_input("ユーザー名")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if login_user(user, pw):
            st.session_state.username = user
            st.success(f"{user} でログインしました！")
        else:
            st.error("ユーザー名かパスワードが違います")

# チャット画面
if st.session_state.username:
    st.sidebar.write(f"ログイン中: {st.session_state.username}")
    partner = st.sidebar.text_input("チャット相手のユーザー名を入力", st.session_state.partner or "")
    if partner:
        st.session_state.partner = partner
        st.subheader(f" {st.session_state.username} ⇔ {partner} のチャット")

        # メッセージ表示
        messages = get_messages(st.session_state.username, partner)
        for sender, msg, ts in messages:
            if sender == st.session_state.username:
                st.write(f"**あなた** ({ts}): {msg}")
            else:
                st.write(f"**{sender}** ({ts}): {msg}")

        # メッセージ送信
        new_message = st.text_input("メッセージを入力")
        if st.button("送信"):
            if new_message.strip():
                save_message(st.session_state.username, partner, new_message)
                st.rerun()
