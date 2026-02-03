from colorama import init, Fore, Style
from datetime import datetime

init(autoreset=True)


class Logger:
    @staticmethod
    def info(msg):
        print(
            f"{Fore.CYAN}[INFO] {datetime.now().strftime('%H:%M:%S')} {msg}{Style.RESET_ALL}"
        )

    @staticmethod
    def success(msg):
        print(
            f"{Fore.GREEN}[SUCCESS] {datetime.now().strftime('%H:%M:%S')} {msg}{Style.RESET_ALL}"
        )

    @staticmethod
    def warning(msg):
        print(
            f"{Fore.YELLOW}[WARNING] {datetime.now().strftime('%H:%M:%S')} {msg}{Style.RESET_ALL}"
        )

    @staticmethod
    def error(msg):
        print(
            f"{Fore.RED}[ERROR] {datetime.now().strftime('%H:%M:%S')} {msg}{Style.RESET_ALL}"
        )

    @staticmethod
    def action(msg, remaining_actions):
        print(
            f"{Fore.MAGENTA}[ACTION] {msg} | {remaining_actions} actions remaining{Style.RESET_ALL}"
        )


log = Logger()
