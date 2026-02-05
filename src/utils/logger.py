from colorama import init, Fore, Style, Back
from datetime import datetime

init(autoreset=True)


class Logger:
    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def info(msg):
        print(f"{Fore.WHITE}🔹 {Logger._timestamp()} {Fore.CYAN}{msg}")

    @staticmethod
    def success(msg):
        print(f"{Fore.GREEN}✅ {Logger._timestamp()} {Style.BRIGHT}{msg}")

    @staticmethod
    def warning(msg):
        print(f"{Fore.YELLOW}⚠️ {Logger._timestamp()} {Style.BRIGHT}{msg}")

    @staticmethod
    def error(msg):
        print(
            f"{Back.RED}{Fore.WHITE} ❌ ERROR {Style.RESET_ALL} {Fore.RED}{Logger._timestamp()} {msg}"
        )

    @staticmethod
    def action(msg, remaining_actions):
        print(f"\n{Fore.MAGENTA}{'='*45}")
        print(
            f"{Fore.BLACK}{Back.MAGENTA} 🚀 ACTION {Style.RESET_ALL} {Fore.MAGENTA}{Style.BRIGHT}{msg}"
        )
        print(f"{Fore.MAGENTA}📍 Points: {remaining_actions} remaining")
        print(f"{Fore.MAGENTA}{'='*45}")

    @staticmethod
    def reasoning(msg):
        print(f"{Fore.BLUE}{Style.BRIGHT}🧠 [STRATEGY] {Style.NORMAL}{msg}")

    @staticmethod
    def criticism(msg):
        print(
            f"{Fore.YELLOW}{Style.BRIGHT}🛡️  [SELF-CRITICISM] {Fore.WHITE}{Style.DIM}{msg}"
        )

    @staticmethod
    def next_move(msg):
        print(f"{Fore.CYAN}{Style.BRIGHT}🔭 [NEXT MOVE] {Style.NORMAL}{msg}")


log = Logger()
