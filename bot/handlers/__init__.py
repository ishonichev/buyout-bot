"""Обработчики событий бота."""
from bot.handlers import client as client_new
from bot.handlers import admin as admin_new
from bot.handlers import support

__all__ = ['client_new', 'admin_new', 'support']
