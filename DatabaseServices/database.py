import bcrypt
import json
import sqlite3
from UserInfo import userInfo


# Veritabanını oluşturma fonksiyonu
def setup_database():
    """ Veritabanını oluşturur ve 'users' tablosunu ekler. """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        conversation_history TEXT DEFAULT '{}',
        session_count INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()
    print("📂 Veritabanı başarıyla başlatıldı.")


# Kullanıcı ekleme fonksiyonu (JSON destekli)
def create_user(username, password):
    print(username, password, "hello")
    """ Kullanıcıyı veritabanına ekler, boş bir sohbet geçmişi ile başlatır. """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Şifreyi hashleyerek sakla
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    # Hata almamak için: Bytes verisini UTF-8 string'e çevir
    hashed_password_str = hashed_password.decode('utf-8')

    # Boş bir sözlük olarak conversation_history başlat
    empty_conversation = json.dumps({})  # "{}" şeklinde saklanacak
    print("cursor printed", cursor)

    try:
        cursor.execute("INSERT INTO users (username, password, conversation_history) VALUES (?, ?, ?)",
                       (username, hashed_password_str, empty_conversation))
        conn.commit()
        print(f"✅ Kullanıcı '{username}' başarıyla eklendi.")
        conn.close()
        return [True, f"✅ Kullanıcı Başarıyla eklendi. Hoş geldin, {username}!"]
    except sqlite3.IntegrityError:
        print("⚠️ Hata: Bu kullanıcı adı zaten mevcut!")
        conn.close()
        return [False, "⚠️ Hata: Bu kullanıcı adı zaten mevcut!"]
    except Exception as e:
        print(f"❌ Hata: {e}")
        conn.close()
        return [False, f"❌ Hata: {e}"]


def check_user(username, password):
    """ Kullanıcının giriş yapmasını kontrol eder. """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Kullanıcıyı veritabanında ara
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    if result:
        hashed_password = result[0]  # Veritabanındaki hashlenmiş şifre

        # Eğer hashed_password string olarak kaydedildiyse, bytes formatına çevir
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')

        # Girilen şifreyi hashlenmiş şifre ile karşılaştır
        if bcrypt.checkpw(password.encode(), hashed_password):
            print(f"✅ Giriş başarılı: Hoş geldin, {username}!")
            cursor.execute("SELECT session_count FROM users WHERE username = ?", (username,))
            session_count = cursor.fetchone()
            if session_count:
                session_count = session_count[0]
                userInfo.set_user_session(session_count)
            conn.close()
            return [True, f"✅ Giriş başarılı: Hoş geldin, {username}!"]
        else:
            print("❌ Hata: Yanlış şifre!")
            conn.close()
            return [False, "❌ Hata: Yanlış şifre!"]
    else:
        print("⚠️ Hata: Kullanıcı bulunamadı!")
        conn.close()
        return [False, "⚠️ Hata: Kullanıcı bulunamadı!"]


