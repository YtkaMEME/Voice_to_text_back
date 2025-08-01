from aiogram.fsm.state import State, StatesGroup

class FileUploadState(StatesGroup):
    waiting_upload = State()