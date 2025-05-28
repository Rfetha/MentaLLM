import os
from flask import Flask
from ChatbotServices.chatbot import chatbot_bp  # Import chatbot blueprint
from LoginServices.loginServices import login_page_bp
from DatabaseServices.database import setup_database
# Initialize the Flask app
app = Flask(__name__)

# Register the chatbot blueprint
app.register_blueprint(chatbot_bp)
app.register_blueprint(login_page_bp)

if __name__ == '__main__':
    # Run the app with specified host and port from environment variables
    setup_database()
    app.run(host='127.0.0.1', port=os.getenv("HOST_PORT"), debug=True)
