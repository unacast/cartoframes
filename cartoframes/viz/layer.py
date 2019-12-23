import pandas

from ..utils.utils import merge_dicts
from .legend import Legend
from .legend_list import LegendList
from .popup import Popup
from .popup_list import PopupList
from .source import Source
from .style import Style
from .widget import Widget
from .widget_list import WidgetList

from ..utils.utils import extract_viz_columns


class Layer():
    """Layer to display data on a map. This class can be used as one or more
    layers in :py:class:`Map <cartoframes.viz.Map>` or on its own in a Jupyter
    notebook to get a preview of a Layer.

    Args:
        source (str, pandas.DataFrame, geopandas.GeoDataFrame,
            :py:class:`CartoDataFrame <cartoframes.CartoDataFrame>`): The source data:
            table name, SQL query or a dataframe.
        style (str, dict, or :py:class:`Style <cartoframes.viz.Style>`, optional):
            The style of the visualization.
        legends (bool, :py:class:`Legend <cartoframes.viz.Legend>` list, optional):
            The legends definition for a layer. It contains a list of legend helpers.
            See :py:class:`Legend <cartoframes.viz.Legend>` for more information.
        widgets (bool, list, or :py:class:`WidgetList <cartoframes.viz.WidgetList>`, optional):
            Widget or list of widgets for a layer. It contains the information to display
            different widget types on the top right of the map. See
            :py:class:`WidgetList` for more information.
        click_popup(`Popup <cartoframes.viz.Popup>`, optional): Set up a popup to be
            displayed on a click event.
        hover_popup(`Popup <cartoframes.viz.Popup>`, optional): Set up a popup to be
            displayed on a hover event.
        credentials (:py:class:`Credentials <cartoframes.auth.Credentials>`, optional):
            A Credentials instance. This is only used for the simplified Source API.
            When a :py:class:`Source <cartoframes.viz.Source>` is passed as source,
            these credentials is simply ignored. If not provided the credentials will be
            automatically obtained from the default credentials.
        bounds (dict or list, optional): a dict with `west`, `south`, `east`, `north`
            keys, or an array of floats in the following structure: [[west,
            south], [east, north]]. If not provided the bounds will be automatically
            calculated to fit all features.
        geom_col (str, optional): string indicating the geometry column name in the source `DataFrame`.


    Example:

        Create a layer with a custom popup, legend, and widget.

        .. code::
            # FIXME

        Create a layer specifically tied to a :py:class:`Credentials
        <cartoframes.auth.Credentials>` and display it on a map.

        .. code::
            # FIXME

        Preview a layer in a Jupyter notebook. Note: if in a Jupyter notebook,
        it is not required to explicitly add a Layer to a :py:class:`Map
        <cartoframes.viz.Map>` if only visualizing data as a single layer.

        .. code::
            #FIXME
    """

    def __init__(self,
                 source,
                 style=None,
                 legends=True,
                 widgets=False,
                 click_popup=None,
                 hover_popup=None,
                 credentials=None,
                 bounds=None,
                 geom_col=None,
                 title='',
                 description='',
                 footer=''):

        self.is_basemap = False
        self._title = title
        self._description = description
        self._footer = footer
        self.source = _set_source(source, credentials, geom_col)
        self.style = _set_style(style)

        self.popups = self._init_popups(title, click_popup, hover_popup)
        self.legends = self._init_legends(legends)
        self.widgets = self._init_widgets(widgets)

        geom_type = self.source.get_geom_type()
        popups_variables = self.popups.get_variables()
        widget_variables = self.widgets.get_variables()
        external_variables = merge_dicts(popups_variables, widget_variables)
        self.viz = self.style.compute_viz(geom_type, external_variables)
        viz_columns = extract_viz_columns(self.viz)

        self.source.compute_metadata(viz_columns)
        self.source_type = self.source.type
        self.source_data = self.source.data
        self.bounds = bounds or self.source.bounds
        self.credentials = self.source.get_credentials()
        self.interactivity = self.popups.get_interactivity()
        self.widgets_info = self.widgets.get_widgets_info()
        self.legends_info = self.legends.get_info() if self.legends is not None else None
        self.has_legend_list = isinstance(self.legends, LegendList)

    def _init_legends(self, legends):
        if legends is True:
            return self.style.default_legends(self._title, self._description, self._footer)

        if legends:
            return _set_legends(legends)

        return LegendList()

    def _init_widgets(self, widgets):
        if widgets is True:
            return WidgetList(self.style.default_widgets(self._title, self._description, self._footer))

        if widgets:
            return _set_widgets(widgets)

        return WidgetList()

    def _init_popups(self, title, click_popup, hover_popup):
        if click_popup is None and hover_popup is None:
            popups = self.style.default_popups(title)
            return _set_popups(popups)
        else:
            return _set_popups({
                'click': click_popup,
                'hover': hover_popup
            })

    def _repr_html_(self):
        from .map import Map
        return Map(self)._repr_html_()


def _set_source(source, credentials, geom_col):
    """Set a Source class from the input"""
    if isinstance(source, (str, pandas.DataFrame)):
        return Source(source, credentials, geom_col)
    elif isinstance(source, Source):
        return source
    else:
        raise ValueError('Wrong source')


def _set_style(style):
    """Set a Style class from the input"""
    if isinstance(style, (str, dict)):
        return Style(style)
    elif isinstance(style, Style):
        return style
    else:
        return Style()


def _set_popups(popups):
    """Set a Popup class from the input"""

    if isinstance(popups, (dict, Popup)):
        return PopupList(popups)
    else:
        return PopupList()


def _set_legends(legends):
    if isinstance(legends, Legend):
        return LegendList(legends)
    if isinstance(legends, LegendList):
        return legends
    if isinstance(legends, list):
        return LegendList(legends)
    else:
        return LegendList()


def _set_widgets(widgets):
    if isinstance(widgets, Widget):
        return WidgetList(widgets)
    if isinstance(widgets, list):
        return WidgetList(widgets)
    if isinstance(widgets, WidgetList):
        return widgets
    else:
        return WidgetList()
