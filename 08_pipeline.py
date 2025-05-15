import os
import time

def run(cmd):
    print(f"\n[Running] {cmd}")
    os.system(cmd)

def main():
    run("bash 01_install_dependencies.sh")
    run("xvfb-run python 02_extract_parse_emails.py")
    run("python 03_fill_database.py")
    run("python 06_classify_emails.py")

    # Start Ollama server (in background)
    print("Starting Ollama server...")
    os.system("ollama serve &")
    time.sleep(10)  # give it a moment to start
    run("python 07_extract_event_info.py")

if __name__ == "__main__":
    main()
