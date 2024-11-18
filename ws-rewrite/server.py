from flask import Flask, request, jsonify
import websockets

app = Flask(__name__)

@app.route("/connection", methods=["GET", "POST"])
async def connection():
    server_version = "pre-alpha V0.1.0"
    data = request.json()
    if data["client_version"] == server_version:
        return jsonify(), 200
    else:
        return jsonify(), 400

if __name__ == "main":
    print(f"   * [red]SERVER VERSION: {server_version}[/]")
    async
    app.run(host="0.0.0.0", debug=True)