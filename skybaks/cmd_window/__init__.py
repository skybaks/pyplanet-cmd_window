import logging

from pyplanet.apps.config import AppConfig
from pyplanet.contrib.command import Command

from .views import CommandView

logger = logging.getLogger(__name__)

class CmdWindowApp(AppConfig):
    game_dependencies = ["trackmania_next", "trackmania", "shootmania"]
    app_dependencies = ["core.maniaplanet", "core.trackmania", "core.shootmania"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def on_start(self) -> None:
        await self.instance.command_manager.register(
            Command(command="cmd", target=self._command_cmd,
                    description="Open the command window. Used for sending commands to the server longer than the chat message limit")
        )

    async def _command_cmd(self, player, data, **kwargs) -> None:
        view = CommandView(self)
        await view.display(player)
