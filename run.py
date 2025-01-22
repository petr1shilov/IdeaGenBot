import asyncio

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InputFile,
    CallbackQuery,
    ErrorEvent,
    InputSticker,
    Message,
    ReplyKeyboardRemove,
    ContentType,
    FSInputFile,
)
from aiogram.utils.deep_linking import create_start_link

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


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await message.answer(hello_message_text, reply_markup=None)
    await message.answer(start_message_text, reply_markup=get_keyboard('start_kb'))

@dp.callback_query(F.data == button_text_agents)
async def get_agents(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.get_agents)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text_for_agent, reply_markup=get_keyboard('empty', back=True))

@dp.message(StateFilter(UserStates.get_agents), F.content_type == "text")
async def get_agent_text(message: Message, state: FSMContext):
    await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,  # Указываем ID предыдущего сообщения
            reply_markup=None
        )
    await state.update_data(agents=message.text)
    answer = api.parsing_agents(message.text)
    name_agents = ', '.join(answer.keys())
    await message.answer(f'Вы ввели {len(answer)} агентов:\n{name_agents}\n\n', reply_markup=get_keyboard('start_kb'))

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_agents))
async def get_back_from_agent(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Стартовые настройки\n\n", reply_markup=get_keyboard('start_kb'))

@dp.callback_query(F.data == button_text_theme)
async def get_theme(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(UserStates.get_theme)
    await callback.message.answer(text_for_theme, reply_markup=get_keyboard('empty', back=True))

@dp.message(StateFilter(UserStates.get_theme), F.content_type == "text")
async def get_theme_text(message: Message, state: FSMContext):
    await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            reply_markup=None
        )
    await state.update_data(history=[])
    await state.update_data(first_messege=True)
    text_messege = message.text
    await state.update_data(theme=text_messege)
    await message.answer(f'Тема диалога: {text_messege}\n\n', reply_markup=get_keyboard('start_kb'))

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_theme))
async def get_back_from_theme(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Стартовые настройки\n\n", reply_markup=get_keyboard('start_kb'))

@dp.callback_query(F.data == button_text_gen_menu)
async def get_gen_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(UserStates.get_menu)
    await callback.message.answer("Меню генерации\n\n", reply_markup=get_keyboard('conversation_kb', back=True))

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_menu))
async def get_back_from_gen_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Стартовые настройки\n\n", reply_markup=get_keyboard('start_kb'))

@dp.callback_query(F.data == button_text_gen, StateFilter(UserStates.get_menu))
async def generate_dialog(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_data = await state.get_data()
    agents = user_data["agents"]
    theme = user_data["theme"]
    history = user_data["history"]
    first_messege = user_data["first_messege"]
    print(first_messege)
    content, convers_history = api.get_answer(agents, theme, history, first_messege)
    for answer in content:
        await callback.message.answer(f'{list(answer.keys())[0]}\n{list(answer.values())[0]}\n')
    await state.update_data(history=convers_history)
    await state.update_data(first_messege=False)
    await callback.message.answer("Меню генерации\n\n",reply_markup=get_keyboard('conversation_kb', back=True))
    await state.set_state(UserStates.get_menu)
    
@dp.callback_query(F.data == button_text_add_replica, StateFilter(UserStates.get_menu))
async def add_replica(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(UserStates.get_add_replica)
    await callback.message.answer(text_for_add_replica, reply_markup=get_keyboard('empty', back=True))

@dp.callback_query(F.data == button_back_text, StateFilter(UserStates.get_add_replica))
async def get_back_to_gen_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.get_menu)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Меню генерации\n\n", reply_markup=get_keyboard('conversation_kb', back=True))

@dp.message(StateFilter(UserStates.get_add_replica), F.content_type == "text")
async def add_replica(message: Message, state: FSMContext):
    await state.set_state(UserStates.get_menu)
    user_data = await state.get_data()
    history = user_data["history"] + [{'role': 'user', 'content': message.text}]
    await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,  
            reply_markup=None
        )
    await state.update_data(history=history)
    await message.answer(f'Добавлено в историю: {message.text}\n\n', reply_markup=get_keyboard('conversation_kb', back=True))
    

@dp.callback_query(F.data == button_text_result, StateFilter(UserStates.get_menu))
async def get_result(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    user_data = await state.get_data()
    agents = user_data["agents"]
    theme = user_data["theme"]
    histoty = user_data["history"]
    result_text = api.get_result(agents, theme, histoty)
    await callback.message.answer(f'{result_text}\n\n')
    await callback.message.answer(start_message_text, reply_markup=get_keyboard('start_kb'))
    await state.clear()

# еще глобально надо почистить лишнее в диалоге(проверить что надо удалять в моменте)
# еще надо узнать почему поднятые боты отрубоаются через 2 суток из-за удаления 

if __name__ == "__main__":
    try:
        asyncio.run(dp.start_polling(bot))
    except Exception as e:
        print(f"Error: {e}")

