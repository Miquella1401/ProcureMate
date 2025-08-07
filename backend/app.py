from dotenv import load_dotenv
from connect_agents import initialize_agents

def main():
    load_dotenv()
    print("Environment loaded.")
    initialize_agents()

if __name__ == "__main__":
    main()
