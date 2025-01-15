import logging
import re
from urllib.parse import parse_qs, urlparse

import aiohttp
from bs4 import BeautifulSoup


class LoginError(Exception):
    pass


class Auth:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self._username = username
        self._password = password

        self.logger = logging.getLogger(__name__)
        self.session = None

        if not self._check_config():
            raise AttributeError("Configuration is incomplete")

    def _check_config(self) -> bool:
        if not self._username:
            self.logger.error("Need a username!")
            return False
        if not self._password:
            self.logger.error("Need a password!")
            return False
        return True

    @staticmethod
    async def _get_verification_token(html_txt: str) -> str:
        soup = BeautifulSoup(html_txt, "html.parser")
        token_elem = soup.find("input", {"name": "__RequestVerificationToken"})

        return token_elem.attrs.get("value")

    @staticmethod
    async def _get_oidc_params(html_txt: str) -> dict:
        soup = BeautifulSoup(html_txt, "html.parser")

        code_elem = soup.find("input", {"name": "code"})
        scope_elem = soup.find("input", {"name": "scope"})
        state_elem = soup.find("input", {"name": "state"})
        session_state_elem = soup.find("input", {"name": "session_state"})

        # Logging the contents of *elem
        for item in [code_elem, scope_elem, state_elem, session_state_elem]:
            if item:
                logging.debug(f"Element tag: {item.name}, value: {item.attrs.get('value')}")
            else:
                logging.debug("Element is missing.")

        if not (code_elem and scope_elem and state_elem and session_state_elem):
            raise LoginError("Login failed, check your credentials?")

        return {
            "code": code_elem.attrs.get("value"),
            "scope": scope_elem.attrs.get("value").replace(" ", "+"),
            "state": state_elem.attrs.get("value"),
            "session_state": session_state_elem.attrs.get("value"),
        }

    @staticmethod
    async def is_session_expired(response: aiohttp.ClientResponse) -> bool:
        # If the session expired, the client is redirected to the SSO login.
        for history_response in response.history:
            if history_response.status != 302:
                continue
            location_header: str = history_response.headers.get("Location")
            if location_header is not None and re.search(
                "^.*://sso.greenchoice.nl/connect/authorize.*$", location_header
            ):
                return True

        # Sometimes we get Forbidden on token expiry
        if response.status == 403:
            return True

        return False

    async def _activate_session(self) -> aiohttp.ClientSession:
        if self.session:
            await self.session.close()

        self.session = aiohttp.ClientSession()
        self.logger.info("Retrieving login cookies")

        # first, get the login cookies and form data
        async with self.session.get(self.base_url) as login_page:
            login_url = login_page.url
            return_url = parse_qs(urlparse(str(login_url)).query).get("ReturnUrl", "")
            token = await self._get_verification_token(await login_page.text())

        # perform actual sign in
        self.logger.debug("Logging in with username and password")
        login_data = {
            "ReturnUrl": return_url,
            "Username": self._username,
            "Password": self._password,
            "__RequestVerificationToken": token,
            "RememberLogin": True,
        }
        async with self.session.post(login_url, data=login_data) as auth_page:
            auth_page.raise_for_status()
            oidc_params = await self._get_oidc_params(await auth_page.text())

        # exchange oidc params for a login cookie (automatically saved in session)
        self.logger.debug("Signing in using OIDC")
        async with self.session.post(f"{self.base_url}/signin-oidc", data=oidc_params) as response:
            response.raise_for_status()

        self.logger.debug("Login success")

        return self.session

    async def refresh_session(self) -> aiohttp.ClientSession:
        self.logger.debug("Session possibly expired, triggering refresh")
        try:
            await self._activate_session()
        except aiohttp.ClientError:
            self.logger.error(
                "Login failed! Please check your credentials and try again."
            )
            raise
        return self.session