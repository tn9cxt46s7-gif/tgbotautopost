from aiogram.fsm.state import State, StatesGroup


class AdCreate(StatesGroup):
    text = State()
    photo = State()
    price = State()


class AdEdit(StatesGroup):
    text = State()
    price = State()


class GroupAdd(StatesGroup):
    waiting = State()


class GroupSettings(StatesGroup):
    interval = State()


class UserSettings(StatesGroup):
    quiet_hours = State()
    default_interval = State()


class SupportChat(StatesGroup):
    chatting = State()


class AdminReply(StatesGroup):
    waiting = State()


class AdminGiveSub(StatesGroup):
    user_id = State()
    days = State()


class AdminFindUser(StatesGroup):
    query = State()


class AdminBroadcast(StatesGroup):
    message = State()
    confirm = State()
