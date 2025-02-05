import asyncio
import logging
import time

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import  CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    Message,
)

import config

from bot.keyboards import get_keyboard
from bot.states import UserStates
from bot.texts import *
from api import IdeaGenAPI

TOKEN = config.bot_token

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(TOKEN)
api = IdeaGenAPI()

bot_logger = logging.getLogger('bot_logger')
handler = logging.StreamHandler()
format_log = logging.Formatter("%(levelname)s:%(name)s - %(message)s")
handler.setFormatter(format_log)
bot_logger.addHandler(handler)
bot_logger.setLevel(logging.INFO)

async def safe_delete_messages(chat_id: int, message_ids: list):
    """Функция безопасного удаления сообщений с обработкой ошибок."""
    if not message_ids:
        return

    try:
        await bot.delete_messages(chat_id=chat_id, message_ids=message_ids)
    except TelegramBadRequest:
        bot_logger.warning(f"Сообщения {message_ids} уже удалены или не существуют.")
    except TelegramForbiddenError:
        bot_logger.warning(f"Нет прав на удаление сообщений в чате {chat_id}.")
    except TelegramRetryAfter as e:
        bot_logger.warning(f"Превышен лимит запросов. Ожидание {e.retry_after} секунд...")
        await asyncio.sleep(e.retry_after)
        await safe_delete_messages(chat_id, message_ids)


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    bot_logger.info(f'Начало работы: пользователь - {message.chat.id}, время: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    await message.answer(hello_message_text, reply_markup=None)
    message_start = await message.answer(start_message_text, reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_start.message_id])

async def new_start_handler(message: Message, state: FSMContext) -> None:
    bot_logger.info(f'Начало работы: пользователь - {message.chat.id}, время: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    message_start = await message.answer(start_message_text, reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_start.message_id])


@dp.callback_query(F.data == button_text_agents)
async def get_agents(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    await state.set_state(UserStates.get_agents)
    message_agent = await callback.message.answer(text_for_agent, reply_markup=get_keyboard('empty', back=True))
    await state.update_data(delete_messege=[message_agent.message_id])

@dp.message(StateFilter(UserStates.get_agents), F.content_type == "text")
async def get_agent_text(message: Message, state: FSMContext):
    message_id = message.message_id
    user_data = await state.get_data() 
    await safe_delete_messages(message.chat.id, user_data.get("delete_messege", []))
    await state.update_data(agents=message.text)
    answer = api.parsing_agents(message.text)
    name_agents = ', '.join(answer.keys())
    message_answer = await message.answer(f'Вы ввели {len(answer)} агентов:\n{name_agents}\n\n', reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_id, message_answer.message_id])

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_agents))
async def get_back_from_agent(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    message_answer = await callback.message.answer("Стартовые настройки\n\n", reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.callback_query(F.data == button_text_theme)
async def get_theme(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    await state.set_state(UserStates.get_theme)
    message_answer = await callback.message.answer(text_for_theme, reply_markup=get_keyboard('empty', back=True))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.message(StateFilter(UserStates.get_theme), F.content_type == "text")
async def get_theme_text(message: Message, state: FSMContext):
    message_id = message.message_id
    user_data = await state.get_data() 
    await safe_delete_messages(message.chat.id, user_data.get("delete_messege", []))
    await state.update_data(history=[])
    await state.update_data(first_messege=True)
    text_messege = message.text
    await state.update_data(theme=text_messege)
    message_answer = await message.answer(f'Тема диалога: {text_messege}\n\n', reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_id, message_answer.message_id])

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_theme))
async def get_back_from_theme(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    message_answer = await callback.message.answer("Стартовые настройки\n\n", reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.callback_query(F.data == button_text_gen_menu)
async def get_gen_menu(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    await state.set_state(UserStates.get_menu)
    message_answer = await callback.message.answer("Меню генерации\n\n", reply_markup=get_keyboard('conversation_kb', back=True))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_menu))
async def get_back_from_gen_menu(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    message_answer = await callback.message.answer("Стартовые настройки\n\n", reply_markup=get_keyboard('start_kb'))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.callback_query(F.data == button_text_gen, StateFilter(UserStates.get_menu))
async def generate_dialog(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    agents = user_data.get("agents", '[робот], спец по космосу')
    theme = user_data.get("theme", 'Расскажи про космос')
    history = user_data.get("history", [])
    first_messege = user_data.get("first_messege", True)
    wait_message = await callback.message.answer('Идет обсуждение')
    try:
        bot_logger.info('генирация диалога')
        content, convers_history = api.get_answer(agents, theme, history, first_messege)
    except Exception as e:
        await callback.message.answer('API ERROR')
        bot_logger.warning(f"!!ERROR!!, {e}")
    await safe_delete_messages(callback.message.chat.id, [wait_message.message_id])
    for answer in content:
        await callback.message.answer(f'{list(answer.keys())[0]}\n{list(answer.values())[0]}\n')
    await state.update_data(history=convers_history)
    await state.update_data(first_messege=False)
    message_answer = await callback.message.answer("Меню генерации\n\n",reply_markup=get_keyboard('conversation_kb', back=True))
    await state.update_data(delete_messege=[message_answer.message_id])
    await state.set_state(UserStates.get_menu)
    
@dp.callback_query(F.data == button_text_add_replica, StateFilter(UserStates.get_menu))
async def add_replica(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    await state.set_state(UserStates.get_add_replica)
    message_answer = await callback.message.answer(text_for_add_replica, reply_markup=get_keyboard('empty', back=True))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_add_replica))
async def get_back_to_gen_menu(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    await state.set_state(UserStates.get_menu)
    message_answer = await callback.message.answer("Меню генерации\n\n", reply_markup=get_keyboard('conversation_kb', back=True))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.message(StateFilter(UserStates.get_add_replica), F.content_type == "text")
async def add_replica(message: Message, state: FSMContext):
    user_data = await state.get_data() 
    await safe_delete_messages(message.chat.id, user_data.get("delete_messege", []))
    await state.set_state(UserStates.get_menu)
    user_data = await state.get_data()
    history = user_data["history"] + [{'role': 'user', 'content': message.text}]
    await state.update_data(history=history)
    message_answer = await message.answer(f'Добавлено в историю: {message.text}\n\n', reply_markup=get_keyboard('conversation_kb', back=True))
    await state.update_data(delete_messege=[message_answer.message_id])

@dp.callback_query(F.data == button_text_result, StateFilter(UserStates.get_menu))
async def get_result(callback: CallbackQuery, state: FSMContext):
    bot_logger.info(f'Конечный ответ: пользователь  {callback.message.chat.id}, время: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')
    user_data = await state.get_data() 
    await safe_delete_messages(callback.message.chat.id, user_data.get("delete_messege", []))
    user_data = await state.get_data()
    agents = user_data.get("agents", '[робот], спец по космосу')
    theme = user_data.get("theme", 'Расскажи про космос')
    history = user_data.get("history", [])
    wait_message = await callback.message.answer('Подведение итогов')
    result_text = api.get_result(agents, theme, history)
    await safe_delete_messages(callback.message.chat.id, [wait_message.message_id])
    await callback.message.answer(f'{result_text}\n\n')
    await state.clear()
    await new_start_handler(callback.message, state)

if __name__ == "__main__":
    try:
        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        print(f"Error: {e}")

