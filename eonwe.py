import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta, timezone
import pytz
import os
import sys
import asyncio

# Environment variables or fallback values
TOKEN = os.getenv("PAL_TOKEN")
CHANNEL_ID = int(os.getenv("PAL_TRAP_ID"))

# Configure the bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
scheduler = AsyncIOScheduler()

# Reminder schedule by week type
reminders = {
    'odd': [  # Week 1
        {'day': 'mon', 'hour': 17, 'minute': 0},
        {'day': 'wed', 'hour': 16, 'minute': 0},
        {'day': 'fri', 'hour': 16, 'minute': 0},
    ],
    'even': [  # Week 2
        {'day': 'sun', 'hour': 15, 'minute': 15},
        {'day': 'tue', 'hour': 16, 'minute': 30},
        {'day': 'thu', 'hour': 15, 'minute': 30},
        {'day': 'sat', 'hour': 15, 'minute': 15},
    ]
}

# Week 1 starts on Sunday, June 29, 2025
def get_week_type():
    reference_date = datetime(2025, 6, 29, tzinfo=timezone.utc)
    today = datetime.now(timezone.utc)
    delta_weeks = (today - reference_date).days // 7
    return 'odd' if delta_weeks % 2 == 0 else 'even'

# Subtract 30 minutes from the event time to schedule the reminder
def adjust_time(hour, minute):
    event_time = datetime(2000, 1, 1, hour, minute)
    reminder_time = event_time - timedelta(minutes=30)
    return reminder_time.hour, reminder_time.minute

# Send reminder only if it's the correct week
async def send_reminder_if_week_matches(channel, week_type, job):
    if get_week_type() == week_type:
        if job['day'] == 'fri' or job['day'] == 'sat':
            await channel.send("@everyone Dancing in 15 minutes and Trap in 30 minutes.")
        else:
            await channel.send("@everyone Trap in 30 minutes.")
        print(f"✅ Reminder sent at {datetime.utcnow().strftime('%H:%M UTC')}")

# Daily debug message after 00:00 UTC
def print_next_scheduled_times():
    print("⏳ Scheduled messages for today (UTC):")
    week_type = get_week_type()
    now = datetime.now(pytz.UTC)
    today_str = now.strftime('%a').lower()

    for job in reminders.get(week_type, []):
        if job['day'] == today_str:
            hour, minute = adjust_time(job['hour'], job['minute'])
            target_time = datetime(now.year, now.month, now.day, hour, minute, tzinfo=pytz.UTC)
            print(f"⏳ Message scheduled for {target_time.strftime('%H:%M %Z')}")

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    channel = bot.get_channel(CHANNEL_ID)

    # Schedule reminders
    for week_type, jobs in reminders.items():
        for job in jobs:
            reminder_hour, reminder_minute = adjust_time(job['hour'], job['minute'])

            trigger = CronTrigger(
                day_of_week=job['day'],
                hour=reminder_hour,
                minute=reminder_minute,
                timezone=pytz.UTC
            )

            scheduler.add_job(
                send_reminder_if_week_matches,
                trigger=trigger,
                args=[channel, week_type, job]
            )

    # Schedule the daily 00:01 UTC info message
    scheduler.add_job(
        print_next_scheduled_times,
        trigger=CronTrigger(hour=0, minute=1, timezone=pytz.UTC)
    )

    scheduler.start()
    await tree.sync()
    print("📆 Reminders activated.")
    print("📝 Slash commands synced.")

@tree.command(name="next_trap", description="Show the next trap time and how much time is left")
async def next_trap(interaction: discord.Interaction):
    try:
        now = datetime.now(pytz.UTC)
        week_type = get_week_type()
        upcoming_traps = []

        for job in reminders[week_type]:
            trap_hour = job['hour']
            trap_minute = job['minute']

            job_weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].index(job['day'])
            today_weekday = now.weekday()
            days_ahead = (job_weekday - today_weekday) % 7

            trap_date = now + timedelta(days=days_ahead)
            trap_dt = datetime(
                trap_date.year, trap_date.month, trap_date.day,
                trap_hour, trap_minute, tzinfo=pytz.UTC
            )

            if trap_dt <= now:
                trap_dt += timedelta(weeks=2)  # traps alternate weekly

            upcoming_traps.append(trap_dt)

        next_trap_dt = min(upcoming_traps)
        time_remaining = next_trap_dt - now
        hours, remainder = divmod(int(time_remaining.total_seconds()), 3600)
        minutes = remainder // 60

        msg = (
            f"**⏰ Next Trap:** {next_trap_dt.strftime('%a, %b %d %Y at %H:%M UTC')}\n"
            f"**⌛ Time Left:** {hours}h {minutes}m\n"
        )
        await interaction.response.send_message(msg)

    except Exception as e:
        await interaction.response.send_message("⚠️ Failed to calculate next trap.")
        print(f"❌ Error in /next_trap: {e}")

@tree.command(name="show_reminders", description="List all trap times for the current week type")
async def show_reminders(interaction: discord.Interaction):
    try:
        week_type = get_week_type()
        msg = f"**📆 Scheduled Traps — {week_type.capitalize()} Week:**\n"
        for job in reminders[week_type]:
            time_str = f"{job['hour']:02d}:{job['minute']:02d} UTC"
            msg += f"• {job['day'].capitalize()} at {time_str}\n"
        await interaction.response.send_message(msg)
    except Exception as e:
        await interaction.response.send_message("⚠️ Failed to show reminders.")
        print(f"❌ Error in /show_reminders: {e}")

@tree.command(name="about_eonwe", description="Learn more about Eönwë and what he does")
async def about_eonwe(interaction: discord.Interaction):
    try:
        msg = (
            "**👋 Hi, I'm Eönwë!**\n\n"
            "I'm **Manwë's messenger**, here to help you stay prepared.\n\n"
            "Right now, I'm tasked with reminding you of upcoming **Trap** events.\n"
            "I'm still under development, but in **Manwë's plans** are:\n"
            "• Reminders for **RR** and other key events\n"
            "• Helpful commands to keep you updated\n"
            "• Smarter scheduling and coordination\n\n"
            "Stay tuned — my powers are growing. 🌟"
        )
        await interaction.response.send_message(msg)
    except Exception as e:
        await interaction.response.send_message("⚠️ Failed to deliver Eönwë's message.")
        print(f"❌ Error in /about_eonwe: {e}")

bot.run(TOKEN)
