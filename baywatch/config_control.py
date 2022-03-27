from __future__ import annotations

from rich.align import Align

from textual.app import App
from textual.reactive import Reactive
from textual.widgets import Footer, Static
from textual.message import Message

from textual_inputs import TextInput

import os
import json


CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'data/conf.json')
SIDEBAR_SIZE = 60

class Dict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Configuration(object):
    """JSON configuration object"""

    def __init__(self, file_path: str, live=True) -> None:
        self.path = file_path
        with open(self.path, 'r') as f:
            self.data = Dict(json.load(f))
        self.live = live

    def add(self, key: str, value: str) -> bool:
        try:
            self.data[key] = value
            if self.live: self.__update()
            return True
        except:
            return False

    def delete(self, key: str) -> bool:
        try:
            del self.data[key]
            if self.live: self.__update()
            return True
        except:
            return False

    def __update(self) -> None:
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def write(self):
        self.__update()

class ConfigUpdateForm(App):
    """Interface for modifying JSON configuration."""

    current_index: Reactive[int] = Reactive(-1)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = Configuration(CONFIG_PATH, live=False)
        self.tab_index = [f for f in self.config.data if type(self.config.data[f]) != dict]
        for f in self.config.data:
            if type(self.config.data[f]) == dict and 'categories' not in f.lower():
                for sf in self.config.data[f]:
                    self.tab_index.append('{}.{}'.format(f, sf))
        self.log(str(self.config.data))

    show_sidebar = Reactive(False)

    async def on_load(self) -> None:
        await self.bind("enter", "submit", "Submit")
        await self.bind("s", "save_config", "Save")
        await self.bind("ctrl+s", "save_config", show=False)
        await self.bind("q", "quit", "Quit")
        await self.bind("escape", "reset_focus", show=False)
        await self.bind("ctrl+i", "next_tab_index", show=False)
        await self.bind("shift+tab", "previous_tab_index", show=False)

    async def on_mount(self) -> None:

        await self.view.dock(Footer(), edge="bottom")

        self.inputs = {f: TextInput(name=f, title=self.title_case(f), placeholder=v) for f,v in self.config.data.items() if type(self.config.data[f]) != dict}
        for f in self.config.data:
            if type(self.config.data[f]) == dict and 'categories' not in f.lower():
                for sf, v in self.config.data[f].items():
                    name = '{}.{}'.format(f, sf)
                    title = self.title_case('{} ({})'.format(sf, f))
                    placeholder = str(v),
                    self.inputs[name] = TextInput(name=name, title=title, placeholder=placeholder)

        for i in self.inputs.values():
            i.on_change_handler_name = 'handle_form_change'

        self.header = Static(
            renderable = Align(
                f'[white]Configuration [/][magenta]\[{CONFIG_PATH}]', align='center'
            )
        )
        await self.view.dock(self.header, *[i for i in self.inputs.values()], edge='top')

    async def action_next_tab_index(self) -> None:
        """Changes the focus to the next form field"""
        if self.current_index < len(self.tab_index) - 1:
            self.current_index += 1
            await self.inputs[self.tab_index[self.current_index]].focus()

    async def action_previous_tab_index(self) -> None:
        """Changes the focus to the previous form field"""
        if self.current_index > 0:
            self.current_index -= 1
            await self.inputs[self.tab_index[self.current_index]].focus()

    async def action_submit(self) -> None:

        await self.header.update(
            Align(
                "[white]Configuration changed[/] [red]\[not saved]", align='center'
            )
        )

    async def action_reset_focus(self) -> None:
        self.current_index = -1
        await self.header.focus()

    async def handle_input_on_focus(self, message: Message) -> None:
        self.current_index = self.tab_index.index(message.sender.name)

    async def handle_form_change(self, message: Message) -> None:
        if message.sender.value == 'none' or message.sender.value == 'null' or message.sender.value == '':
            value = None
        elif message.sender.value.lower() == 'true':
            value = True
        elif message.sender.value.lower() == 'false':
            value = False
        elif message.sender.value.isdigit():
            value = int(message.sender.value)
        else:
            value = message.sender.value

        if '.' in message.sender.name:
            names = message.sender.name.split('.')
            self.config.data[names[0]][names[1]] = value
        else:
            self.config.data[message.sender.name] = value
        self.log(f"{message.sender.title} Field Contains: {value}")

    @staticmethod
    def title_case(input_string: str) -> str:
        return input_string.replace('_',' ').replace('-',' ').title()

    async def action_save_config(self):
        self.config.write()
        await self.header.update(
            Align(
                "[green bold]Configuration Saved", align='center'
            )
        )

def main():
    ConfigUpdateForm.run(title="baywatch config")

if __name__ == "__main__":
    main()
