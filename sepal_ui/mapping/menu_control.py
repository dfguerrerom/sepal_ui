from ipyleaflet import WidgetControl

from sepal_ui import sepalwidgets as sw
from sepal_ui.mapping.map_btn import MapBtn


class MenuControl(WidgetControl):
    """
    Widget control displaying a btn on the map. When clicked the menu expand to show the content set by the user.
    It's used to display interactive tiles directly in the map. If the card_content is a Tile it will be automatically nested.

    Args:
        icon_content (str): the icon content as specified in the sm.MapBtn object (i.e. a 3 letter name or an icon name)
        card_content (container): any container from sw. The sw.Tile is specifically design to fit in this component
    """

    def __init__(self, icon_content, card_content, **kwargs):

        # create a clickable btn
        btn = MapBtn(content=icon_content, v_on="menu.on")
        slot = {"name": "activator", "variable": "menu", "children": btn}

        # set up the content
        card = sw.Card(
            tile=True,
            max_height="40vh",
            min_height="40vh",
            max_width="400px",
            min_width="400px",
            children=[card_content],
            style_="overflow: auto",
        )

        # assemble everything in a menu
        self.menu = sw.Menu(
            v_model=False,
            close_on_click=False,
            close_on_content_click=False,
            children=[card],
            v_slots=[slot],
            offset_x=True,
        )

        super().__init__(widget=self.menu, position="bottomright")

        # place te menu according to the widget positioning
        self.update_position(None)
        self.observe(self.update_position, "position")

    def update_position(self, change):
        """
        update the position of the menu if the position of the widget is dynamically changed
        """

        self.menu.top = "bottom" in self.position
        self.menu.bottom = "top" in self.position
        self.menu.left = "right" in self.position
        self.menu.right = "left" in self.position
        return
