class BotConfig:
    def __init__(self, token: str, db_connection, user_id_list: list[int] = []):
        self.token = token
        self.db_connection = db_connection
        self.user_id_list = user_id_list
