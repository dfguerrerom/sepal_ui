from typing import Optional, Union

import ipyvuetify as v
import traitlets as t
from deprecated.sphinx import versionadded
from ipyvue import VueWidget
from traitlets import observe
from typing_extensions import Self

__all__ = ["SepalWidget", "Tooltip"]


class SepalWidget(v.VuetifyWidget):
    """
    Custom vuetifyWidget to add specific methods

    Args:
        viz (bool, optional): define if the widget should be visible or not
        tooltip (str, optional): tooltip text of the widget. If set the widget will be displayed on :code:`self.widget` (irreversible).
    """

    viz: t.Bool = t.Bool(True).tag(sync=True)
    "whether the widget is displayed or not"

    old_class: t.Unicode = t.Unicode("").tag(sync=True)
    "a saving attribute of the widget class"

    with_tooltip: Optional[v.Tooltip] = None
    "the full widget and its tooltip. Useful for display purposes when a tooltip has been set"

    def __init__(self, viz: bool = True, tooltip: str = "", **kwargs) -> None:

        # init the widget
        super().__init__(**kwargs)

        # setup the viz status
        self.viz = viz

        # create a tooltip only if a message is set
        self.set_tooltip(tooltip)

    @observe("viz")
    def _set_viz(self, *args) -> None:
        """
        hide or show the component according to its viz param value.

        Hide the widget by reducing the html class to :code:`d-none`.
        Show the widget by removing the :code:`d-none` html class.
        Save the previous class
        """

        # will be replaced byt direct calls to built-in hide
        # once the previous custom implementation will be fully removed

        if self.viz:

            # change class value
            self.class_ = self.old_class or self.class_
            self.class_list.remove("d-none")

        else:

            # change class value
            self.class_list.remove("d-none")
            self.old_class = str(self.class_)
            self.class_ = "d-none"

        return

    def toggle_viz(self) -> Self:
        """
        toogle the visibility of the widget.
        """

        self.viz = not self.viz

        return self

    def hide(self) -> Self:
        """
        Hide the widget by reducing the html class to :code:`d-none`.
        Save the previous class and set viz attribute to False.
        """

        # update viz state
        self.viz = False

        return self

    def show(self) -> Self:
        """
        Show the widget by removing the d-none html class.
        Save the previous class and set viz attribute to True.
        """

        # update viz state
        self.viz = True

        return self

    def reset(self) -> Self:
        """
        Clear the widget v_model. Need to be extented in custom widgets to fit the structure of the actual input.
        """

        self.v_model = None

        return self

    def get_children(self, id_: str = "") -> Union[str, list]:
        """Retrieve all children elements that matches with the given id\_.

        Args:
            id\_ (str, optional): attribute id to compare with.

        Returns:
            list with all mathing elements if there are more than one, otherwise will return the matching element.

        """

        elements = []

        def search_children(parent):

            if issubclass(parent.__class__, VueWidget):

                if parent.attributes.get("id") == id_:
                    elements.append(parent)

                if len(parent.children):
                    [search_children(chld) for chld in parent.children]

        # Search in the self children elements
        [search_children(chld) for chld in self.children]

        return elements[0] if len(elements) == 1 else elements

    def set_children(
        self, children: Union[str, v.VuetifyWidget, list], position: str = "first"
    ) -> Self:
        """Insert input children in self children within given position

        Args:
            children: the list of children to add to the widget. It can also be a list (str and DOMWidgets are accepted)
            position: whether to insert as first or last element. ["first", "last"]
        """

        if not isinstance(children, list):
            children = [children]

        new_childrens = self.children[:]

        if position == "first":
            new_childrens = children + new_childrens

        elif position == "last":
            new_childrens = new_childrens + children

        else:
            raise ValueError(
                f"Position '{position}' is not a valid value. Use 'first' or 'last'"
            )

        self.children = new_childrens

        return self

    @versionadded(version="2.9.0", reason="Tooltip are now integrated to widgets")
    def set_tooltip(self, txt: str = "", **kwargs) -> v.Tooltip:
        """
        Create a tooltip associated with the widget. If the text is not set, the
        tooltip will be automatically removed. Once the tooltip is set the object
        variable can be accessed normally but to render the widget, one will need
        to use :code:`self.with_tooltip` (irreversible).

        Args:
            txt: anything False (0, False, empty text, None) will lead to the removal of the tooltip. everything else will be used to fill the text area
            kwargs: any options available in a Tooltip widget

        Returns:
            the tooltip associated with the object
        """
        if isinstance(self.with_tooltip, Tooltip):
            # If it's already created, and there are new kwargs, let's modify it
            [setattr(self.with_tooltip, attr, value) for attr, value in kwargs.items()]
            self.with_tooltip.children = [txt]
            self.with_tooltip.disabled = not bool(txt)
        elif txt != "":
            self.with_tooltip = Tooltip(self, txt, **kwargs)

        return self


class Tooltip(v.Tooltip):
    """
    Custom widget to display tooltip when mouse is over widget

    Args:
        widget: widget used to display tooltip
        tooltip: the text to display in the tooltip
    """

    def __init__(self, widget: v.VuetifyWidget, tooltip: str, **kwargs) -> None:

        # set some default parameters
        kwargs["close_delay"] = kwargs.pop("close_delay", 200)

        self.v_slots = [
            {"name": "activator", "variable": "tooltip", "children": widget}
        ]
        widget.v_on = "tooltip.on"

        self.children = [tooltip]

        super().__init__(**kwargs)
