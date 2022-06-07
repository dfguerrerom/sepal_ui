from traitlets import Int
from datetime import datetime as dt

import pandas as pd

import sepal_ui.sepalwidgets as sw
from sepal_ui.scripts import utils as su
from sepal_ui.aoi.aoi_model import AoiModel
from sepal_ui.message import ms
from sepal_ui import color as sc

CUSTOM = AoiModel.CUSTOM
ADMIN = AoiModel.ADMIN
ALL = "All"
select_methods = AoiModel.METHODS

__all__ = ["AoiView", "select_methods"]


class MethodSelect(sw.Select):
    f"""
    A method selector. It will list the available methods for this very AoiView.
    'ALL' will select all the available methods (default)
    'ADMIN' only the admin one, 'CUSTOM' only the custom one.
    'XXX' will add the selected method to the list when '-XXX' will discard it.
    You cannot mix adding and removing behaviours.

    Args:
        methods (str|[str]): a list of methods from the available list ({', '.join(select_methods.keys())})
        map_ (SepalMap, optional): link the aoi_view to a custom SepalMap to display the output, default to None
        gee (bool, optional): wether to bind to ee or not
    """

    def __init__(self, methods="ALL", gee=True, map_=None):

        # create the method list
        if methods == "ALL":
            self.methods = select_methods
        elif methods == "ADMIN":
            self.methods = {
                k: v for k, v in select_methods.items() if v["type"] == ADMIN
            }
        elif methods == "CUSTOM":
            self.methods = {
                k: v for k, v in select_methods.items() if v["type"] == CUSTOM
            }
        elif type(methods) == list:

            if any(m[0] == "-" for m in methods) != all(m[0] == "-" for m in methods):
                raise Exception("You mixed adding and removing, punk")

            if methods[0][0] == "-":

                to_remove = [method[1:] for method in methods]

                # Rewrite the methods instead of mutate the class methods
                self.methods = {
                    k: v for k, v in select_methods.items() if k not in to_remove
                }

            else:
                self.methods = {k: select_methods[k] for k in methods}
        else:
            raise Exception("I don't get what you meant")

        # clean the list from things we can't use
        gee is True or self.methods.pop("ASSET", None)
        map_ is not None or self.methods.pop("DRAW", None)

        # build the item list with header
        prev_type = None
        items = []
        for k, m in self.methods.items():
            current_type = m["type"]

            if prev_type != current_type:
                items.append({"header": current_type})
            prev_type = current_type

            items.append({"text": m["name"], "value": k})

        # create the input
        super().__init__(label=ms.aoi_sel.method, items=items, v_model="", dense=True)


class AdminField(sw.Select):
    """
    An admin level selector. It is binded to ee (GAUL 2015) or not (GADM 2021). allows to select administrative codes taking into account the administrative parent code and displaying humanly readable administrative names.

    Args:
        level (int): The administrative level of the field
        parent (AdminField): the adminField that deal with the parent admin level of the current selector. used to narrow down the possible options
        ee (bool, optional): wether to use ee or not (default to True)

    Attributes:
        gee (bool): the earthengine status
        level (int): the admin level of the current field
        parent (AdminField): the field parent object
    """

    # the file location of the database
    FILE = AoiModel.FILE
    CODE = AoiModel.CODE
    NAME = AoiModel.NAME

    def __init__(self, level, parent=None, gee=True):

        # save ee state
        self.ee = gee

        # get the level info
        self.level = level
        self.parent = parent

        # init an empty widget
        super().__init__(
            v_model=None, items=[], clearable=True, label=ms.aoi_sel.adm[level]
        )

        # add js behaviour
        self.parent is None or self.parent.observe(self._update, "v_model")

    def show(self):
        """
        when an admin field is shown, show its parent as well

        Return:
            self
        """

        super().show()
        self.parent is None or self.parent.show()

        return self

    def get_items(self, filter_=None):
        """
        update the item list based on the given filter

        Params:
            filter_ (str): The code of the parent v_model to filter the current results

        Return:
            self
        """

        # extract the level list
        df = (
            pd.read_csv(self.FILE[self.ee])
            .drop_duplicates(subset=self.CODE[self.ee].format(self.level))
            .sort_values(self.NAME[self.ee].format(self.level))
        )

        # filter it
        if filter_:
            df = df[df[self.CODE[self.ee].format(self.level - 1)] == filter_]

        # formatted as a item list for a select component
        self.items = [
            {
                "text": su.normalize_str(
                    r[self.NAME[self.ee].format(self.level)], folder=False
                ),
                "value": r[self.CODE[self.ee].format(self.level)],
            }
            for _, r in df.iterrows()
        ]

        return self

    def _update(self, change):
        """update the item list of the admin select"""

        # reset v_model
        self.v_model = None

        # update the items list
        if change["new"]:
            self.get_items(change["new"])

        return self


