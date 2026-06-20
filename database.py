import pymysql
from pymysql.cursors import DictCursor
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE


def create_connection(with_database=False):
    """Create a MySQL connection. Use without database to initialize schema."""
    connection_args = {
        'host': MYSQL_HOST,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
    }
    if with_database:
        connection_args['db'] = MYSQL_DATABASE
    return pymysql.connect(**connection_args)


def init_db():
    """Create the application database and tables if they do not exist."""
    try:
        conn = create_connection(with_database=False)
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        conn.close()
    except Exception as err:
        print('Database initialization error:', err)
        return

    try:
        conn = create_connection(with_database=True)
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    word VARCHAR(100) NOT NULL,
                    phonetic VARCHAR(100),
                    part_of_speech VARCHAR(100),
                    chinese_meaning TEXT,
                    definition TEXT,
                    collocations TEXT,
                    synonyms TEXT,
                    antonyms TEXT,
                    example_sentence TEXT,
                    chinese_translation TEXT,
                    source_name VARCHAR(255),
                    source_url TEXT,
                    difficulty VARCHAR(50),
                    ai_explanation TEXT,
                    review_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    command TEXT,
                    target_word VARCHAR(100),
                    status VARCHAR(50),
                    steps TEXT,
                    result_summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS review_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    vocabulary_id INT NOT NULL,
                    result VARCHAR(50),
                    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (vocabulary_id) REFERENCES vocabulary(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_name VARCHAR(255),
                    source_url TEXT,
                    word VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS login_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    login_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """
            )
        conn.commit()
    except Exception as err:
        print('Schema creation error:', err)
    finally:
        conn.close()


def get_db_connection():
    """Get a database connection to the configured application database."""
    return create_connection(with_database=True)
