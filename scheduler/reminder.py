import os
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()


def revision_reminder():

    print("\n")
    print("====================================")
    print("🔔 DAILY REVISION REMINDER")
    print("====================================")
    print("Time to revise!")
    print("Open your AI Revision Agent.")
    print("====================================")
    print()


def start_scheduler():

    scheduler = BackgroundScheduler()

    revision_time = os.getenv(
        "REVISION_TIME",
        "18:00"
    )

    hour, minute = map(
        int,
        revision_time.split(":")
    )

    scheduler.add_job(
        revision_reminder,
        "cron",
        hour=hour,
        minute=minute
    )

    scheduler.start()

    return scheduler