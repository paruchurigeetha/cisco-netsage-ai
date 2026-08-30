import os
import sys
import subprocess
import time
import webbrowser
import threading

def run_server():
    print("Starting NetSage AI Flask Server...")
    # Run app.py using the current python executable
    subprocess.run([sys.executable, "app.py"])

def main():
    # 1. Make sure databases are generated
    if not os.path.exists("cases_db.json") or not os.path.exists("cases.csv"):
        print("Generating cases dataset files...")
        subprocess.run([sys.executable, "generate_cases.py"])
        
    # 2. Make sure initial excel dashboard is generated
    if not os.path.exists("dashboard.xlsx"):
        print("Generating initial spreadsheet dashboard...")
        subprocess.run([sys.executable, "export_dashboard.py"])
        
    # 3. Spin up server in a separate thread so we can open browser and handle shutdown cleanly
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to boot
    time.sleep(1.5)
    
    # 4. Open default browser
    url = "http://127.0.0.1:5000/"
    print(f"\nNetSage AI Dashboard is now running locally!")
    print(f"Opening browser to: {url}")
    print("Press Ctrl+C in this terminal to stop the server.")
    
    try:
        webbrowser.open(url)
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping NetSage AI Server. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
