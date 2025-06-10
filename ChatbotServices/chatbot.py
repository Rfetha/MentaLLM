from flask import Flask, request, jsonify, Blueprint, render_template, redirect, url_for
from ChatbotServices.rag import llm_response, initialize_llm, load_environment, prepare_data,llm_response_for_header
from UserInfo import userInfo
from DatabaseServices.database import setup_database, get_conversation_history, update_user_session_count,get_conversation_by_chat_id,delete_chat_from_conversation,get_unique_sessions,first_message_check
# Veritabanı başlatma
setup_database()

# Blueprint oluştur
chatbot_bp = Blueprint("chatbot", __name__)

prepared_llm = None
prepared_retriever = None


def set_llm(llm):
    global prepared_llm
    prepared_llm = llm


def get_llm():
    return prepared_llm


def set_retriever(retriever):
    global prepared_retriever
    prepared_retriever = retriever
    if prepared_retriever is None:
        print("prepared_retriever is none")


def get_retriever():
    return prepared_retriever


@chatbot_bp.route("/api/chatbot", methods=["POST"])
def handle_chat_request():
    response_data={}
    """Kullanıcı mesajını işler ve chatbot yanıtını döndürür"""
    active_chat = userInfo.get_active_session()
    try:
        request_data = request.get_json()
        if not request_data or "message" not in request_data:
            return jsonify({"error": "Geçersiz istek formatı"}), 400
        user_message = request_data["message"]
        if not get_conversation_by_chat_id(active_chat):
            chat_header = llm_response_for_header(user_message)
            response_data["chat_header"] = chat_header
        bot_response = llm_response(user_message)
        response_data["response"] = bot_response
        return jsonify(response_data)

    except Exception as error:
        print(f"Chatbot hatası: {str(error)}")
        return jsonify({"error": "İç sunucu hatası"}), 500


@chatbot_bp.route("/api/session", methods=["UPDATE"])
def update_session_count():
    update_user_session_count('+')
    return jsonify({"session": userInfo.get_user_session()})


@chatbot_bp.route("/api/session", methods=["GET"])
def get_session_count():
    print("get uniq sessions loading : ->>>>>", get_unique_sessions())
    return jsonify({"session_count": get_unique_sessions()})

@chatbot_bp.route("/api/session", methods=["POST"])
def set_session_count():
    session_number = request.get_json()["session_number"]
    print("session number: ", session_number[-1])
    userInfo.set_user_session(session_number)
    return jsonify({"Session Count updated": True})

@chatbot_bp.route("/api/activeSession", methods=["POST"])
def set_active_session():
    current_session = request.get_json()["current_session"]
    userInfo.set_active_session(current_session)
    print("active session: ", userInfo.get_active_session())
    return jsonify({"Session updated": True})

@chatbot_bp.route("/api/chatHistory", methods=["GET"])
def get_chat_history():
    chat_history = get_conversation_history(10)
    print("chat_history: ", chat_history)
    return jsonify({"chat_history": chat_history})
@chatbot_bp.route("/api/deleteChat", methods=["DELETE"])
def del_user_chat():
    chat_id = request.get_json()["chat_id"]
    username = userInfo.get_user()
    delete_chat_from_conversation(username,chat_id)
    update_user_session_count('-')
    print("deleting chat_id: ", chat_id)
    return jsonify({"successfully deleted": chat_id})

@chatbot_bp.route("/api/requestedChatData", methods=["POST"])
def get_requested_chat_data():
    chat_id = request.get_json()["chat_id"]
    print("chat_id: ", chat_id)
    conversation_history_by_id = get_conversation_by_chat_id(chat_id)
    print("conversation_history_by_id: ", conversation_history_by_id)
    return jsonify({"conversation_history_by_id": conversation_history_by_id})

@chatbot_bp.route("/chat", methods=["GET"])
def show_chat_interface():
    if userInfo.get_user() is None:
        return redirect(url_for("chatbot.direct_login_page"))
    """Sohbet arayüzünü görüntüler"""
    return render_template("index.html")


@chatbot_bp.route("/login", methods=["GET"])
def direct_login_page():
    print("return worked in chatbotpy")
    return render_template("userLogin.html")


@chatbot_bp.route("/", methods=["GET"])
@chatbot_bp.route("/chat", methods=["GET"])
def direct_user():
    if userInfo.get_user() is None:
        return redirect(url_for(("chatbot.direct_login_page")))
    else:
        return redirect(url_for("chatbot.show_chat_interface"))


@chatbot_bp.route("/api/prepareData", methods=["POST"])
def pre_prepare_data():
    print("Preparing data and LLM")
    load_environment()
    llm = initialize_llm()
    retriever = prepare_data()
    set_llm(llm)
    set_retriever(retriever)
    print("Data and LLM successfully prepared")
    return {"success": True}


# Flask uygulaması
app = Flask(__name__)
app.register_blueprint(chatbot_bp)
