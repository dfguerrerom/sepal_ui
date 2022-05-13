import ipyvuetify as v

from sepal_ui import color
from sepal_ui.planetapi import PlanetModel
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw


class PlanetView(sw.Layout):
    def __init__(self, *args, btn=None, alert=None, planet_model=None, **kwargs):
        """Stand-alone interface to capture planet lab credentials, validate its  subscription and
        connect to the client stored in the model.

        Args:
            bnt (sw.Btn, optional): Button to trigger the validation process in the associated model.
            alert (sw.Alert, v.Alert, optional): Alert component to display end-user action results.
            planet_model (sepal_ui.planetlab.PlanetModel): backend model to manipulate interface actions.

        """

        self.class_ = "d-block flex-wrap"

        super().__init__(*args, **kwargs)

        self.planet_model = planet_model if planet_model else PlanetModel()
        self.btn = btn if btn else sw.Btn("Validate", small=True, class_="mr-1")
        self.alert = alert if alert else sw.Alert()

        self.w_username = sw.TextField(
            label="Planet username", class_="mr-2", v_model=""
        )
        self.w_password = sw.PasswordField(label="Planet password")
        self.w_key = sw.PasswordField(label="Planet API key", v_model="").hide()

        states = {
            False: ("Not connected", color.error),
            True: ("Connected", color.success),
        }

        self.w_state = sw.StateIcon(self.planet_model, "active", states)

        self.w_method = v.Select(
            label="Login method",
            class_="mr-2",
            v_model="credentials",
            items=[
                {"value": "api_key", "text": "API Key"},
                {"value": "credentials", "text": "Credentials"},
            ],
        )

        w_validation = v.Flex(
            style_="flex-grow: 0 !important;",
            children=[self.btn, self.w_state],
            class_="pr-1 flex-nowrap",
        )
        self.children = [
            self.w_method,
            sw.Layout(
                class_="align-center",
                children=[
                    self.w_username,
                    self.w_password,
                    self.w_key,
                ],
            ),
        ]

        if not btn:
            self.children[-1].set_children(w_validation, "last")

        if not alert:
            self.set_children(self.alert, "last")

        self.w_method.observe(self._swap_inputs, "v_model")
        self.btn.on_event("click", self.validate)

    def reset(self):
        """Empty credentials fields"""

        self.w_username.v_model = None
        self.w_password.v_model = None
        self.w_key.v_model = None

    def _swap_inputs(self, change):
        """Swap between credentials and api key inputs"""

        self.planet_model._init_client(None)
        self.alert.reset()
        self.reset()

        if change["new"] == "api_key":
            self.w_username.hide()
            self.w_password.hide()
            self.w_key.show()
        else:
            self.w_username.show()
            self.w_password.show()
            self.w_key.hide()

    @su.loading_button()
    def validate(self, *args):
        """Initialize planet client and validate if is active"""

        if self.w_method.v_model == "credentials":
            credentials = (self.w_username.v_model, self.w_password.v_model)
        else:
            credentials = self.w_key.v_model

        self.planet_model._init_client(credentials, event=True)
