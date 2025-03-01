import os
import json
import asyncio
import logging

from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

import config


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_json(file_path, default_type={}):
    file_path = os.path.normpath(file_path)
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            return data
    except (IOError, json.JSONDecodeError) as err:
        logger.error("Error loading JSON from %s: %s", file_path, err)
    except Exception as err:
        logger.error("Unexpected error in load_json: %s", err)

    return default_type


def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except IOError as err:
        logger.error("Error saving JSON to %s: %s", file_path,  err)
    except Exception as err:
        logger.error("Unexpected error in save_json: %s", err)


def get_daily_file_path(daily_folder_path):
    try:
        today = datetime.now()
        norm_daily_folder_path = os.path.normpath(daily_folder_path)

        if not os.path.exists(norm_daily_folder_path):
            os.makedirs(norm_daily_folder_path)

        return os.path.join(norm_daily_folder_path, f"{today.strftime('%Y-%m-%d')}.md")
    except Exception as err:
        logger.error("Error in get_daily_file_path: %s", err)

        return None


def format_task_with_callout(task):
    try:
        lines = task.split('\n')
        formatted_task = f"> - [ ] {lines[0]}\n"

        if len(lines) > 1:
            formatted_task += ''.join(
                f">     {line}  \n" if line.strip() else ">  \n"
                for line in lines[1:]
            )

        return formatted_task
    except Exception as err:
        logger.error("Error in format_task_with_callout: %s", err)

        return "> - [ ] Error formatting task\n"


def format_task(task):
    try:
        lines = task.split('\n')
        formatted_task = f"- [ ] {lines[0]}\n"

        if len(lines) > 1:
            formatted_task += ''.join(
                f"    {line}  \n" if line.strip() else "  \n"
                for line in lines[1:]
            )

        return formatted_task
    except Exception as err:
        logger.error("Error in format_task: %s", err)

        return "- [ ] Error formatting task\n"


def append_tasks_to_file(file_path, tasks, use_callout_format):
    try:
        with open(file_path, "ab+") as f:
            f.seek(0, os.SEEK_END)
            end_position = f.tell()

            if end_position > 0:
                f.seek(end_position - 1)
                last_char = f.read(1)

                if last_char != b"\n":
                    f.write(b"\n")

        with open(file_path, "a", encoding="utf-8") as f:
            if use_callout_format and os.path.getsize(file_path) == 0:
                f.write("> [!note] Task and ideas\n")

            for task in tasks:
                if use_callout_format:
                    formatted_task = format_task_with_callout(task)
                else:
                    formatted_task = format_task(task)

                f.write(formatted_task)
    except Exception as err:
        logger.error("Error in append_tasks_to_file: %s", err)


def get_last_update_id(file_path):
    try:
        data = load_json(file_path, default_type={"last_update_id": 0})

        return data.get("last_update_id", 0)
    except Exception as err:
        logger.error("Error in get_last_update_id: %s", err)

        return 0


async def check_and_add_tasks(bot_token, user_id, daily_folder_path, last_update_id_file_path, use_callout_format):
    bot = Bot(token=bot_token)
    last_update_id = get_last_update_id(last_update_id_file_path)

    try:
        new_tasks = []
        max_update_id = last_update_id
        updates = await bot.get_updates()

        for update in updates:
            if update.update_id <= last_update_id:
                continue

            if update.message and update.message.text and update.message.chat.id == user_id:
                new_tasks.append(update.message.text)

            max_update_id = max(max_update_id, update.update_id)

        if new_tasks:
            file_path = get_daily_file_path(daily_folder_path)

            if file_path:
                append_tasks_to_file(file_path, new_tasks, use_callout_format)

        if max_update_id > last_update_id:
            save_json(last_update_id_file_path, {"last_update_id": max_update_id})
    except TelegramError as err:
        logger.error("Telegram API error: %s", err)
    except Exception as err:
        logger.error("Error in check_and_add_tasks: %s", err)


if __name__ == "__main__":
    asyncio.run(
        check_and_add_tasks(
            bot_token                = config.BOT_TOKEN,
            user_id                  = config.USER_ID,
            daily_folder_path        = config.DAILY_FOLDER_PATH,
            last_update_id_file_path = config.LAST_UPDATE_ID_FILE_PATH,
            use_callout_format       = config.USE_CALLOUT_FORMAT
        )
    )
