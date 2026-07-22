from __future__ import annotations

from typing import Any

from dpay.exceptions import DPayValueError


class DeviceInfo:
    def __init__(
        self,
        browser_accept_header: str,
        browser_language: str,
        browser_color_depth: int,
        browser_screen_height: int,
        browser_screen_width: int,
        browser_tz: int,
        browser_user_agent: str,
        system_family: str,
        geo_localization: str,
        device_id: str,
        application_name: str,
    ) -> None:
        if device_id == "" or len(device_id) > 64:
            raise DPayValueError("Device ID must be 1-64 characters")
        if application_name == "" or len(application_name) > 64:
            raise DPayValueError("Application name must be 1-64 characters")
        self.browser_accept_header = browser_accept_header
        self.browser_language = browser_language
        self.browser_color_depth = browser_color_depth
        self.browser_screen_height = browser_screen_height
        self.browser_screen_width = browser_screen_width
        self.browser_tz = browser_tz
        self.browser_user_agent = browser_user_agent
        self.system_family = system_family
        self.geo_localization = geo_localization
        self.device_id = device_id
        self.application_name = application_name
        self.browser_java_enabled: bool | None = None

    @classmethod
    def create(
        cls,
        browser_accept_header: str,
        browser_language: str,
        browser_color_depth: int,
        browser_screen_height: int,
        browser_screen_width: int,
        browser_tz: int,
        browser_user_agent: str,
        system_family: str,
        geo_localization: str,
        device_id: str,
        application_name: str,
    ) -> DeviceInfo:
        return cls(
            browser_accept_header,
            browser_language,
            browser_color_depth,
            browser_screen_height,
            browser_screen_width,
            browser_tz,
            browser_user_agent,
            system_family,
            geo_localization,
            device_id,
            application_name,
        )

    def with_browser_java_enabled(self, enabled: bool) -> DeviceInfo:
        self.browser_java_enabled = enabled
        return self

    def to_api(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "browserAcceptHeader": self.browser_accept_header,
            "browserLanguage": self.browser_language,
            "browserColorDepth": self.browser_color_depth,
            "browserScreenHeight": self.browser_screen_height,
            "browserScreenWidth": self.browser_screen_width,
            "browserTZ": self.browser_tz,
            "browserUserAgent": self.browser_user_agent,
            "systemFamily": self.system_family,
            "geoLocalization": self.geo_localization,
            "deviceID": self.device_id,
            "applicationName": self.application_name,
        }
        if self.browser_java_enabled is not None:
            data["browserJavaEnabled"] = "true" if self.browser_java_enabled else "false"
        return data
