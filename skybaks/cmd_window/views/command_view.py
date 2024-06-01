import logging
import json

from pyplanet.views.template import TemplateView
from pyplanet.apps.core.maniaplanet.models.player import Player

logger = logging.getLogger(__name__)

class PiecemealCommand:
    def __init__(self, count: int) -> None:
        self.count: int = count
        self.parts: "list[str | None]" = [None] * self.count

    @property
    def complete(self) -> bool:
        return all(self.parts)

    @property
    def command(self) -> str:
        return "".join(self.parts)

    def set_part(self, index: int, contents: str) -> None:
        if index >= len(self.parts):
            return
        self.parts[index] = contents


class CommandView(TemplateView):
    template_name = "cmd_window/command.xml"

    def __init__(self, app):
        super().__init__(self)
        self.app = app
        self.manager = app.context.ui
        self.tag = "cmd_window.views.command_view_displayed"
        self.cmds: "dict[int, PiecemealCommand]" = dict()
        self.window_minimized: bool = False
        self.clear_input: bool = True
        self.subscribe("cmd_button_close", self.close)
        self.subscribe("cmd_button_minmax", self.toggle_minmax)
        self.subscribe("cmd_transmit_server_data", self.receive_command_data)

    async def get_context_data(self):
        context = await super().get_context_data()
        context.update({
            "title": "Pyplanet: Command Window",
            "minmax_button_substyle": "Windowed" if self.window_minimized else "Minimize",
            "minimized": self.window_minimized,
            "clear_input": self.clear_input,
        })
        # Ensure clear_input is only set once
        self.clear_input = False
        return context

    async def refresh(self, player, *args, **kwargs):
        await self.display(player=player)

    async def display(self, player=None):
        login = player.login if isinstance(player, Player) else player
        if not player:
            raise Exception("No player/login given to display to")
        player = (
            player
            if isinstance(player, Player)
            else await self.app.instance.player_manager.get_player(
                login=login, lock=False
            )
        )

        other_view = player.attributes.get(self.tag, None)
        if other_view and isinstance(other_view, str):
            other_manialink = self.app.instance.ui_manager.get_manialink_by_id(
                other_view
            )
            if isinstance(other_manialink, CommandView):
                await other_manialink.close(player)
        player.attributes.set(self.tag, self.id)

        return await super().display(player_logins=[login])

    async def close(self, player, *args, **kwargs):
        if self.player_data and player.login in self.player_data:
            del self.player_data[player.login]
        await self.hide(player_logins=[player.login])
        player.attributes.set(self.tag, None)

    async def toggle_minmax(self, player, *args, **kwargs):
        self.window_minimized = not self.window_minimized
        await self.refresh(player=player)

    async def receive_command_data(self, player, action: str, values: dict, *args, **kwargs):
        cmd_data = json.loads(values.get("cmd", "{}"))
        if cmd_data:
            cmd_id: int = cmd_data["ID"]
            cmd_text_data: str = cmd_data["Data"]
            cmd_index: int = cmd_data["Index"]
            cmd_maxcount: int = cmd_data["Count"]
            if cmd_id not in self.cmds:
                self.cmds[cmd_id] = PiecemealCommand(cmd_maxcount)
            self.cmds[cmd_id].set_part(cmd_index, cmd_text_data)

            if self.cmds[cmd_id].complete:
                await self.app.instance.command_manager.execute(player, self.cmds[cmd_id].command)
                del self.cmds[cmd_id]
                self.clear_input = True
                await self.refresh(player=player)
