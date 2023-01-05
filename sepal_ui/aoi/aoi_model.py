import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.request import urlretrieve

import ee
import geopandas as gpd
import pandas as pd
import traitlets as t
from deprecated.sphinx import deprecated
from ipyleaflet import GeoJSON
from typing_extensions import Self

from sepal_ui import color
from sepal_ui import sepalwidgets as sw
from sepal_ui.frontend import styles as ss
from sepal_ui.message import ms
from sepal_ui.model import Model
from sepal_ui.scripts import gee
from sepal_ui.scripts import utils as su

__all__ = ["AoiModel"]


class AoiModel(Model):

    # ###########################################################################
    # ###                      dataset const                                  ###
    # ###########################################################################

    FILE: List[Path] = [
        Path(__file__).parents[1] / "scripts" / "gadm_database.csv",
        Path(__file__).parents[1] / "scripts" / "gaul_database.csv",
    ]
    "Paths to the GADM(0) and GAUL(1) database"

    CODE: List[str] = ["GID_{}", "ADM{}_CODE"]
    "GADM(0) and GAUL(1) administrative codes key format"

    NAME: List[str] = ["NAME_{}", "ADM{}_NAME"]
    "GADM(0) and GAUL(1) naming key format"

    ISO: List[str] = ["GID_0", "ISO 3166-1 alpha-3"]
    "GADM(0) and GAUL(1) iso codes key"

    GADM_BASE_URL: str = (
        "https://biogeo.ucdavis.edu/data/gadm3.6/gpkg/gadm36_{}_gpkg.zip"
    )
    "The base url to download gadm maps"

    GAUL_ASSET: str = "FAO/GAUL/2015/level{}"
    "The GAUL asset name"

    ASSET_SUFFIX: str = "aoi_"
    "The suffix to identify the asset in GEE"

    # ###########################################################################
    # ###                             const methods                           ###
    # ###########################################################################

    CUSTOM: str = ms.aoi_sel.custom
    "The word displayed for custom method in the relevant lang"

    ADMIN: str = ms.aoi_sel.administrative
    "The word displayed for admin method in the relevant lang"

    METHODS: Dict[str, Dict[str, str]] = {
        "ADMIN0": {"name": ms.aoi_sel.adm[0], "type": ADMIN},
        "ADMIN1": {"name": ms.aoi_sel.adm[1], "type": ADMIN},
        "ADMIN2": {"name": ms.aoi_sel.adm[2], "type": ADMIN},
        "SHAPE": {"name": ms.aoi_sel.vector, "type": CUSTOM},
        "DRAW": {"name": ms.aoi_sel.draw, "type": CUSTOM},
        "POINTS": {"name": ms.aoi_sel.points, "type": CUSTOM},
        "ASSET": {"name": ms.aoi_sel.asset, "type": CUSTOM},
    }
    "The word displayed for all selection methods in the relevant lang"

    # ###########################################################################
    # ###                      widget related traitlets                       ###
    # ###########################################################################

    method: t.Unicode = t.Unicode(None, allow_none=True).tag(sync=True)
    "str: the currently selected method"

    point_json: t.Dict = t.Dict(None, allow_none=True).tag(sync=True)
    "dict: information that will be use to transform the csv into a gdf"

    vector_json: t.Dict = t.Dict(None, allow_none=True).tag(sync=True)
    "dict: information that will be use to transform the vector file into a gdf"

    geo_json: t.Dict = t.Dict(None, allow_none=True).tag(sync=True)
    "dict: the drawn geojson shape"

    admin: t.Unicode = t.Unicode(None, allow_none=True).tag(sync=True)
    "The admin number selected"

    asset_name: t.Unicode = t.Unicode(None, allow_none=True).tag(sync=True)
    "The asset name (only for GEE model)"

    asset_json: t.Dict = t.Dict(None, allow_none=True).tag(sync=True)
    "The asset json description (only for GEE model)"

    name: t.Unicode = t.Unicode(None, allow_none=True).tag(sync=True)
    "The name of the file to create (used only in drawn shaped)"

    # ###########################################################################
    # ###                           model parameters                          ###
    # ###########################################################################

    gee: bool = True
    "either or not the model is bound to gee"

    folder: Union[str, Path] = ""
    "The folder name used in GEE related component, mainly used for debugging"

    default_vector: Optional[Union[str, Path]] = None
    "The default vector file that will be used to produce the gdf. need to be readable by fiona and/or GDAL/OGR"

    default_admin: Optional[str] = None
    "The default administrative area in GADM or GAUL norm"

    default_asset: Optional[str] = None
    "The default asset name, need to point to a readable FeatureCollection"

    # ###########################################################################
    # ###                           model outputs                             ###
    # ###########################################################################

    dst_asset_id: str = ""
    "The exported asset id"

    selected_feature: Optional[Union[ee.Feature, gpd.GeoDataFrame]] = None
    "The Feature associated with a query"

    gdf: Optional[gpd.GeoDataFrame] = None
    "The geodataframe corresponding to the selected AOI"

    feature_collection: Optional[ee.FeatureCollection] = None
    "The feature Collection generated by the parameters (only for GEE models)"

    ipygeojson: Optional[GeoJSON] = None
    "The representation of the AOI as a ipyleaflet layer"

    @deprecated(
        version="2.11.3",
        reason=":code:`alert` positional argument will be removed. Successfull output messages has to be created in AoiView.",
    )
    def __init__(
        self,
        alert: Optional[sw.Alert] = None,
        gee: bool = True,
        vector: Optional[Union[str, Path]] = None,
        asset: Optional[Union[str, Path]] = None,
        admin: Optional[str] = None,
        folder: Union[str, Path] = "",
    ) -> None:

        """
        an Model object dedicated to the sorage and the manipulation of aoi.
        It is meant to be used with the AoiView object (embeded in the AoiTile).
        By using this you will be able to provide your application with aoi as an ee_object
        or a gdf, depending if you activated the ee binding or not.
        The class also provide insight on your aoi geometry.

        Args:
            gee: wether or not the aoi selector should be using the EarthEngine binding
            vector: the path to the default vector object
            admin: the administrative code of the default selection. Need to be GADM if ee==False and GAUL 2015 if ee==True.
            asset: the default asset. Can only work if ee==True
            folder: the init GEE asset folder where the asset selector should start looking (debugging purpose)

        .. deprecated:: 2.3.2
            'asset_name' will be used as variable to store 'ASSET' method info. To get the destination saved asset id, please use 'dst_asset_id' variable.

        """

        super().__init__()

        # the ee retated informations
        self.gee = gee
        if gee:
            su.init_ee()
            self.folder = str(folder) or ee.data.getAssetRoots()[0]["id"]

        # set default values
        self.set_default(vector, admin, asset)

    def set_default(
        self,
        vector: Optional[Union[str, Path]] = None,
        admin: Optional[str] = None,
        asset: Optional[Union[str, Path]] = None,
    ) -> Self:
        """
        Set the default value of the object and create a gdf/feature_collection out of it

        Args:
            vector: the default vector file that will be used to produce the gdf. need to be readable by fiona and/or GDAL/OGR
            admin: the default administrative area in GADM or GAUL norm
            asset: the default asset name, need to point to a readable FeatureCollection
        """

        # save the default values
        self.default_vector = vector
        self.default_asset = self.asset_name = str(asset) if asset else None
        self.asset_json = (
            {"pathname": asset, "column": "ALL", "value": None} if asset else None
        )
        self.default_admin = self.admin = admin

        # cast the vector to json
        self.vector_json = (
            {"pathname": str(vector), "column": "ALL", "value": None}
            if vector
            else None
        )

        # cast the asset to json
        self.asset_json = (
            {"pathname": asset, "column": "ALL", "value": None} if asset else None
        )

        # set the default gdf if possible
        if self.vector_json is not None:
            self.set_object("SHAPE")
        elif self.admin:
            self.set_object("ADMIN0")  # any level will work
        elif self.asset_json is not None:
            self.set_object("ASSET")

        return self

    def set_object(self, method: str = "") -> Self:
        """
        set the object (gdf/featurecollection) based on the model inputs. The method can
        be manually overwritten

        Args:
            method: a model loading method
        """

        # clear the model output if existing
        self.clear_output()

        # overwrite self.method
        self.method = method or self.method

        if self.method in ["ADMIN0", "ADMIN1", "ADMIN2"]:
            self._from_admin(self.admin)
        elif self.method == "POINTS":
            self._from_points(self.point_json)
        elif self.method == "SHAPE":
            self._from_vector(self.vector_json)
        elif self.method == "DRAW":
            self._from_geo_json(self.geo_json)
        elif self.method == "ASSET":
            self._from_asset(self.asset_json)
        else:
            raise Exception(ms.aoi_sel.exception.no_inputs)

        return self

    def _from_asset(self, asset_json: dict) -> Self:
        """set the ee.FeatureCollection output from an existing asset"""

        if not (asset_json["pathname"]):
            raise Exception(ms.aoi_sel.exception.no_asset)

        if asset_json["column"] != "ALL":
            if asset_json["value"] is None:
                raise Exception(ms.aoi_sel.exception.no_value)

        # set the name
        self.name = Path(asset_json["pathname"]).stem.replace(self.ASSET_SUFFIX, "")
        self.asset_name = asset_json["pathname"]
        ee_col = ee.FeatureCollection(asset_json["pathname"])

        if asset_json["column"] != "ALL":

            column = asset_json["column"]
            value = asset_json["value"]
            ee_col = ee_col.filterMetadata(column, "equals", value)
            self.name = f"{self.name}_{column}_{value}"

        # set the feature collection
        self.feature_collection = ee_col

        # create a gdf form te feature_collection
        features = self.feature_collection.getInfo()["features"]
        self.gdf = gpd.GeoDataFrame.from_features(features).set_crs(epsg=4326)

        return self

    def _from_points(self, point_json: dict) -> Self:
        """
        set the object output from a csv json

        Args:
            point_json: the geo_interface description of the points
        """

        if not all(point_json.values()):
            raise Exception(ms.aoi_sel.exception.uncomplete)

        # cast the pathname to pathlib Path
        point_file = Path(point_json["pathname"])

        # check that the columns are well set
        values = [v for v in point_json.values()]
        if not len(values) == len(set(values)):
            raise Exception(ms.aoi_sel.exception.duplicate_key)

        # create the gdf
        df = pd.read_csv(point_file, sep=None, engine="python")
        self.gdf = gpd.GeoDataFrame(
            df,
            crs="EPSG:4326",
            geometry=gpd.points_from_xy(
                df[point_json["lng_column"]], df[point_json["lat_column"]]
            ),
        )

        # set the name
        self.name = point_file.stem

        if self.gee:
            # transform the gdf to ee.FeatureCollection
            self.feature_collection = ee.FeatureCollection(self.gdf.__geo_interface__)

            # export as a GEE asset
            self.export_to_asset()

        return self

    def _from_vector(self, vector_json: dict) -> Self:
        """
        Set the object output from a vector json

        Args:
            vector_json: the dict describing the vector file, and column filter
        """

        if not (vector_json["pathname"]):
            raise Exception(ms.aoi_sel.exception.no_file)

        if vector_json["column"] != "ALL":
            if vector_json["value"] is None:
                raise Exception(ms.aoi_sel.exception.no_value)

        # cast the pathname to pathlib Path
        vector_file = Path(vector_json["pathname"])

        # create the gdf
        self.gdf = gpd.read_file(vector_file).to_crs("EPSG:4326")

        # set the name using the file stem
        self.name = vector_file.stem

        # filter it if necessary
        if vector_json["value"] is not None:
            self.gdf = self.gdf[self.gdf[vector_json["column"]] == vector_json["value"]]
            self.name = f"{self.name}_{vector_json['column']}_{vector_json['value']}"

        if self.gee:
            # transform the gdf to ee.FeatureCollection
            self.feature_collection = su.geojson_to_ee(self.gdf.__geo_interface__)

            # export as a GEE asset
            self.export_to_asset()

        return self

    def _from_geo_json(self, geo_json: dict) -> Self:
        """
        Set the gdf output from a geo_json

        Args:
            geo_json: the __geo_interface__ dict of a geometry drawn on the map
        """

        if not geo_json:
            raise Exception(ms.aoi_sel.exception.no_draw)

        # remove the style property from geojson as it's not recognize by geopandas and gee
        for feat in geo_json["features"]:
            if "style" in feat["properties"]:
                del feat["properties"]["style"]

        # create the gdf
        self.gdf = gpd.GeoDataFrame.from_features(geo_json).set_crs(epsg=4326)

        # normalize the name
        self.name = su.normalize_str(self.name)

        if self.gee:
            # transform the gdf to ee.FeatureCollection
            self.feature_collection = su.geojson_to_ee(self.gdf.__geo_interface__)

            # export as a GEE asset
            self.export_to_asset()
        else:
            # save the geojson in downloads
            path = Path("~", "downloads", "aoi").expanduser()
            path.mkdir(
                exist_ok=True, parents=True
            )  # if nothing have been run the downloads folder doesn't exist
            self.gdf.to_file(path / f"{self.name}.geojson", driver="GeoJSON")

        return self

    def _from_admin(self, admin: str) -> Self:
        """
        Set the object according to given an administrative number in the GADM norm

        Args:
            admin: the admin code corresponding to FAO GAUl (if gee) or GADM
        """

        if not admin:
            raise Exception(ms.aoi_sel.exception.no_admlyr)

        # get the admin level corresponding to the given admin code
        df = pd.read_csv(self.FILE[self.gee], dtype=str)

        # extract the first element that include this administrative code and set the level accordingly
        is_in = df.filter([self.CODE[self.gee].format(i) for i in range(3)]).isin(
            [admin]
        )

        if not is_in.any().any():
            raise Exception(ms.aoi_sel.exception.invalid_code)
        else:
            index = 3 if self.gee else -1
            level = (
                is_in[~((~is_in).all(axis=1))].idxmax(1).iloc[0][index]
            )  # the character that contains the index

        if self.gee:

            # get the feature_collection
            self.feature_collection = ee.FeatureCollection(
                self.GAUL_ASSET.format(level)
            ).filter(ee.Filter.eq(f"ADM{level}_CODE", int(admin)))

            # transform it into gdf
            features = self.feature_collection.getInfo()["features"]
            self.gdf = gpd.GeoDataFrame.from_features(features).set_crs(epsg=4326)

        else:
            # save the country iso_code
            iso_3 = admin[:3]

            # download the geopackage in a tmp directory
            with tempfile.TemporaryDirectory() as tmp_dir:

                zip_file = Path(tmp_dir) / f"{iso_3}.zip"

                # get the zip from GADM server only the ISO_3 code need to be used
                urlretrieve(self.GADM_BASE_URL.format(iso_3), zip_file)

                # read the geopackage
                layer_name = f"gadm36_{iso_3}_{level}"
                level_gdf = gpd.read_file(
                    f"{zip_file}!gadm36_{iso_3}.gpkg", layer=layer_name
                )

            # get the exact admin from this layer
            self.gdf = level_gdf[level_gdf[self.CODE[self.gee].format(level)] == admin]

        # set the name using the layer
        r = df[df[self.CODE[self.gee].format(level)] == admin].iloc[0]
        names = [
            su.normalize_str(r[self.NAME[self.gee].format(i)])
            if i
            else r[self.ISO[self.gee]]
            for i in range(int(level) + 1)
        ]
        self.name = "_".join(names)

        return self

    def clear_output(self) -> Self:
        """
        Clear the output of the aoi selector without changing the traits and/or the parameters.
        """

        # reset the outputs
        self.gdf = None
        self.feature_collection = None
        self.ipygeojson = None
        self.selected_feature = None
        self.dst_asset_id = None

        return self

    def clear_attributes(self) -> Self:
        """
        Return all attributes to their default state.
        Set the default setting as current object.
        """

        # keep the default
        admin = self.default_admin
        vector = self.default_vector
        asset = self.default_asset

        # delete all the traits
        [setattr(self, attr, None) for attr in self.trait_names()]

        # reset the outputs
        self.clear_output()

        # reset the default
        self.set_default(vector, admin, asset)

        return self

    def get_columns(self) -> List[str]:
        """
        Retrieve the columns or variables from self excluding geometries and gee index.

        Returns:
            sorted list of column names
        """

        if self.gdf is None:
            raise Exception(ms.aoi_sel.exception.no_gdf)

        if self.gee:
            aoi_ee = ee.Feature(self.feature_collection.first())
            columns = aoi_ee.propertyNames().getInfo()
            list_ = [
                col for col in columns if col not in ["system:index", "Shape_Area"]
            ]
        else:
            list_ = list(set(["geometry"]) ^ set(self.gdf.columns.to_list()))

        return sorted(list_)

    def get_fields(self, column: str) -> List[str]:
        """
        Retrieve the fields from a column

        Args:
            A column name to query over the asset

        Returns:
            sorted list of fields value

        """

        if self.gdf is None:
            raise Exception(ms.aoi_sel.exception.no_gdf)

        if self.gee:
            fields = self.feature_collection.distinct(column).aggregate_array(column)
            list_ = fields.getInfo()
        else:
            list_ = self.gdf[column].to_list()

        return sorted(list_)

    def get_selected(
        self, column: str, field: str
    ) -> Union[ee.Feature, gpd.GeoDataFrame]:
        """
        Select an ee object based on selected column and field.

        Args:
            column: the selected column in the dataset
            field: the value to search in the selected column

        Returns:
            The Feature associated with the query
        """

        if self.gdf is None:
            raise Exception(ms.aoi_sel.exception.no_gdf)

        if self.gee:
            selected_feature = self.feature_collection.filterMetadata(
                column, "equals", field
            )
        else:
            selected_feature = self.gdf[self.gdf[column] == field]

        return selected_feature

    def total_bounds(self) -> Tuple[float, float, float, float]:
        """
        Reproduce the behaviour of the total_bounds method from geopandas

        Returns:
            minxx, miny, maxx, maxy
        """

        if self.gee:
            ee_bounds = self.feature_collection.geometry().bounds().coordinates()
            coords = ee_bounds.get(0).getInfo()
            ll, ur = coords[0], coords[2]
            bounds = ll[0], ll[1], ur[0], ur[1]
        else:
            bounds = self.gdf.total_bounds

        return bounds

    def export_to_asset(self) -> Self:
        """
        Export the feature_collection as an asset (only for ee model)
        """

        asset_name = self.ASSET_SUFFIX + self.name
        asset_id = str(Path(self.folder, asset_name))

        self.dst_asset_id = asset_id

        # check if the table already exist
        if asset_id in [a["name"] for a in gee.get_assets(self.folder)]:
            return self

        # check if the task is running
        if gee.is_running(asset_name):
            return self

        # run the task
        task_config = {
            "collection": self.feature_collection,
            "description": asset_name,
            "assetId": asset_id,
        }

        task = ee.batch.Export.table.toAsset(**task_config)
        task.start()

        return self

    def get_ipygeojson(self) -> GeoJSON:
        """
        Converts current geopandas object into ipyleaflet GeoJSON

        Return:
            The geojson layer of the aoi gdf, ready to use in a Map
        """

        if self.gdf is None:
            raise Exception(ms.aoi_sel.exception.no_gdf)

        # read the data from geojson and add the name as a property of the shape
        # useful when handler are added from ipyleaflet
        data = json.loads(self.gdf.to_json())
        for f in data["features"]:
            f["properties"]["name"] = self.name

        # adapt the style to the theme
        style = json.loads((ss.JSON_DIR / "aoi.json").read_text())
        style.update(color=color.success, fillColor=color.success)

        # create a GeoJSON object
        # attribution="SEPAL(c)" is not recognized yet
        # https://github.com/jupyter-widgets/ipyleaflet/issues/847
        self.ipygeojson = GeoJSON(data=data, style=style, name="aoi")

        return self.ipygeojson
