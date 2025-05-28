user = None
session = 0
active_session = None

def set_user(username):
    global user
    user = username


def get_user():
    return user


def set_user_session(session_count):
    global session
    session = session_count


def get_user_session():
    return session

def set_active_session(current_session):
    global active_session
    active_session = current_session

def get_active_session():
    return active_session