class AoiView(sw.Card):
    """
    Versatile card object to deal with the aoi selection. multiple selection method are available (see the MethodSelector object) and the widget can be fully customizable. Can also be bound to ee (ee==True) or not (ee==False)

    Args:
        methods (list, optional): the methods to use in the widget, default to 'ALL'. Available: {'ADMIN0', 'ADMIN1', 'ADMIN2', 'SHAPE', 'DRAW', 'POINTS', 'ASSET', 'ALL'}
        map_ (SepalMap, optional): link the aoi_view to a custom SepalMap to display the output, default to None
        gee (bool, optional): wether to bind to ee or not
        vector (str|pathlib.Path, optional): the path to the default vector object
        admin (int, optional): the administrative code of the default selection. Need to be GADM if :code:`ee==False` and GAUL 2015 if :code:`ee==True`.
        asset (str, optional): the default asset. Can only work if :code:`ee==True`
    """

    # ##########################################################################
    # ###                             widget parameters                      ###
    # ##########################################################################

    updated = Int(0).tag(sync=True)
    "int: traitlets triggered every time a AOI is selected"

    ee = True
    "bool: either or not he aoi_view is connected to gee"

    folder = None
    "str: the folder name used in GEE related component, mainly used for debugging"

    model = None
    "sepal_ui.aoi.AoiModel: the model to create the AOI from the selected parameters"

    # ##########################################################################
    # ###                            the embeded widgets                     ###
    # ##########################################################################

    map_ = None
    "sepal_ui.mapping.SepalMap: the map to draw the AOI"

    w_method = None
    "widget: the widget to select the method"

    components = None
    "dict: the followingwidgets used to define AOI"

    w_admin_0 = None
    "widget: the widget used to select admin level 0"

    w_admin_1 = None
    "widget: the widget used to select admin level 1"

    w_admin_2 = None
    "widget: the widget used to select admin level 2"

    w_vector = None
    "widget: the widget used to select vector shapes"

    w_points = None
    "widget: the widget used to select points files"

    w_draw = None
    "widget: the widget used to select the name of a drawn shape (only if :code:`map_ != None`)"

    w_asset = None
    "widget: the widget used to select asset name of a featureCollection (only if :code:`gee == True`)"

    btn = None
    "sw.Btn: a default btn"

    alert = None
    "sw.Alert: a alert to display message to the end user"

    def __init__(self, methods="ALL", map_=None, gee=True, folder=None, **kwargs):

        # set ee dependencie
        self.ee = gee
        self.folder = folder
        gee is False or su.init_ee()

        # get the model
        self.model = AoiModel(sw.Alert(), gee=gee, folder=folder, **kwargs)

        # get the map if filled
        self.map_ = map_

        # create the method widget
        self.w_method = MethodSelect(methods, gee=gee, map_=map_)

        # add the methods blocks
        self.w_admin_0 = AdminField(0, gee=gee).get_items()
        self.w_admin_1 = AdminField(1, self.w_admin_0, gee=gee)
        self.w_admin_2 = AdminField(2, self.w_admin_1, gee=gee)
        self.w_vector = sw.VectorField(label=ms.aoi_sel.vector)
        self.w_points = sw.LoadTableField(label=ms.aoi_sel.points)
        self.w_draw = sw.TextField(label=ms.aoi_sel.aoi_name)

        # group them together with the same key as the select_method object
        self.components = {
            "ADMIN0": self.w_admin_0,
            "ADMIN1": self.w_admin_1,
            "ADMIN2": self.w_admin_2,
            "SHAPE": self.w_vector,
            "POINTS": self.w_points,
            "DRAW": self.w_draw,
        }

        # hide them all
        [c.hide() for c in self.components.values()]

        # use the same alert as in the model
        self.alert = self.model.alert

        # bind the widgets to the model
        (
            self.model.bind(self.w_admin_0, "admin")
            .bind(self.w_admin_1, "admin")
            .bind(self.w_admin_2, "admin")
            .bind(self.w_vector, "vector_json")
            .bind(self.w_points, "point_json")
            .bind(self.w_method, "method")
            .bind(self.w_draw, "name")
        )

        # defint the asset select separately. If no gee is set up we don't want any
        # gee based widget to be requested. If it's the case, application that does not support GEE
        # will crash if the user didn't authenticate
        if self.ee:
            self.w_asset = sw.VectorField(
                label=ms.aoi_sel.asset, gee=True, folder=self.folder, types=["TABLE"]
            ).hide()
            self.components["ASSET"] = self.w_asset
            self.model.bind(self.w_asset, "asset_name")

        # add a validation btn
        self.btn = sw.Btn(ms.aoi_sel.btn)

        # create the widget
        self.children = (
            [self.w_method] + [*self.components.values()] + [self.btn, self.alert]
        )

        super().__init__(**kwargs)

        # js events
        self.w_method.observe(self._activate, "v_model")  # activate widgets
        self.btn.on_event("click", self._update_aoi)  # load the informations

        # reset te aoi_model
        self.model.clear_attributes()

    @su.loading_button(debug=True)
    def _update_aoi(self, widget, event, data):
        """load the object in the model & update the map (if possible)"""

        # read the information from the geojson datas
        if self.map_:
            self.model.geo_json = self.map_.dc.to_json()

        # update the model
        self.model.set_object()

        # update the map
        if self.map_:
            self.map_.remove_layer("aoi", none_ok=True)
            self.map_.zoom_bounds(self.model.total_bounds())

            if self.ee:
                self.map_.add_ee_layer(
                    self.model.feature_collection, {"color": sc.success}, "aoi"
                )
            else:
                self.map_.add_layer(self.model.get_ipygeojson())

            self.map_.hide_dc()

        # tell the rest of the apps that the aoi have been updated
        self.updated += 1

        return self

    def reset(self):
        """clear the aoi_model from input and remove the layer from the map (if existing)"""

        # clear the map
        self.map_ is None or self.map_.remove_layer("aoi", none_ok=True)

        # clear the inputs
        [w.reset() for w in self.components.values()]
        print(self.w_draw.v_model)

        # clear the model
        self.model.clear_attributes()
        print(self.w_draw.v_model)

        # reset the alert
        self.alert.reset()
        print(self.w_draw.v_model)

        # reset the view of the widgets
        self.w_method.v_model = None
        print(self.w_draw.v_model)

        return self

    def _activate(self, change):
        """activate the adapted widgets"""

        # clear and hide the alert
        self.alert.reset()

        # deactivate or activate the dc
        # clear the geo_json saved features to start from scratch
        if self.map_:
            if change["new"] == "DRAW":
                self.map_.dc.show()
            else:
                self.map_.dc.hide()

        # clear the inputs
        [w.reset() for w in self.components.values()]

        # activate the widget
        [
            w.show() if change["new"] == k else w.hide()
            for k, w in self.components.items()
        ]

        # init the name to the current value
        now = dt.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.w_draw.v_model = None if change["new"] is None else f"Manual_aoi_{now}"

        return self
