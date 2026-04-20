from argparse import ArgumentParser
from time import time, sleep
from typing import Any

import requests
import jwt

class JwtHandler:
    """
    Manages JWT authentication with automatic token refresh.
    
    Handles acquisition and refreshing of JWT access tokens, ensuring requests
    are authenticated with valid tokens. Automatically refreshes tokens before expiry.
    
    Args:
        username: Username for initial authentication.
        password: Password for initial authentication.
        base_url: The base URL for the API.
        access_endpoint: Endpoint path for token access.
        refresh_endpoint: Endpoint path for token refresh.
        skew_seconds: Time buffer in seconds before token expiry to trigger refresh.
            Defaults to 60.
    
    Attributes:
        base_url: The base URL for the API endpoints.
        skew_seconds: Seconds subtracted from token expiry for clock skew/latency.
        access_endpoint: The API endpoint for obtaining access tokens.
        refresh_endpoint: The API endpoint for refreshing access tokens.
        authorized: Whether the handler has valid credentials.
    
    Example:
        >>> handler = JwtHandler(
        ...     username="user",
        ...     password="pass",
        ...     base_url="https://api.example.com",
        ...     access_endpoint="/auth/token/",
        ...     refresh_endpoint="/auth/token/refresh/"
        ... )
        >>> token = handler.token  # Automatically refreshes if needed
    """
    
    def __init__(
        self,
        username: str,
        password: str,
        base_url: str,
        access_endpoint: str,
        refresh_endpoint: str,
        skew_seconds: int = 60,
    ) -> None:
        self.base_url: str = base_url
        self.skew_seconds: int = skew_seconds
        self.access_endpoint: str = access_endpoint
        self.refresh_endpoint: str = refresh_endpoint

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry_timestamp: int | None = None
        
        self.authorized: bool = False

        self._get_access_token(username=username, password=password)

    @classmethod
    def from_refresh_token(
        cls,
        refresh_token: str,
        base_url: str,
        access_endpoint: str,
        refresh_endpoint: str,
        skew_seconds: int = 60,
    ) -> "JwtHandler":
        """Herstel een JwtHandler vanuit een opgeslagen refresh token (bijv. uit een browsercookie)."""
        obj = cls.__new__(cls)
        obj.base_url = base_url
        obj.skew_seconds = skew_seconds
        obj.access_endpoint = access_endpoint
        obj.refresh_endpoint = refresh_endpoint
        obj._access_token = None
        obj._refresh_token = refresh_token
        # Zet expiry op 0 zodat bij het eerste gebruik van .token direct een refresh plaatsvindt.
        obj._token_expiry_timestamp = 0
        obj.authorized = False
        obj._get_refresh_token()
        return obj

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Send a POST request to the specified endpoint with JSON data.
        Args:
            endpoint (str): The API endpoint path to append to the base URL.
            data (dict[str, Any]): A dictionary containing the data to be sent as JSON in the request body.
        Returns:
            dict[str, Any]: The JSON response from the server parsed as a dictionary.
        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns an unsuccessful status code.
            requests.exceptions.RequestException: If there's a network-related error or connection problem.
        """
        
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_refresh_token(self) -> str:
        """
        Get the current refresh token.
        Returns:
            str: The current refresh token.
        """
        return self._refresh_token
    
    def clear_tokens(self) -> None:
        """
        Clear the stored access and refresh tokens.
        This method resets the internal access token, refresh token, and expiry timestamp
        to None, effectively logging out the user.
        Returns:
            None: This method does not return a value.
        """
        self._access_token = None
        self._refresh_token = None
        self._token_expiry_timestamp = None
        self.authorized = False

    @property
    def token(self) -> str:
        """
        Get the current access token, refreshing it if necessary.
        This method checks if the current access token has expired. If it has,
        it automatically refreshes the token by calling the internal refresh
        method before returning the access token.
        Returns:
            str: The current valid access token.
        Raises:
            May raise exceptions from _get_refresh_token() if token refresh fails.
        """

        if self._token_is_expired():
            self._get_refresh_token()
        return self._access_token

    def _token_is_expired(self) -> bool:
        """
        Check if the current token has expired.
        Compares the current time against the stored token expiry timestamp
        to determine if the token is still valid.
        Returns:
            bool: True if the token has expired (current time >= expiry timestamp),
                  False if the token is still valid.
        """
        
        return time() >= self._token_expiry_timestamp

    def _get_refresh_token(self) -> None:
        """
        Refresh the access token using the refresh token.
        This method sends a POST request to the refresh endpoint with the current
        refresh token to obtain a new access token. It updates the internal access
        token and calculates the new token expiry timestamp with a skew adjustment.
        Returns:
            None: This method updates instance variables but does not return a value.
        Raises:
            May raise exceptions from the post() method if the API request fails.
        Side Effects:
            - Updates self._access_token with the new access token
            - Updates self.authorized to True if refresh is successful
            - Updates self._token_expiry_timestamp with the new expiry time minus skew
        """
        try:
            token = self.post(
                endpoint=self.refresh_endpoint, data={"refresh": self._refresh_token}
            )
            self.authorized = True
            self._access_token = token.get("access")
            self._token_expiry_timestamp = (
                self._get_token_expiry_seconds(token.get("access")) - self.skew_seconds
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.authorized = False
            raise e
            

    def _get_access_token(self, username: str, password: str) -> None:
        """
        Retrieve and store access and refresh tokens by authenticating with username and password.
        This method sends a POST request to the access endpoint with the provided credentials,
        then extracts and stores the access token, refresh token, and calculates the token 
        expiry timestamp with a skew adjustment.
        Args:
            username (str): The username for authentication.
            password (str): The password for authentication.
        Returns:
            None: This method updates instance variables (_access_token, _refresh_token, 
                  _token_expiry_timestamp) but does not return a value.
        Raises:
            May raise exceptions from the post() method if authentication fails or 
            if there are network/connection issues.
        Side Effects:
            - Updates self._access_token with the obtained access token
            - Updates self._refresh_token with the obtained refresh token
            - Updates self._token_expiry_timestamp with the expiry time minus skew
            - Sets self.authorized to True upon successful authentication
        """

        token = self.post(
            endpoint=self.access_endpoint,
            data={"username": username, "password": password},
        )
        self.authorized = True

        self._access_token = token.get("access")
        self._refresh_token = token.get("refresh")
        self._token_expiry_timestamp = (
            self._get_token_expiry_seconds(token.get("access")) - self.skew_seconds
        )

    def _get_token_expiry_seconds(self, access_token: str) -> int:
        """
        Extracts and returns the expiration timestamp from a JWT access token.
        Args:
            access_token (str): The JWT access token to decode.
        Returns:
            int: The expiration timestamp (Unix epoch time) from the token's payload.
        Note:
            This method decodes the JWT without verifying the signature.
            The signature verification is disabled for performance or when verification
            is handled elsewhere in the authentication flow.
        """

        payload = jwt.decode(access_token, options={"verify_signature": False})
        print(payload)
        return payload["exp"]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--username", required=True, help="Username for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    args = parser.parse_args()

    base_url = "http://localhost:8000/"
    access_endpoint = "api/token/"
    refresh_endpoint = "api/token/refresh/"

    handler = JwtHandler(
        base_url=base_url,
        access_endpoint=access_endpoint,
        refresh_endpoint=refresh_endpoint,
        username=args.username,
        password=args.password,
    )
    print("Access Token:", handler._access_token)
    print("Refresh Token:", handler._refresh_token)
    print("Token Expiry Timestamp:", handler._token_expiry_timestamp)
    
    sleep(300)
    
    print(handler.token)
    
