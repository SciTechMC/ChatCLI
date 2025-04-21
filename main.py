from app import create_app
from app.database.db_helper import close_db
from waitress import serve

app = create_app()

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5123, debug=True)
    except Exception as e:
        print(f"Error: {e}")