import requests
import json
import logging
from datetime import datetime
import os
import sys

# Configuration
BASE_URL = "http://localhost:5123"

# Create logs directory if it doesn't exist
if not os.path.exists('test_logs'):
    os.makedirs('test_logs')

# Set up logging format
log_format = '%(asctime)s - %(levelname)s - %(message)s'
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_logger(name, log_file, level=logging.INFO):
    """Function to set up a logger with file handler"""
    formatter = logging.Formatter(log_format)
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    return logger

# Create main logger
main_logger = setup_logger('main_tests', f'test_logs/tests_{current_time}.log')

def log_response(logger, label, response, request_data=None):
    """Helper function to log request and response details"""
    logger.info(f"\n{'='*50}")
    logger.info(f"TEST: {label}")
    
    if request_data:
        logger.info("REQUEST DATA:")
        logger.info(json.dumps(request_data, indent=2))
    
    logger.info(f"STATUS CODE: {response.status_code}")
    
    try:
        response_data = response.json()
        logger.info("RESPONSE:")
        logger.info(json.dumps(response_data, indent=2))
    except ValueError:
        logger.info("RESPONSE (non-JSON):")
        logger.info(response.text)
    
    if response.status_code >= 400:
        logger.warning(f"TEST FAILED: {label}")
    else:
        logger.info(f"TEST PASSED: {label}")

def get_input(prompt, required=True, input_type=str):
    """Helper function to get user input with validation"""
    while True:
        try:
            value = input(prompt).strip()
            if required and not value:
                print("This field is required!")
                continue
            return input_type(value)
        except ValueError:
            print(f"Invalid input. Please enter a valid {input_type.__name__}")

