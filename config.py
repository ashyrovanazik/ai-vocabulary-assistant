import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '12345678')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'ai_vocabulary_assistant')
SECRET_KEY = os.getenv('SECRET_KEY', 'change_this_secret_key')
