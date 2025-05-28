from flask import Flask, request, jsonify, Blueprint, render_template,redirect,url_for
import os
import sys
import pyautogui
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from DatabaseServices.database import check_user, create_user
from UserInfo import userInfo
login_page_bp = Blueprint("login_page", __name__)

# Üst dizini path'e ekleyerek modüllerin tanınmasını sağlıyoruz
@login_page_bp.route("/login", methods=["GET"])
def show_login_interface():
    """Sohbet arayüzünü görüntüler"""
    return render_template("userLogin.html")

@login_page_bp.route("/api/login/checkUser", methods=["POST"])
def check_user_exist():
    request_data = request.get_json()
    username = request_data["username"]
    password = request_data["password"]
    result = check_user(username, password)
    if result[0] == True:
        userInfo.set_user(username)
        return jsonify({"success": True, "html": render_template("loadingScreen.html",user = username.upper())})
    else:
        return jsonify({"success": False, "message": "Kullanıcı adı veya şifre hatalı!"})


@login_page_bp.route("/api/login/createUser",methods=["POST"])
def create_new_user():
    request_data = request.get_json()
    username = request_data["username"]
    password = request_data["password"]
    result = create_user(username, password)
    print(result)
    return result

@login_page_bp.route("/api/logout", methods=["POST"])
def logout():
    userInfo.set_user(None)
    pyautogui.hotkey('f5')
    print("userinfo ",userInfo.get_user())
    return {"success": True}