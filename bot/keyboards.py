from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.texts import *

keyboards = {
              "empty": [[]], 
              "start_kb": [
                            [button_text_agents], 
                            [button_text_theme],
                            [button_text_gen_menu],
                          ],
              "conversation_kb": [
                                  [button_text_gen],
                                  [button_text_add_replica],
                                  [button_text_result]
                                ]
              }


def get_keyboard(name: str, back: bool = False):
    if name not in keyboards:
        raise ValueError(f"Invalid name of keybord: {name}")
    current_keybord = []
    for key in keyboards[name]:
        current_keybord.append(
            [
                InlineKeyboardButton(text=text_key, callback_data=f"{text_key}")
                for text_key in key
            ]
        )
    if back:
        back_text = button_back_text
        current_keybord.append(
            [InlineKeyboardButton(text=back_text, callback_data=f"{back_text}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=current_keybord)