from aiogram import Router
from aiogram.filters import Command

from services.bot.src.commande.start import cmd_start
from services.bot.src.commande.status import cmd_status
from services.bot.src.commande.run import cmd_run
from services.bot.src.commande.stop import cmd_stop
from services.bot.src.commande.next import cmd_next
from services.bot.src.commande.result import cmd_result

# Crée un router central
router = Router()

# Enregistrement des handlers avec Command filter
router.message.register(cmd_start, Command(commands=["start", "help"]))
router.message.register(cmd_status, Command(commands=["status"]))
router.message.register(cmd_run, Command(commands=["run"]))
router.message.register(cmd_stop, Command(commands=["stop"]))
router.message.register(cmd_next, Command(commands=["next"]))
router.message.register(cmd_result, Command(commands=["result"]))
