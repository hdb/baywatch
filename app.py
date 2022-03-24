from __future__ import annotations
from typing import Any

import bay

import rich
from rich.panel import Panel
from rich.console import RenderableType

from textual import events
from textual.app import App
from textual.widgets import Placeholder, ButtonPressed
from textual.widget import Widget, Reactive

from textual_inputs import TextInput
from ck_widgets_lv import ListViewUo

import subprocess
import pyperclip
import json
import logging


logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s %(message)s', level=logging.INFO)


class Dict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Configuration(object):
    """JSON configuration object"""

    def __init__(self, file_path: str) -> None:
        self.path = file_path
        with open(self.path, 'r') as f:
            self.data = Dict(json.load(f))

    def add(self, key: str, value: str) -> bool:
        try:
            self.data[key] = value
            self.__update()
            return True
        except:
            return False

    def delete(self, key: str) -> bool:
        try:
            del self.data[key]
            self.__update()
            return True
        except:
            return False

    def __update(self) -> None:
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)


class SearchResult(Widget, can_focus=True):

    has_focus: Reactive[bool] = Reactive(False)
    mouse_over: Reactive[bool] = Reactive(False)
    style: Reactive[str] = Reactive("")
    height: Reactive[int | None] = Reactive(None)

    def __init__(self, *, data: dict | None = None, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height
        self.data = data

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name
        yield "has_focus", self.has_focus, False
        yield "mouse_over", self.mouse_over, False

    def render(self) -> RenderableType:
        if self.data is None: return self.render_empty()
        return Panel(
            f"[white]{self.data['category_name']}[/]\n[cyan]{self.data['magnet']}[/]",
            title=f"[bold blue]{self.data['name']}[/]",
            title_align="left",
            border_style="magenta" if not self.has_focus else "yellow",
            subtitle=f"[blue]{self.data['num_files']} file{'s' if int(self.data['num_files']) > 1 else ''}[/] | [blue]{self.data['size']}[/] | [green]{self.data['seeders']}[/] | [red]{self.data['leechers']}[/]",
            subtitle_align="right",
        )

    def render_empty(self) -> RenderableType:
        return Panel(
            f"[bold red]No results[/]",
            border_style="red",
        )

    async def on_focus(self, event: events.Focus) -> None:
        self.has_focus = True

    async def on_blur(self, event: events.Blur) -> None:
        self.has_focus = False

    async def on_enter(self, event: events.Enter) -> None:
        self.mouse_over = True

    async def on_leave(self, event: events.Leave) -> None:
        self.mouse_over = False

    async def on_key(self, event: events.Key) -> None:
        self.key = event.key
        logging.info(str(event))
        if event.key == 'k':
            pass
        elif event.key == 'p':
            event.prevent_default().stop()
            await self.emit(ButtonPressed(self))
        elif event.key == 'c':
            self.copy_link()

    def copy_link(self) -> None: # on "c"
        pyperclip.copy(self.data['magnet'])


class TPBSearch(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config_path = 'conf.json'
        self.config = Configuration(config_path)
        self.client = bay.Bay(self.config.data.mirror)

    async def on_load(self, event: events.Load):
        await self.bind("enter", "submit", "Submit")
        await self.bind("b", "toggle_sidebar", "Toggle sidebar")
        await self.bind("q", "quit", "Quit")

    show_bar = Reactive(False)

    async def on_mount(self, event: events.Mount) -> None:
        """Create a grid with auto-arranging cells."""
        self.text_input = TextInput(
            name="code",
            title="Pirate Search",
        )

        self.bar = Placeholder(name="left")
        await self.view.dock(self.bar, edge="left", size=40, z=1)
        self.bar.layout_offset_x = -40

        await self.view.dock(self.text_input, edge='top', size=4)

    async def action_submit(self):
        with self.console.status("Searching"):
            #search
            search_term = self.text_input.value
            results = self.client.search(search_term)

            # clear widgets
            self.view.layout.docks.clear()
            self.view.widgets.clear()

            # re-add widgets
            await self.view.dock(self.text_input, edge='top', size=4)
            await self.view.dock(self.bar, edge="left", size=40, z=1)

            # build search results
            await self.view.dock(ListViewUo([SearchResult(data=r) for r in results]))

    async def on_shutdown_request(self, event) -> None:
        await self.client.close()
        await self.close_messages()

    async def handle_button_pressed(self, message: ButtonPressed) -> None:

        # Play on 'p'
        if message.sender.key == 'p':
            command = self.config.data.command_multifile if int(message.sender.data['num_files']) > 1 else self.config.data.command
            await self.shutdown_and_run(command.format(message.sender.data['magnet']))

    def watch_show_bar(self, show_bar: bool) -> None:
        """Called when show_bar changes."""
        self.bar.animate("layout_offset_x", 0 if show_bar else -40)

    def action_toggle_sidebar(self) -> None:
        """Called when user hits 'b' key."""
        self.show_bar = not self.show_bar

    async def shutdown_and_run(self, command: str, detach: bool = False):
        command = 'sleep 1 && {}{}'.format(command, ' &' if detach else '')
        logging.info('running {}'.format(command))
        subprocess.run(command, shell=True)
        await self.shutdown()

def main():
    TPBSearch.run()

if __name__ == '__main__':
    main()
