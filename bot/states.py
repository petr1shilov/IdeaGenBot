from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    get_agents = State()
    get_menu = State()
    get_theme = State()
    get_add_replica = State()