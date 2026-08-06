"""
Quick Test Runner
Run specific tests quickly from command line
"""
import sys
import subprocess

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

TESTS = {
    "1": {"name": "Database", "file": "test_database.py"},
    "2": {"name": "Services", "file": "test_services.py"},
    "3": {"name": "Embeddings", "file": "test_embeddings.py"},
    "4": {"name": "LLM Models", "file": "test_llm_models.py"},
    "5": {"name": "RAG Pipeline", "file": "test_rag_pipeline.py"},
    "6": {"name": "Performance", "file": "test_performance.py"},
    "7": {"name": "API Endpoints", "file": "test_api.py"},
    "8": {"name": "All Tests", "file": "test_all.py"}
}


def print_menu():
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}QUICK TEST RUNNER{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")
    
    for key, test in TESTS.items():
        print(f"{BLUE}[{key}]{RESET} {test['name']}")
    
    print(f"\n{BLUE}[0]{RESET} Exit")
    print(f"{CYAN}{'='*60}{RESET}\n")


def run_test(test_file):
    print(f"\n{YELLOW}Running: {test_file}{RESET}\n")
    
    result = subprocess.run(
        [sys.executable, test_file],
        cwd="."
    )
    
    return result.returncode == 0


def main():
    if len(sys.argv) > 1:
        # Command line argument provided
        choice = sys.argv[1]
        
        if choice in TESTS:
            test = TESTS[choice]
            print(f"\n{CYAN}Running: {test['name']}{RESET}")
            success = run_test(test['file'])
            sys.exit(0 if success else 1)
        else:
            print(f"{RED}Invalid choice: {choice}{RESET}")
            print(f"Valid options: {', '.join(TESTS.keys())}")
            sys.exit(1)
    
    # Interactive mode
    while True:
        print_menu()
        
        try:
            choice = input(f"{YELLOW}Select test to run: {RESET}").strip()
            
            if choice == "0":
                print(f"\n{GREEN}Goodbye!{RESET}\n")
                break
            
            if choice in TESTS:
                test = TESTS[choice]
                success = run_test(test['file'])
                
                if success:
                    print(f"\n{GREEN}✓ Test completed successfully{RESET}")
                else:
                    print(f"\n{RED}✗ Test failed{RESET}")
                
                input(f"\n{YELLOW}Press Enter to continue...{RESET}")
            else:
                print(f"{RED}Invalid choice. Please try again.{RESET}")
        
        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}Interrupted by user{RESET}\n")
            break
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")


if __name__ == "__main__":
    main()
