from app import create_app
from app.database.db_helper import close_db
from waitress import serve
import logging
from dotenv import load_dotenv
import os

load_dotenv()

app = create_app()

if os.getenv("PROD_STAGE") == "dev":
    logging.getLogger("db-debug").setLevel(logging.DEBUG)

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

if __name__ == "__main__":
    try:
        if os.getenv("PROD_STAGE") == "prod":
            serve(app, host='0.0.0.0', port=5123, threads=os.getenv("THREADS", 4))
        elif os.getenv("PROD_STAGE") == "dev":
            app.run(host='0.0.0.0', port=5123, debug=True)
    except Exception as e:
        print(f"Error: {e}")