import requests
from datetime import date

server_ip_receive = "http://172.27.27.231:5000"  # Include http:// and port 5000 (default Flask port)
server_ip_send = "http://172.27.27.231:5000/send"
sender = "ScitechMC"
receiver = "nig"

try:
    r = requests.get(server_ip_receive)
    print(r.text)  # Print the content of the response
except requests.exceptions.RequestException as e:
    print("Request failed:", e)

choice = input("send(s)/or receive(r): ")
match choice:
    case "s":
        send_message = input("Please enter text to send to the server: ")
        try:
            # Convert the date object to a string (YYYY-MM-DD)
            current_date = date.today().strftime("%Y-%m-%d")
            # Send the message in JSON format
            r = requests.post(server_ip_send, json={
                "message": send_message,
                "sender": sender,
                "receiver": receiver,
                "date": current_date  # Use the current_date string here, not the 'date' class
            })
            print("Server response:", r.text)  # Print the server's response
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
    case "r":
        try:
            r = requests.get(server_ip_receive)
            print(r.text)  # Print the content of the response
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)



#options, send, login, signup, receive
#
#
#
#
#
#
#
#
#