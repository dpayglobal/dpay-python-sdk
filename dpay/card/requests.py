from __future__ import annotations

from typing import Any

from dpay.card.enums import DccDecision
from dpay.payment.device_info import DeviceInfo


class CardPaymentRequest:
    def __init__(self, device_info: DeviceInfo) -> None:
        self.device_info = device_info
        self.email: str | None = None
        self.channel_id: int | None = None
        self.card_holder_first_name: str | None = None
        self.card_holder_last_name: str | None = None
        self.encrypted_card_data: str | None = None
        self.three_ds_confirmed: bool | None = None
        self.dcc_decision: str | None = None

    @classmethod
    def create(cls, device_info: DeviceInfo) -> CardPaymentRequest:
        return cls(device_info)

    def with_email(self, email: str) -> CardPaymentRequest:
        self.email = email
        return self

    def with_channel_id(self, channel_id: int) -> CardPaymentRequest:
        self.channel_id = channel_id
        return self

    def with_card_holder(self, first_name: str, last_name: str) -> CardPaymentRequest:
        self.card_holder_first_name = first_name
        self.card_holder_last_name = last_name
        return self

    def with_encrypted_card_data(self, encrypted_card_data: str) -> CardPaymentRequest:
        self.encrypted_card_data = encrypted_card_data
        return self

    def with_three_ds_confirmed(self, confirmed: bool) -> CardPaymentRequest:
        self.three_ds_confirmed = confirmed
        return self

    def with_dcc_decision(self, decision: str) -> CardPaymentRequest:
        DccDecision.assert_valid(decision)
        self.dcc_decision = decision
        return self

    def to_api(self) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if self.email is not None:
            body["email"] = self.email
        if self.channel_id is not None:
            body["channelId"] = self.channel_id
        if self.card_holder_first_name is not None:
            body["cardHolderFirstName"] = self.card_holder_first_name
        if self.card_holder_last_name is not None:
            body["cardHolderLastName"] = self.card_holder_last_name
        if self.encrypted_card_data is not None:
            body["encryptedCardData"] = self.encrypted_card_data
        body["deviceInfo"] = self.device_info.to_api()
        if self.three_ds_confirmed is not None:
            body["threeDsConfirmed"] = self.three_ds_confirmed
        if self.dcc_decision is not None:
            body["dccDecision"] = self.dcc_decision
        return body


class GooglePayRequest:
    def __init__(self, token: str, device_info: DeviceInfo) -> None:
        self.token = token
        self.device_info = device_info
        self.email: str | None = None
        self.channel_id: int | None = None

    @classmethod
    def create(cls, token: str, device_info: DeviceInfo) -> GooglePayRequest:
        return cls(token, device_info)

    def with_email(self, email: str) -> GooglePayRequest:
        self.email = email
        return self

    def with_channel_id(self, channel_id: int) -> GooglePayRequest:
        self.channel_id = channel_id
        return self

    def to_api(self) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if self.email is not None:
            body["email"] = self.email
        if self.channel_id is not None:
            body["channelId"] = self.channel_id
        body["xPayType"] = "GOOGLE_PAY"
        body["xPayToken"] = self.token
        body["deviceInfo"] = self.device_info.to_api()
        return body


class ApplePayRequest:
    def __init__(self, x_pay_type: str, token: str | None, device_info: DeviceInfo) -> None:
        self.x_pay_type = x_pay_type
        self.token = token
        self.device_info = device_info
        self.channel_id: int | None = None

    @classmethod
    def init(cls, device_info: DeviceInfo) -> ApplePayRequest:
        return cls("APPLE_PAY_INIT", None, device_info)

    @classmethod
    def pay(cls, token: str, device_info: DeviceInfo) -> ApplePayRequest:
        return cls("APPLE_PAY", token, device_info)

    def with_channel_id(self, channel_id: int) -> ApplePayRequest:
        self.channel_id = channel_id
        return self

    def to_api(self) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if self.channel_id is not None:
            body["channelId"] = self.channel_id
        body["xPayType"] = self.x_pay_type
        if self.token is not None:
            body["xPayToken"] = self.token
        body["deviceInfo"] = self.device_info.to_api()
        return body
