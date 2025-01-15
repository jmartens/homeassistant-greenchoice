import logging
from datetime import datetime, UTC
from typing import Union
from urllib.parse import urlencode

import aiohttp

from .auth import Auth
from .model import MeterReadings, Reading, Rates, Profile
from .model import Preferences
from .util import curl_dump

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://mijn.greenchoice.nl"


class ApiError(Exception):
    def __init__(self, message: str):
        _LOGGER.error(message)
        super().__init__(message)


class GreenchoiceApi:
    def __init__(self, username: str, password: str):
        self.auth = Auth(BASE_URL, username, password)
        self.preferences: Preferences | None = None

        self.result = {}

    async def _authenticated_request(
        self, method: str, endpoint: str, data=None, json=None
    ) -> aiohttp.ClientResponse:
        _LOGGER.debug(
            f"Request: {method} {endpoint} {data if data is not None else json}"
        )
        if not self.auth.session:
            self.auth.session = aiohttp.ClientSession()

        async with self.auth.session.request(method, endpoint, json=json) as response:
            if await self.auth.is_session_expired(response):
                self.auth.session = await self.auth.refresh_session()
                async with self.auth.session.request(method, endpoint, json=json) as response:
                    _LOGGER.debug(await curl_dump(response.request))
            else:
                _LOGGER.debug(await curl_dump(response.request))
            return response

    async def request(
        self, method: str, endpoint: str, data=None, _retry_count=2
    ) -> aiohttp.ClientResponse:
        try:
            target_url = BASE_URL + endpoint
            response = await self._authenticated_request(method, target_url, json=data)

            if len(response.history) > 1:
                _LOGGER.debug("Response history len > 1. %s", response.history)

            if response.status == 404:
                return response

            response.raise_for_status()
        except aiohttp.ClientResponseError as e:
            _LOGGER.error("HTTP Error: %s", e)
            _LOGGER.error("Cookies: %s", [c.key for c in self.auth.session.cookie_jar])
            if _retry_count == 0:
                raise ApiError(f"HTTP Error: {e}")

            _LOGGER.debug("Retrying request")
            return await self.request(method, endpoint, data, _retry_count - 1)

        _LOGGER.debug("Request success")
        return response

    @staticmethod
    async def _validate_response(response: aiohttp.ClientResponse) -> dict:
        if not response:
            raise ApiError("Error retrieving response!")

        try:
            response_json = await response.json()
        except aiohttp.ClientResponseError as e:
            raise ApiError("Could not parse response: invalid JSON", e)

        return response_json

    async def microbus_init(self) -> dict:
        response = await self.request("GET", "/microbus/init")
        return await self._validate_response(response)

    async def get_preferences(self) -> Preferences:
        preferences_json = await self._validate_response(
            await self.request("GET", "/api/v2/Preferences/")
        )
        return Preferences.from_dict(preferences_json)

    async def get_profiles(self) -> list[Profile]:
        profiles_json = await self._validate_response(
            await self.request("GET", "/api/v2/Profiles/")
        )
        return [Profile.from_dict(p) for p in profiles_json]

    async def get_meter_readings(self) -> MeterReadings:
        meter_json = await self._validate_response(
            await self.request(
                "GET",
                (
                    "/api/v2/customers/"
                    f"{self.preferences.subject.customerNumber}/"
                    "agreements/"
                    f"{self.preferences.subject.agreementId}/"
                    "meter-readings/"
                    f"{datetime.now(UTC).year}/"
                ),
            )
        )

        return MeterReadings.from_dict(meter_json)

    async def get_ref_ids(self) -> tuple[str, str]:
        init_config = await self.microbus_init()

        customer_id = self.preferences.subject.customerNumber
        contract_id = self.preferences.subject.agreementId
        ref_id_electricity = ""
        ref_id_gas = ""

        all_client_details = init_config.get("klantgegevens")
        for client_details in all_client_details:
            if client_details.get("klantnummer") == customer_id:
                client_addresses = client_details.get("adressen")
                for client_address in client_addresses:
                    if (
                        client_address.get("klantnummer") == customer_id
                        and client_address.get("overeenkomstId") == contract_id
                    ):
                        contracts = client_address.get("contracten")
                        for contract in contracts:
                            if (
                                contract.get("marktsegment") == "E"
                            ):  # E stands for electricity, G for gas
                                ref_id_electricity = contract.get("refId")
                            else:
                                ref_id_gas = contract.get("refId")

        return ref_id_electricity, ref_id_gas

    async def get_rates(self) -> Rates:
        profiles = await self.get_profiles()
        current_profile: Profile | None = None
        for profile in profiles:
            if (
                profile.customerNumber == self.preferences.subject.customerNumber
                and profile.agreementId == self.preferences.subject.agreementId
            ):
                current_profile = profile
                break
        if not current_profile:
            raise ApiError("Cant find profile")

        ref_id_electricity, ref_id_gas = await self.get_ref_ids()

        req_data = {
            "HouseNumber": current_profile.houseNumber,
            "ZipCode": current_profile.postalCode,
        }
        if ref_id_electricity:
            req_data["ReferenceIdElectricity"] = ref_id_electricity
            req_data["AgreementIdElectricity"] = current_profile.agreementId
        if ref_id_gas:
            req_data["ReferenceIdGas"] = ref_id_gas
            req_data["AgreementIdGas"] = current_profile.agreementId

        response = await self.request(
            "GET",
            f"/api/v2/customers/{current_profile.customerNumber}/rates?{urlencode(req_data)}",
        )
        if response.status == 404:
            response = await self.request("GET", "/api/tariffs")
        pricing_details = await self._validate_response(response)
        if "huidig" in pricing_details:
            pricing_details = pricing_details["huidig"]

        return Rates.from_dict(pricing_details)

    async def update(self) -> dict:
        self.result = {}
        try:
            self.preferences = await self.get_preferences()
        except ApiError:
            _LOGGER.error("Cant get preferences")
            return self.result

        try:
            await self.update_usage_values(self.result)
        except ApiError:
            _LOGGER.error("Cant update usage values")
            pass

        try:
            await self.update_contract_values(self.result)
        except ApiError:
            _LOGGER.error("Cant update contract values")
            pass

        return self.result

    async def update_usage_values(self, result: dict) -> None:
        _LOGGER.debug("Retrieving meter values")

        meter_readings = await self.get_meter_readings()

        electricity_reading: Reading | None = meter_readings.last_electricity_reading
        gas_reading: Reading | None = meter_readings.last_gas_reading

        if electricity_reading:
            result["electricity_consumption_low"] = (
                electricity_reading.offPeakConsumption
            )
            result["electricity_consumption_high"] = (
                electricity_reading.normalConsumption
            )
            result["electricity_consumption_total"] = (
                electricity_reading.offPeakConsumption
                + electricity_reading.normalConsumption
            )
            result["electricity_return_low"] = electricity_reading.offPeakFeedIn
            result["electricity_return_high"] = electricity_reading.normalFeedIn
            result["electricity_return_total"] = (
                electricity_reading.offPeakFeedIn + electricity_reading.normalFeedIn
            )
            result["measurement_date_electricity"] = electricity_reading.readingDate

        if gas_reading:
            result["gas_consumption"] = gas_reading.gas
            result["measurement_date_gas"] = gas_reading.readingDate

    async def update_contract_values(self, result: dict) -> None:
        _LOGGER.debug("Retrieving contract values")

        pricing_details = await self.get_rates()

        if pricing_details.stroom:
            result["electricity_price_single"] = (
                pricing_details.stroom.leveringEnkelAllIn
            )
            result["electricity_price_low"] = pricing_details.stroom.leveringLaagAllIn
            result["electricity_price_high"] = pricing_details.stroom.leveringHoogAllIn
            result["electricity_return_price"] = (
                pricing_details.stroom.terugleverVergoeding
            )
            result["electricity_return_cost"] = (
                pricing_details.stroom.terugleverKostenIncBtw
            )

        if pricing_details.gas:
            result["gas_price"] = pricing_details.gas.leveringAllIn

    # Alias for update method
    async_update = update