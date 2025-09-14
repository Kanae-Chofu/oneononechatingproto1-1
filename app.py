import streamlit as st
import sqlite3
import bcrypt
from streamlit_autorefresh import st_autorefresh

# 🌙 ダークモード固定＋背景色変更
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    div[data-testid="stHeader"] {
        background-color: #000000;
    }
    div[data-testid="stToolbar"] {
        display: none;
    }
    input, textarea {
        background-color: #1F2F54 !important;
        color: #FFFFFF !important;
    }
    button {
        background-color: #426AB3 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
    c.execute('''CREATE TABLE IF NOT EXISTS friends (
                    user TEXT,
                    friend TEXT,
                    UNIQUE(user, friend))''')
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

# 友達追加
def add_friend(user, friend):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO friends (user, friend) VALUES (?, ?)", (user, friend))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# 友達一覧取得
def get_friends(user):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT friend FROM friends WHERE user = ?", (user,))
    friends = [row[0] for row in c.fetchall()]
    conn.close()
    return friends


# --- 📊 会話フィードバック機能 ---
def calc_feedback_percentages(messages, current_user):
    if not messages:
        return {}

    # 自分の発言だけ抽出
    user_msgs = [m for s, m, _ in messages if s == current_user]
    total = len(user_msgs)
    if total == 0:
        return {}

    avg_len = sum(len(m) for m in user_msgs) / total
    short_rate = sum(1 for m in user_msgs if len(m) <= 10) / total * 100
    question_rate = sum(1 for m in user_msgs if "?" in m or "？" in m) / total * 100

    positive_words = ["楽しい", "うれしい", "いいね", "すごい", "ありがとう"]
    pos_rate = sum(1 for m in user_msgs if any(w in m for w in positive_words)) / total * 100

    negative_words = ["疲れた", "無理", "いやだ", "嫌い", "最悪"]
    neg_rate = sum(1 for m in user_msgs if any(w in m for w in negative_words)) / total * 100

    return {
        "平均文字数": round(avg_len, 1),
        "短文率": round(short_rate, 1),
        "質問率": round(question_rate, 1),
        "ポジティブ語率": round(pos_rate, 1),
        "ネガティブ語率": round(neg_rate, 1),
    }


# Streamlit UI
st.set_page_config(page_title="チャットSNSメビウス", layout="centered")
st.title("1対1チャットSNSメビウス（α版）")

st_autorefresh(interval=5000, key="chat_autorefresh")

# セッション管理
if "username" not in st.session_state:
    st.session_state.username = None
if "partner" not in st.session_state:
    st.session_state.partner = None

# メニュー選択
menu = st.radio("操作を選択してください", ["新規登録", "ログイン"], horizontal=True)

# 新規登録
if menu == "新規登録":
    st.subheader("🆕 新規登録")
    new_user = st.text_input("ユーザー名を入力")
    new_pass = st.text_input("パスワードを入力", type="password")
    if st.button("登録", use_container_width=True):
        if register_user(new_user, new_pass):
            st.success("登録成功！ログインしてください")
        else:
            st.error("このユーザー名は既に使われています")

# ログイン
elif menu == "ログイン":
    st.subheader("🔐 ログイン")
    user = st.text_input("ユーザー名")
    pw = st.text_input("パスワード", type="password")
    if st.button("ログイン", use_container_width=True):
        if login_user(user, pw):
            st.session_state.username = user
            st.success(f"{user} でログインしました！")
        else:
            st.error("ユーザー名かパスワードが違います")

# チャット画面
if st.session_state.username:
    st.divider()
    st.subheader("💬 チャット画面")
    st.write(f"ログイン中ユーザー: `{st.session_state.username}`")

    # 👥 友達一覧表示（折りたたみ式）
    with st.expander("👥 友達一覧を表示／非表示", expanded=True):
        friends = get_friends(st.session_state.username)
        if friends:
            for f in friends:
                st.markdown(f"- `{f}`")
        else:
            st.info("まだ友達はいません。ユーザー名を入力して友達追加してください。")

    # ✍️ チャット相手の手動入力
    partner = st.text_input("チャット相手のユーザー名を入力", st.session_state.partner or "")
    if partner:
        st.session_state.partner = partner
        st.write(f"チャット相手: `{partner}`")

        # ➕ 友達追加ボタン
        if st.button("このユーザーを友達に追加", use_container_width=True):
            if add_friend(st.session_state.username, partner):
                st.success(f"{partner} を友達に追加しました！")
            else:
                st.info(f"{partner} はすでに友達に追加されています")

    # 💬 メッセージ表示（左右揃え）
    if st.session_state.partner:
        messages = get_messages(st.session_state.username, st.session_state.partner)
        for sender, msg, _ in messages:
            if sender == st.session_state.username:
                st.markdown(
                    f"""
                    <div style='text-align: right; margin: 5px 0;'>
                        <span style='background-color:#1F2F54; color:#FFFFFF; padding:8px 12px; border-radius:10px; display:inline-block; max-width:80%;'>
                            {msg}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style='text-align: left; margin: 5px 0;'>
                        <span style='background-color:#426AB3; color:#FFFFFF; padding:8px 12px; border-radius:10px; display:inline-block; max-width:80%; border:1px solid #ccc;'>
                            {msg}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ✉️ メッセージ送信
        new_message = st.chat_input("メッセージを入力")
        if new_message:
            save_message(st.session_state.username, st.session_state.partner, new_message)
            st.rerun()

        # 📊 フィードバック表示
        if st.button("📊 この会話の統計を見る", use_container_width=True):
            stats = calc_feedback_percentages(messages, st.session_state.username)
            if stats:
                st.subheader("📊 会話フィードバック（自分の発言のみ）")
                for k, v in stats.items():
                    if k == "平均文字数":
                        st.write(f"{k}: {v}")
                    else:
                        st.write(f"{k}: {v}%")
            else:
                st.info("まだ自分の発言がありません。")