def test_base_routes(email):
    """Test all base routes"""
    try:
        print("\n[Testing Base Routes]")
        
        # Test index route
        response = requests.get(f"{BASE_URL}/")
        log_response(main_logger, "Index Route", response)
        print("1. Index route tested")
        
        # Test verify connection with GET (should fail)
        response = requests.get(f"{BASE_URL}/verify-connection")
        log_response(main_logger, "Verify Connection (GET)", response)
        print("2. Verify connection (GET) tested - should fail")
        
        # Test verify connection with POST (incompatible version)
        request_data = {"version": "invalid"}
        response = requests.post(f"{BASE_URL}/verify-connection", json=request_data)
        log_response(main_logger, "Verify Connection (POST - invalid version)", response, request_data)
        print("3. Verify connection (POST - invalid version) tested - should fail")
        
        # Test verify connection with POST (correct version)
        request_data = {"version": "alpha 0.2.0"}
        response = requests.post(f"{BASE_URL}/verify-connection", json=request_data)
        log_response(main_logger, "Verify Connection (POST - valid version)", response, request_data)
        print("4. Verify connection (POST - valid version) tested - should pass")
        
        # Test subscribe with POST
        request_data = {"email": email}
        response = requests.post(
            f"{BASE_URL}/subscribe",
            data=request_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        log_response(main_logger, "Subscribe (POST)", response, request_data)
        print("5. Subscribe route tested with email:", email)
        
    except Exception as e:
        main_logger.error(f"Exception in base routes tests: {str(e)}", exc_info=True)
        print(f"Error testing base routes: {str(e)}")

def test_user_registration(email):
    """Test user registration and return credentials"""
    try:
        print("\n[Testing User Registration]")
        username = get_input("Enter username to register: ")
        password = get_input("Enter password: ")
        
        request_data = {
            "username": username,
            "password": password,
            "email": email
        }
        
        response = requests.post(f"{BASE_URL}/user/register", json=request_data)
        log_response(main_logger, "User Registration", response, request_data)
        
        if response.status_code == 200:
            print("Registration successful!")
            return username, password
        else:
            print("Registration failed!")
            return None, None
            
    except Exception as e:
        main_logger.error(f"Exception in registration test: {str(e)}", exc_info=True)
        print(f"Error testing registration: {str(e)}")
        return None, None

def test_user_login(username, password):
    """Test user login and return session token"""
    try:
        print("\n[Testing User Login]")
        
        request_data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(f"{BASE_URL}/user/login", json=request_data)
        log_response(main_logger, "User Login", response, request_data)
        
        if response.status_code == 200:
            session_token = response.json().get("response", {}).get("session_token")
            if session_token:
                print("Login successful! Session token obtained.")
                return session_token
        print("Login failed!")
        return None
        
    except Exception as e:
        main_logger.error(f"Exception in login test: {str(e)}", exc_info=True)
        print(f"Error testing login: {str(e)}")
        return None

def test_chat_routes(session_token, username):
    """Test chat-related routes"""
    if not session_token:
        print("No session token available - skipping chat tests")
        return
        
    try:
        print("\n[Testing Chat Routes]")
        
        # Test fetch chats
        request_data = {"username": username}
        response = requests.post(
            f"{BASE_URL}/chat/fetch-chats",
            headers={"Authorization": f"Bearer {session_token}"},
            json=request_data
        )
        log_response(main_logger, "Fetch Chats", response, request_data)
        print("1. Fetch chats tested")
        
        # Test create chat
        participant = get_input("Enter participant username for new chat (leave empty to skip): ", required=False)
        if participant:
            request_data = {
                "username": username,
                "participants": [username, participant]
            }
            response = requests.post(
                f"{BASE_URL}/chat/create-chat",
                headers={"Authorization": f"Bearer {session_token}"},
                json=request_data
            )
            log_response(main_logger, "Create Chat", response, request_data)
            print("2. Create chat tested with participant:", participant)
        
        # Test receive message
        chat_id = get_input("Enter chat ID to send message to (leave empty to skip): ", required=False)
        if chat_id:
            message = get_input("Enter message to send: ")
            request_data = {
                "chatID": int(chat_id),
                "message": message
            }
            response = requests.post(
                f"{BASE_URL}/chat/receive-message",
                headers={"Authorization": f"Bearer {session_token}"},
                json=request_data
            )
            log_response(main_logger, "Receive Message", response, request_data)
            print("3. Receive message tested in chat:", chat_id)
            
    except Exception as e:
        main_logger.error(f"Exception in chat routes tests: {str(e)}", exc_info=True)
        print(f"Error testing chat routes: {str(e)}")

def main_menu():
    """Display main menu and handle user choices"""
    print("\nAPI Test Menu")
    print("1. Test all routes")
    print("2. Test base routes only")
    print("3. Test user routes only")
    print("4. Test chat routes only")
    print("5. Exit")
    
    choice = get_input("Enter your choice (1-5): ", input_type=int)
    return choice

def main():
    print(f"\nAPI Testing Tool - Logs will be saved to 'test_logs/tests_{current_time}.log'")
    
    # Get test email
    test_email = get_input("Enter test email address: ")
    
    while True:
        choice = main_menu()
        
        if choice == 1:  # Test all routes
            test_base_routes(test_email)
            username, password = test_user_registration(test_email)
            if username and password:
                session_token = test_user_login(username, password)
                test_chat_routes(session_token, username)
                
        elif choice == 2:  # Test base routes only
            test_base_routes(test_email)
            
        elif choice == 3:  # Test user routes only
            username, password = test_user_registration(test_email)
            if username and password:
                test_user_login(username, password)
                
        elif choice == 4:  # Test chat routes only
            username = get_input("Enter existing username: ")
            password = get_input("Enter password: ")
            session_token = test_user_login(username, password)
            test_chat_routes(session_token, username)
            
        elif choice == 5:  # Exit
            print("Exiting test program.")
            break
            
        else:
            print("Invalid choice. Please try again.")
            
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        main_logger.error(f"Main execution error: {str(e)}", exc_info=True)
        sys.exit(1)