def update_conversation(question, answer):
    """ Kullanıcının sohbet geçmişine yeni bir soru ve cevap ekler. """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    username = userInfo.get_user()
    # Kullanıcının mevcut sohbet geçmişini al
    cursor.execute("SELECT conversation_history FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    if result:
        conversation_history_text = result[0]

        # Eğer sohbet geçmişi boşsa, yeni bir sözlük başlat
        if conversation_history_text is None or conversation_history_text.strip() == "":
            conversation_history = {}
        else:
            conversation_history = json.loads(conversation_history_text)  # JSON formatına çevir

        # Yeni mesajın ID'sini belirle
        message_id = len(conversation_history) + 1
        current_session = userInfo.get_active_session()
        # Yeni soru-cevap çiftini ekle
        conversation_history[message_id] = {
            "session_id": current_session,
            "question": question,
            "answer": answer
        }

        # Güncellenmiş JSON'u tekrar veritabanına kaydet
        cursor.execute("UPDATE users SET conversation_history = ? WHERE username = ?",
                       (json.dumps(conversation_history), username))
        conn.commit()
        print(f"💬 '{username}' kullanıcısının sohbet geçmişi güncellendi.")
    else:
        print("⚠️ Kullanıcı bulunamadı!")

    conn.close()


def get_conversation_history(limit):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    conversation_history = None
    # Kullanıcı adı verildiğinde ilgili konuşma geçmişini al
    username = userInfo.get_user()  # Burada istediğin kullanıcı adını belirtebilirsin
    cursor.execute("""
        SELECT conversation_history 
        FROM users 
        WHERE username = ?
    """, (username,))
    conversation_history_json = cursor.fetchone()
    if conversation_history_json:
        # JSON verisini yükle
        conversation_history = json.loads(conversation_history_json[0])  # conversation_history sütunu JSON verisi

        # JSON verisinde son 5 konuşmayı almak
        conversation_history = list(conversation_history.values())[-limit:]

    if not conversation_history_json:
        conversation_history = []

    conn.close()
    return conversation_history

def get_unique_sessions():
    conn=sqlite3.connect('users.db')
    cur=conn.cursor()
    username = userInfo.get_user()
    cur.execute("SELECT conversation_history FROM users WHERE username=?", (username,))
    row=cur.fetchone()
    conn.close()
    if not row: return []
    hist_json=row[0]
    hist=json.loads(hist_json)
    session_ids = {entry['session_id'] for entry in hist.values()}
    return list(session_ids)


def get_conversation_by_chat_id(chat_id):
    conn = None
    try:
        username = userInfo.get_user()
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute("SELECT conversation_history FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        print("by_chat_id", row)
        if row is None:
            print("🚫 Kullanıcı bulunamadı.")
            return None

        try:
            conversation_history = json.loads(row[0])  # JSON string → dict
        except json.JSONDecodeError:
            print("⚠️ JSON verisi çözümlenemedi.")
            return None

        filtered_messages = [
            item for item in conversation_history.values()
            if item.get("session_id") == chat_id
        ]

        if filtered_messages:
            print(f"✅ '{chat_id}' için {len(filtered_messages)} mesaj bulundu.")
            return filtered_messages
        else:
            print("🔍 Belirtilen chat_id için mesaj bulunamadı.")
            return []

    except sqlite3.Error as e:
        print(f"💥 Veritabanı hatası: {e}")
        return None

    finally:
        if conn:
            conn.close()


def update_user_session_count(operator):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    session_count = 0
    print("previous session count", userInfo.get_user_session())
    if operator == '+':
        session_count = userInfo.get_user_session() + 1
    if operator == '-':
        session_count = userInfo.get_user_session() - 1
    userInfo.set_user_session(session_count)
    print("new session count", userInfo.get_user_session())
    username = userInfo.get_user()  # Burada istediğin kullanıcı adını belirtebilirsin
    cursor.execute("UPDATE users SET session_count = ? WHERE username = ?",
                   (session_count, username))
    conn.commit()
    conn.close()


def delete_chat_from_conversation(username, chat_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # 1. Kullanıcının conversation_history'sini al
    cursor.execute("SELECT conversation_history FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    if result:
        print(result, "result printed")
        conversation_json = result[0]
        print(conversation_json, "conversation_json printed")
        try:
            # 2. JSON olarak parse et
            conversation_data = json.loads(conversation_json)

            # 3. session_id'si chat_id olanları sil
            filtered_data = {
                key: value for key, value in conversation_data.items()
                if value.get("session_id") != chat_id
            }

            # 4. Geri veritabanına yaz
            updated_json = json.dumps(filtered_data)
            cursor.execute("UPDATE users SET conversation_history = ? WHERE username = ?", (updated_json, username))
            conn.commit()
            print("Silme işlemi tamamlandı.")
        except json.JSONDecodeError:
            print("conversation_history alanı geçerli bir JSON değil.")
    else:
        print("Kullanıcı bulunamadı.")

    conn.close()


def first_message_check():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    username = userInfo.get_user()
    active_chat_id = userInfo.get_active_session()
    print(active_chat_id,"active_chat_id printed")
    cursor.execute("SELECT conversation_history FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    conn.close()

    if result:
        try:
            conversation_list = json.loads(result[0])
            # id'si eşleşen sohbeti filtrele
            filtered_chat = [chat for chat in conversation_list if chat.get("id") == active_chat_id]
            return filtered_chat  # List döner, 1 elemanlı ya da boş
        except json.JSONDecodeError:
            return {"error": "conversation_history geçerli bir JSON değil."}
    else:
        return {"error": "Kullanıcı bulunamadı."}
