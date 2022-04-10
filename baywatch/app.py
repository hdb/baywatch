from __future__ import annotations

from baywatch.bay import Bay
from baywatch.config_control import ConfigUpdateForm, Configuration
from baywatch.version import __version__

import rich
from rich.panel import Panel
from rich.align import Align
from rich.console import RenderableType
from rich.text import Text
from rich.table import Table

from textual import events
from textual.app import App
from textual.widgets import ButtonPressed, Footer
from textual.widget import Widget, Reactive
from textual.message import Message
from textual_inputs import TextInput

from pyfiglet import Figlet
import subprocess
from transmission_rpc import Client as Transmission
import pyperclip
import asyncio
import os
import argparse

try:
    from ck_widgets_lv import ListViewUo
except:
    print('ck_widgets.ListViewUo is a required dependency not included in pypi install\n')
    print('install using pip:\n\n\tpip install git+https://github.com/Cvaniak/TextualListViewUnofficial.git\n')
    exit()


MIRROR_SIDEBAR_SIZE = 35
FILE_SIDEBAR_SIZE = 80
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'data/conf.json')


class TitleWidget(Widget, can_focus=True):
    """Widget displays title on open"""

    def __init__(self, *, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name

    def render(self) -> RenderableType:
        return Align(
            f"[magenta]{self.generate_title()}[/]", vertical='middle', align='center', pad=False
        )

    def generate_title(self, figlet_font: str = 'shadow') -> None:
        return Text(
            Figlet(figlet_font).renderText('{}'.format(self.name)),
            no_wrap=True,
            overflow='crop',
        )


class SearchResult(Widget, can_focus=True):
    """Search result item; handles key press actions on focus"""

    has_focus: Reactive[bool] = Reactive(False)

    def __init__(self, *, data: dict | None = None, idx: int | None = None, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height
        self.data = data
        self.idx = idx

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name
        yield "has_focus", self.has_focus, False

    def render(self) -> RenderableType:
        if self.data is None: return self.render_empty()
        return Panel(
            Text.assemble((self.data['category_name'], "white"), "\n", (self.data['magnet'], 'cyan'), no_wrap=True, overflow='ellipsis'),
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
        self.key = 'focus'
        await self.emit(ButtonPressed(self))

    async def on_blur(self, event: events.Blur) -> None:
        self.has_focus = False

    async def on_key(self, event: events.Key) -> None:
        self.key = event.key
        if event.key == 'f':
            event.prevent_default().stop()
            await self.emit(ButtonPressed(self))
        elif event.key == 'p':
            event.prevent_default().stop()
            await self.emit(ButtonPressed(self))
        elif event.key == 'd':
            event.prevent_default().stop()
            await self.emit(ButtonPressed(self))
        elif event.key == 'c':
            pyperclip.copy(self.data['magnet'])


class MirrorSidebar(Widget):
    """Display site mirror connection and response time"""

    def __init__(self, *, client: Bay | None = None, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height
        self.client = client
        self.response_time = None
        self.footer = self.build_footer()

    def build_footer(self) -> Text:
        """Replicate footer for sidebar for actions only available when visible"""

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
        self.response_time = self.client.get_active_mirror_response()

    async def update_mirror(self) -> Bay:
        with self.console.status('Getting mirrors'):
            self.client.update_mirror()
            self.get_response_time()
        return self.client

class FilesSidebar(Widget):
    """Display details of search result item"""

    def __init__(self, *, data: dict | None = None, user: dict | None = None, name: str | None = None, height: int | None = None) -> None:
        super().__init__(name=name)
        self.height = height
        self.data = data
        self.user = user

    def render(self) -> RenderableType:
        if self.data is None or self.user is None: return self.render_empty()
        if len(self.data) == 0 and self.user is not None: return self.render_no_files()
        user_color = '' if self.user is None else 'green' if self.user['status'] == 'vip' else 'magenta' if self.user['status'] == 'trusted' else 'white'
        return Panel(
            Align(self.build_table(), vertical='middle'),
            border_style="blue",
            title='Files',
            subtitle=f"uploaded by [{user_color}]{self.user['username']}[/]" if self.user is not None else None,
            subtitle_align='right'
        )

    def render_empty(self) -> RenderableType:
        return Panel(
            "",
            border_style="red",
        )

    def render_no_files(self) -> RenderableType:
        user_color = '' if self.user is None else 'green' if self.user['status'] == 'vip' else 'magenta' if self.user['status'] == 'trusted' else 'white'
        return Panel(
            Align('[red]File list not available[/]', vertical='middle', align='center'),
            title='Files',
            border_style="blue",
            subtitle=f"uploaded by [{user_color}]{self.user['username']}[/]" if self.user is not None else None,
            subtitle_align='right'
        )

    def update_data(self, files_data: list | None, user: dict | None) -> None:
        """Receive file and upload user data"""

        self.data = files_data
        self.user = user

    def build_table(self) -> Table:
        table = Table('[blue]#', '[blue]Filename', '[blue]Size', box=None, show_lines=True, min_width=FILE_SIDEBAR_SIZE)
        for i, row in enumerate(self.data):
            color = 'blue' if i%2==1 else 'white'
            table.add_row(str(i+1), row['name'], row['size'], style=color)
        return table


class Baywatch(App):
    """Main app"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = Configuration(CONFIG_PATH)
        self.client = Bay(self.config.data.mirror, user_agent=self.config.data.user_agent.format(__version__))
        self.display_title = 'baywatch'
        self.transmission_client = None

    async def on_load(self, event: events.Load) -> None:
        """Register keybindings + dummy keybindings for widget events"""

        await self.bind("enter", "submit", "Search")
        await self.bind("m", "toggle_mirror_sidebar", "Mirror info")
        await self.bind("f", "toggle_files_sidebar", "Files info")
        await self.bind("r", "refresh_mirror", "Refresh mirror", show=False)
        await self.bind("p", "pass", "Play")
        await self.bind("d", "pass", "Download")
        await self.bind("c", "copy_link", "Copy link")
        await self.bind("q", "quit", "Quit")
        await self.bind("ctrl+q", "quit", show=False)

        await self.bind("escape", "reset_focus", show=False)
        await self.bind("ctrl+i", "next_tab_index", show=False)
        await self.bind("shift+tab", "previous_tab_index", show=False)

    show_mirror_bar = Reactive(False)
    show_files_bar = Reactive(False)

    async def on_mount(self, event: events.Mount) -> None:
        """Initialize widgets"""

        self.search_bar = TextInput(
            name="search_bar",
            title="Search",
        )

        self.footer = Footer()
        await self.view.dock(self.footer, edge="bottom")

        self.mirror_sidebar = MirrorSidebar(name="mirror", client=self.client)
        await self.view.dock(self.mirror_sidebar, edge="left", size=MIRROR_SIDEBAR_SIZE, z=1)
        self.mirror_sidebar.layout_offset_x = -MIRROR_SIDEBAR_SIZE

        self.files_sidebar = FilesSidebar(name="files")
        await self.view.dock(self.files_sidebar, edge="right", size=FILE_SIDEBAR_SIZE, z=2)
        self.files_sidebar.layout_offset_x = FILE_SIDEBAR_SIZE

        await self.view.dock(self.search_bar, edge='top', size=4)

        self.title_text = TitleWidget(name=self.display_title)
        await self.view.dock(self.title_text)

        self.tab_index = ['search_bar', 'title_text']
        self.current_index = -1

    async def action_submit(self) -> None:
        """Search bar submit"""

        with self.console.status("Searching"):
            #search
            search_term = self.search_bar.value
            self.log(f'searching "{search_term}"')
            results = self.client.search(search_term)
            self.log(f'{len(results)} found for "{search_term}"')

            # build search results
            self.search_results = ListViewUo([SearchResult(data=r, idx=i) for i, r in enumerate(results)])

            # clear widgets
            self.view.layout.docks.clear()
            self.view.widgets.clear()

            # re-add widgets
            await self.view.dock(self.mirror_sidebar, edge="left", size=MIRROR_SIDEBAR_SIZE, z=1)
            await self.view.dock(self.files_sidebar, edge="right", size=FILE_SIDEBAR_SIZE, z=2)
            await self.view.dock(self.search_bar, edge='top', size=4)
            await self.view.dock(self.footer, edge="bottom")
            await self.view.dock(self.search_results)

            # build tab index
            self.build_tab_index()

    def build_tab_index(self) -> None:
        """Tab-index search bar and search result widgets"""

        tab_index = ['search_bar']
        if hasattr(self, 'search_results'):
            tab_index += ['search_results[{}]'.format(i) for i in range(len(self.search_results.widgets_list))]
        self.tab_index = tab_index
        self.current_index = 0

    async def add_transmission_client(self) -> bool:
        """Set-up transmission connection"""

        try:
            self.transmission_client = Transmission(
                username=self.config.data.transmission['username'],
                password=self.config.data.transmission['password'],
                host=self.config.data.transmission['host'],
                port=self.config.data.transmission['port'],
            )
            return True
        except Exception as e:
            self.log(e)
            if self.config.data.transmission['try_open']:
                self.log('trying to open {}'.format(self.config.data.transmission['command']))
                try:
                    subprocess.run('{} >/dev/null 2>&1 &'.format(self.config.data.transmission['command']), shell=True)
                    await asyncio.sleep(1)
                    self.transmission_client = Transmission(
                        username=self.config.data.transmission['username'],
                        password=self.config.data.transmission['password'],
                        host=self.config.data.transmission['host'],
                        port=self.config.data.transmission['port'],
                    )
                    return True
                except Exception as e:
                    self.log('could not open {}'.format(self.config.data.transmission['command']))
                    self.log(e)
                    return False
            else:
                return False

    async def action_refresh_mirror(self) -> None:
        """Get fastest available mirror"""

        if self.show_mirror_bar:
            self.client = await self.mirror_sidebar.update_mirror()
            self.config.add('mirror', self.client.mirror)
            self.log('mirror updated to {}'.format(self.client.mirror))

    async def action_pass(self) -> None:
        """Dummy action to render widget key events in footer"""

        return None

    async def action_copy_link(self) -> None:
        """Copy result link to clipboard"""

        if type(self.focused) == SearchResult:
            await self.highlight_footer_key('c')

    async def highlight_footer_key(self, key: str) -> None:
        """Force highlight footer key for visual feedback"""

        self.footer.highlight_key = key
        await self.footer.call_later(self.unhighlight_footer_key)

    async def unhighlight_footer_key(self) -> None:
        await asyncio.sleep(.3)
        self.footer.highlight_key = None

    async def handle_button_pressed(self, message: ButtonPressed) -> None:
        """Receive events from widgets"""

        # Play on 'p'
        if message.sender.key == 'p' and isinstance(message.sender, SearchResult):
            self.log(f"playing {message.sender.data['id']}: {message.sender.data['name']}")
            command = self.config.data.play_multifile if int(message.sender.data['num_files']) > 1 else self.config.data.command
            if '{}' not in command:
                command = '{} \'{}\''.format(command,'{}')
            await self.shutdown_and_run(command.format(message.sender.data['magnet']))

        # Show files on 'f'
        elif message.sender.key == 'f' and isinstance(message.sender, SearchResult):
            self.log(f"showing files for {message.sender.data['id']}: {message.sender.data['name']}")
            file_names = self.client.filenames(message.sender.data['id'])
            user = {'username': message.sender.data['username'], 'status': message.sender.data['status']}
            self.files_sidebar.update_data(file_names, user)
            self.log(file_names)
            self.log(user)
            self.action_toggle_files_sidebar()

        # Download on 'd'
        elif message.sender.key == 'd' and isinstance(message.sender, SearchResult):
            if self.transmission_client is None:
                transmission_added = await self.add_transmission_client()
                if not transmission_added:
                    #TODO add failure notification if transmission settings not configured correctly
                    self.log(f"unable to download torrent {message.sender.data['id']}: {message.sender.data['name']}")
                    return None
            self.log(f"downloading {message.sender.data['id']}: {message.sender.data['name']}")
            await self.highlight_footer_key('d')
            await self.download(message.sender.data['magnet'])

        # Triggered on widget focus
        elif message.sender.key == 'focus' and isinstance(message.sender, SearchResult):
            await self.handle_searchresult_on_focus(message)

    async def download(self, magnet: str) -> None:
        """Trigger transmission download"""

        self.transmission_client.add_torrent(magnet)

    def watch_show_mirror_bar(self, show_mirror_bar: bool) -> None:
        """Show/hide mirror sidebar"""

        self.mirror_sidebar.animate("layout_offset_x", 0 if show_mirror_bar else -MIRROR_SIDEBAR_SIZE)

    def action_toggle_mirror_sidebar(self) -> None:
        """Trigger show/hide mirror sidebar"""

        if not self.show_mirror_bar: self.mirror_sidebar.get_response_time()
        if self.show_files_bar: self.show_files_bar = False
        self.show_mirror_bar = not self.show_mirror_bar

    def watch_show_files_bar(self, show_files_bar: bool) -> None:
        """Show/hide files sidebar"""

        self.files_sidebar.animate("layout_offset_x", 0 if show_files_bar else FILE_SIDEBAR_SIZE)

    def action_toggle_files_sidebar(self) -> None:
        """Trigger show/hide files sidebar"""

        if self.files_sidebar.data is None: return None
        if self.show_mirror_bar: self.show_mirror_bar = False
        self.show_files_bar = not self.show_files_bar

    async def action_next_tab_index(self) -> None:
        """Change tab index to the next widget and focus"""

        if self.show_mirror_bar or self.show_files_bar: return None
        self.current_index += 1 if self.current_index < (len(self.tab_index) - 1) else -1
        await self.assign_tab_focus()

    async def action_previous_tab_index(self) -> None:
        """Change tab index to the previous widget and focus"""

        if self.show_mirror_bar or self.show_files_bar: return None
        self.current_index -= 1 if self.current_index > 0 else len(self.tab_index) - 1
        await self.assign_tab_focus()

    async def assign_tab_focus(self) -> None:
        """Set focus to current tab index"""

        idx = self.tab_index[self.current_index]
        if idx.startswith('search_results'):
            widget = self.search_results.widgets_list[int(idx.split('[')[1].split(']')[0])]
            await widget.focus()
            if not widget.visible:
                self.search_results.page_down() # TODO
        else:
            await getattr(self, idx).focus()

    async def action_reset_focus(self) -> None:
        """Removes focus from any widget"""

        self.current_index = -1
        await self.set_focus(None)

    async def handle_input_on_focus(self, message: Message) -> None:
        """Update current index when search bar is focused"""

        self.current_index = self.tab_index.index(message.sender.name)

    async def handle_searchresult_on_focus(self, message: ButtonPressed) -> None:
        """Update current index when search result is focused"""

        self.current_index = message.sender.idx+1

    async def shutdown_and_run(self, command: str, detach: bool = False) -> None:
        """Quit app and run command on exit"""

        self.log('running {}'.format(command))
        command = 'sleep 1 && {}{}'.format(command, ' &' if detach else '')
        subprocess.run(command, shell=True)
        await self.shutdown()

def parse() -> argparse.Namespace:
    """Argument parser; options for launching configuration editor or enabling logs"""

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="configure settings", action="store_true")
    parser.add_argument("-l", "--log", help=".log file to log actions", nargs='?', default=None)
    return parser.parse_args()

def main():
    args = parse()
    if args.config:
        ConfigUpdateForm.run(title='baywatch config', log=args.log)
    else:
        Baywatch.run(title='baywatch', log=args.log)

if __name__ == '__main__':
    main()
