def run_application(flask_script="main.py", fastapi_script="app/websockets/main.py"):
    """Launch the Flask and FastAPI scripts in separate CMD windows with clear titles."""
    try:
        subprocess.Popen([
            "cmd.exe", "/c",
            "start", "Flask Backend",
            "cmd.exe", "/k", f"python {flask_script}"
        ])

        subprocess.Popen([
            "cmd.exe", "/c",
            "start", "FastAPI Backend",
            "cmd.exe", "/k", f"python {fastapi_script}"
        ])

    except Exception as e:
        input(f"An error occurred while starting the application: {e}\nPress Enter to exit...")
        raise
    
if __name__ == "__main__":
    import subprocess

    run_application()