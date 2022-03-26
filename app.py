from __future__ import annotations
from typing import Any

import bay

import rich
from rich.panel import Panel
from rich.align import Align
from rich.console import RenderableType
from rich.text import Text
from rich.table import Table

from textual import events
from textual.app import App
from textual.widgets import ButtonPressed, Footer, Placeholder
from textual.widget import Widget, Reactive

from textual_inputs import TextInput
from ck_widgets_lv import ListViewUo

from pyfiglet import Figlet
import subprocess
import pyperclip
import json
import logging


logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s %(message)s', level=logging.INFO)

MIRROR_SIDEBAR_SIZE = 35
FILE_SIDEBAR_SIZE = 80


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


class TitleWidget(Widget, can_focus=True):
    mouse_over: Reactive[bool] = Reactive(False)

    def __init__(self, *, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name
        yield "mouse_over", self.mouse_over, False

    def render(self) -> RenderableType:
        return Align(
            f"[magenta]{self.generate_title()}[/]", vertical='middle', align='center', pad=False
        )

    def generate_title(self, figlet_font='shadow'):
        return Text(
            Figlet(figlet_font).renderText('{}'.format(self.name)),
            no_wrap=True,
            overflow='crop',
        )

    async def on_enter(self, event: events.Enter) -> None:
        self.mouse_over = True

    async def on_leave(self, event: events.Leave) -> None:
        self.mouse_over = False


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
        if event.key == 'f':
            event.prevent_default().stop()
            await self.emit(ButtonPressed(self))
        elif event.key == 'p':
            event.prevent_default().stop()
            await self.emit(ButtonPressed(self))
        elif event.key == 'c':
            self.copy_link()

    def copy_link(self) -> None: # on "c"
        pyperclip.copy(self.data['magnet'])

class MirrorSidebar(Widget):

    def __init__(self, *, client: bay.Bay | None = None, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height
        self.client = client
        self.response_time = None
        self.footer = self.build_footer()

    def build_footer(self) -> Text:
        footer = Text(
            no_wrap=True,
            overflow="ellipsis",
            justify="left",
            end="",
        )

        footer.append(Text.assemble(
            (f" R ", "default on default"),
            f" Refresh mirror ",
            meta={"@click": f"app.press('{'r'}')", "key": 'r'},
        ))

        return footer

    def render(self) -> RenderableType:
        return Panel(
            Align.center(
                f"[magenta]{self.client.mirror}[/]\n[blue]{self.response_time} sec[/]", vertical='middle'
            ),
            title=f"[bold blue]Mirror[/]",
            border_style="blue",
            subtitle=self.footer,
        )

    def get_response_time(self) -> None:
        self.response_time = self.client.getActiveMirrorResponse()

    async def update_mirror(self) -> bay.Bay:
        with self.console.status('Getting mirrors'):
            self.client.updateMirror()
            self.get_response_time()
        return self.client

class FilesSidebar(Widget):
    def __init__(self, *, data: dict | None = None, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height
        self.data = data

    def render(self) -> RenderableType:
        if self.data is None: return self.render_empty()
        return Panel(
            Align(self.build_table(), vertical='middle'),
            border_style="blue",
            title='Files',
        )

    def render_empty(self) -> RenderableType:
        return Panel(
            "",
            border_style="red",
        )

    def update_data(self, data) -> None:
        self.data = data

    def build_table(self) -> Table:
        table = Table('[blue]#', '[blue]Filename', '[blue]Size', box=None, show_lines=True, min_width=FILE_SIDEBAR_SIZE)
        for i, row in enumerate(self.data):
            color = 'blue' if i%2==1 else 'white'
            table.add_row(str(i+1), row['name'], row['size'], style=color)
        return table


class TPBSearch(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config_path = 'conf.json'
        self.config = Configuration(config_path)
        self.client = bay.Bay(self.config.data.mirror)
        self.display_title = 'baywatch'

    async def on_load(self, event: events.Load):
        await self.bind("enter", "submit", "Search")
        await self.bind("m", "toggle_mirror_sidebar", "Mirror info")
        await self.bind("f", "toggle_files_sidebar", "Files info")
        await self.bind("r", "refresh_mirror", "Refresh mirror", show=False)
        await self.bind("p", "pass", "Play")
        await self.bind("c", "pass", "Copy link")
        await self.bind("q", "quit", "Quit")

    show_mirror_bar = Reactive(False)
    show_files_bar = Reactive(False)

    async def on_mount(self, event: events.Mount) -> None:
        """Create a grid with auto-arranging cells."""
        self.text_input = TextInput(
            name="code",
            title="Pirate Search",
        )

        await self.view.dock(Footer(), edge="bottom")

        self.mirror_sidebar = MirrorSidebar(name="mirror", client=self.client)
        await self.view.dock(self.mirror_sidebar, edge="left", size=MIRROR_SIDEBAR_SIZE, z=1)
        self.mirror_sidebar.layout_offset_x = -MIRROR_SIDEBAR_SIZE

        self.files_sidebar = FilesSidebar(name="files")
        await self.view.dock(self.files_sidebar, edge="right", size=FILE_SIDEBAR_SIZE, z=2)
        self.files_sidebar.layout_offset_x = FILE_SIDEBAR_SIZE

        await self.view.dock(self.text_input, edge='top', size=4)

        self.title_text = TitleWidget(name=self.display_title)
        await self.view.dock(self.title_text)

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
            await self.view.dock(self.mirror_sidebar, edge="left", size=MIRROR_SIDEBAR_SIZE, z=1)
            await self.view.dock(self.files_sidebar, edge="right", size=FILE_SIDEBAR_SIZE, z=2)
            await self.view.dock(Footer(), edge="bottom")

            # build search results
            await self.view.dock(ListViewUo([SearchResult(data=r) for r in results]))

    async def action_refresh_mirror(self) -> None:
        if self.show_mirror_bar:
            self.client = await self.mirror_sidebar.update_mirror()
            self.config.add('mirror', self.client.mirror)
            logging.info('mirror updated to {}'.format(self.client.mirror))

    async def action_pass(self) -> None:
        return None

    async def on_shutdown_request(self, event) -> None:
        await self.client.close()
        await self.close_messages()

    async def handle_button_pressed(self, message: ButtonPressed) -> None:

        # Play on 'p'
        if message.sender.key == 'p' and isinstance(message.sender, SearchResult):
            command = self.config.data.command_multifile if int(message.sender.data['num_files']) > 1 else self.config.data.command
            await self.shutdown_and_run(command.format(message.sender.data['magnet']))

        # Show files on 'f'
        elif message.sender.key == 'f' and isinstance(message.sender, SearchResult):
            file_names = self.client.filenames(message.sender.data['id'])
            self.files_sidebar.update_data(file_names)
            self.action_toggle_files_sidebar()

    def watch_show_mirror_bar(self, show_mirror_bar: bool) -> None:
        """Called when show_mirror_bar changes."""
        self.mirror_sidebar.animate("layout_offset_x", 0 if show_mirror_bar else -MIRROR_SIDEBAR_SIZE)

    def action_toggle_mirror_sidebar(self) -> None:
        """Called when user hits 'm' key."""
        if not self.show_mirror_bar: self.mirror_sidebar.get_response_time()
        if self.show_files_bar: self.show_files_bar = False
        self.show_mirror_bar = not self.show_mirror_bar

    def watch_show_files_bar(self, show_files_bar: bool) -> None:
        """Called when show_files_bar changes."""
        self.files_sidebar.animate("layout_offset_x", 0 if show_files_bar else FILE_SIDEBAR_SIZE)

    def action_toggle_files_sidebar(self) -> None:
        """Called when user hits 'f' key."""
        if self.files_sidebar.data is None: return None
        if self.show_mirror_bar: self.show_mirror_bar = False
        self.show_files_bar = not self.show_files_bar

    async def shutdown_and_run(self, command: str, detach: bool = False):
        command = 'sleep 1 && {}{}'.format(command, ' &' if detach else '')
        logging.info('running {}'.format(command))
        subprocess.run(command, shell=True)
        await self.shutdown()

def main():
    TPBSearch.run()

if __name__ == '__main__':
    main()
