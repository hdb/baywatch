import bay

from rich.columns import Columns
from rich.panel import Panel
from textual import events
from textual.app import App
from textual.widgets import ScrollView
from textual_inputs import TextInput


class TPBSearch(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.columns = Columns([])
        self.client = bay.Bay(bay.MIRROR)

    async def on_load(self, event: events.Load):
        await self.bind("enter", "submit", "Submit")
        await self.bind("q", "quit", "Quit")

    async def on_mount(self, event: events.Mount) -> None:
        """Create a grid with auto-arranging cells."""
        self.scroll_view = ScrollView(self.columns)
        self.text_input = TextInput(
            name="code",
            title="Pirate Search",
        )

        grid = await self.view.dock_grid(edge="left", name="left")

        grid.add_column(fraction=1, name="center")

        grid.add_row(fraction=1, name="top", min_size=3)
        grid.add_row(fraction=10, name="middle")


        grid.add_areas(
            text_view="center,top",
            scroll_view="center,middle",
        )

        grid.place(
            text_view=self.text_input,
            scroll_view=self.scroll_view,
        )

    async def action_submit(self):
        with self.console.status("Searching"):
            search_term = self.text_input.value
            results = self.client.search(search_term)
            # print(results)
            results_renderables = []
            if len(results) != 0:
                for result in results:
                    subtitle = f"[blue]{result['num_files']} file{'s' if int(result['num_files']) > 1 else ''}[/] | [blue]{result['size']}[/] | [green]{result['seeders']}[/] | [red]{result['leechers']}[/]"
                    results_renderables.append(
                        Panel(
                            f"[white]{result['category_name']}[/]\n[cyan]{result['magnet']}[/]",
                            title=f"[bold blue]{result['name']}[/]",
                            title_align="left",
                            border_style="magenta",
                            subtitle=subtitle,
                            subtitle_align="right",
                        )
                    )
            else:
                results_renderables.append(
                    Panel(
                        f"[bold red]No results[/]",
                        border_style="red",
                    )
                )

            await self.scroll_view.update(Columns(results_renderables))

    async def on_shutdown_request(self, event) -> None:
        await self.client.close()
        await self.close_messages()


def main():
    TPBSearch.run()

if __name__ == '__main__':
    main()