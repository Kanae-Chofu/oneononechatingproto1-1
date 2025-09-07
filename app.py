# app.py
import streamlit as st
import sqlite3
import datetime
import bcrypt

DB_FILE = "chat.db"

# --- DB 初期化 ---
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash BLOB
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            recipient TEXT,
            content TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- ユーザー操作 ---
def create_user(username, password):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    pw_hash = row[0]
    return bcrypt.checkpw(password.encode(), pw_hash)

def list_users(exclude=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if exclude:
        c.execute("SELECT username FROM users WHERE username != ? ORDER BY username", (exclude,))
    else:
        c.execute("SELECT username FROM users ORDER BY username")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

# --- メッセージ操作 ---
def save_message(sender, recipient, content):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, recipient, content, timestamp) VALUES (?, ?, ?, ?)",
              (sender, recipient, content, ts))
    conn.commit()
    conn.close()

def load_conversation(user_a, user_b, limit=200):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # user_a↔user_b のやりとりを取得（古い→新しい）
    c.execute("""
        SELECT sender, recipient, content, timestamp
        FROM messages
        WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)
        ORDER BY id ASC
        LIMIT ?
    """, (user_a, user_b, user_b, user_a, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# --- UI ---
def main():
    st.set_page_config(page_title="簡易 1対1 SNS デモ", layout="centered")
    st.title("簡易 1対1 SNS（デモ）")

    if "user" not in st.session_state:
        st.session_state.user = None
    if "chat_with" not in st.session_state:
        st.session_state.chat_with = None

    # --- ログイン / 新規登録 ---
    if st.session_state.user is None:
        st.subheader("ログイン")
        col1, col2 = st.columns([2,3])
        with col1:
            login_user = st.text_input("ユーザー名", key="login_user")
        with col2:
            login_pass = st.text_input("パスワード", type="password", key="login_pass")
        if st.button("ログイン"):
            if check_user(login_user, login_pass):
                st.session_state.user = login_user
                st.success(f"{login_user} でログインしました。")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが違います")

        st.markdown("---")
        st.subheader("新規登録")
        new_user = st.text_input("新しいユーザー名", key="reg_user")
        new_pass = st.text_input("新しいパスワード", type="password", key="reg_pass")
        if st.button("登録"):
            if not new_user or not new_pass:
                st.error("ユーザー名・パスワードを入力してください。")
            else:
                ok = create_user(new_user, new_pass)
                if ok:
                    st.success("登録成功。ログインしてみてください。")
                else:
                    st.error("そのユーザー名は既に存在します。")
        return

    # --- ログアウトボタン ---
    if st.button("ログアウト"):
        st.session_state.user = None
        st.session_state.chat_with = None
        st.rerun()

    st.write(f"ログイン中: **{st.session_state.user}**")
    st.markdown("---")

    # --- 相手を選ぶ（ユーザー一覧） ---
    st.subheader("チャットする相手を選ぶ")
    users = list_users(exclude=st.session_state.user)
    if not users:
        st.info("他のユーザーがいません。誰かを登録してから試してください。")
    else:
        choice = st.selectbox("相手を選択", ["-- 選択 --"] + users, key="select_peer")
        if choice != "-- 選択 --":
            st.session_state.chat_with = choice

    # --- 直接ユーザー名を入力してチャット開始も可能 ---
    new_peer = st.text_input("相手のユーザー名を直接入力して開始（既存ユーザー名）", key="direct_peer")
    if st.button("直接開始"):
        if new_peer and new_peer in users:
            st.session_state.chat_with = new_peer
        else:
            st.error("そのユーザーは存在しません（または自分の名前です）。")

    st.markdown("---")

    # --- チャット表示エリア ---
    if st.session_state.chat_with:
        peer = st.session_state.chat_with
        st.subheader(f"チャット: {peer}  (1対1)")
        conv = load_conversation(st.session_state.user, peer)

        # 表示（上が古い、下が新しい） — スタイルを簡単に
        for sender, recipient, content, ts in conv:
            if sender == st.session_state.user:
                st.markdown(f"<div style='text-align: right; background:#e6ffe6; padding:6px; border-radius:6px; margin:6px 0'>{content}<div style='font-size:10px; color:#666'>{ts}</div></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align: left; background:#f0f0f0; padding:6px; border-radius:6px; margin:6px 0'>{content}<div style='font-size:10px; color:#666'>{ts}</div></div>", unsafe_allow_html=True)

        st.markdown("---")
        # 送信フォーム（Enterでも、ボタンでもOK）をフォームで作ると扱いやすい
        with st.form(key="send_form", clear_on_submit=True):
            text = st.text_input("メッセージを入力（Enterで送信）", max_chars=500, key="message_input")
            submitted = st.form_submit_button("送信")
            if submitted and text:
                save_message(st.session_state.user, peer, text)
                st.rerun()

    else:
        st.info("チャットする相手を選んでください。")

if __name__ == "__main__":
    init_db()
    main()
