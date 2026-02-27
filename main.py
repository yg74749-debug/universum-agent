from portals.ums import run_ums
from portals.canvas import run_canvas
from telegram_notify import send_telegram

def main():
    report = []
    report += run_ums()
    report += run_canvas()

    send_telegram("\n".join(report) if report else "Hiçbir veri çekilemedi.")

if __name__ == "__main__":
    main()
