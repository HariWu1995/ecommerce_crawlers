import sqlite3 as sqllib


db_connector = sqllib.connect('product_reviews_.db')
db_cursor = db_connector.cursor()


def execute_sql(query: str):
    try:
        query = query.replace('\n', '').replace('\t', '')
        while '  ' in query:
            query = query.replace('  ', ' ')
        db_cursor.execute(query)
        db_connector.commit()
    except Exception as e:
        print("\n\nQuery Error", query, '\n\n', e)
        # quit()


def insert_new_category(category_info: list or tuple):
    query = f"""
        INSERT INTO categories (title, url, source) 
        VALUES ("{category_info[0].replace('"', "'")}", "{category_info[1]}", "{category_info[2]}");
    """
    execute_sql(query)


def insert_new_product(product_info: list or tuple):
    query = f"""
        INSERT INTO products (title, url, category_id) 
        VALUES ("{product_info[0].replace('"', "'")}", "{product_info[1]}", "{product_info[2]}");
    """
    execute_sql(query)


def insert_new_review(review_info: list or tuple):
    query = f"""
        INSERT INTO reviews (content, is_verified, n_likes, rating, product_id) 
        VALUES ("{review_info[0].replace('"', "'")}", "{review_info[1]}", {review_info[2]}, {review_info[3]}, {review_info[4]});
    """
    execute_sql(query)


def initialize_db():
    # Create tables
    query = """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            title VARCHAR(32), 
            url VARCHAR(128), 
            source VARCHAR(8) 
        );
    """
    execute_sql(query)

    query = """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            title VARCHAR(64), 
            url VARCHAR(128), 
            category_id INTEGER 
        );
    """
    execute_sql(query)

    query = """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            content VARCHAR(1024), 
            is_verified VARCHAR(16), 
            n_likes INTEGER, 
            rating INTEGER, 
            product_id INTEGER 
        );
        """
    execute_sql(query)
    


