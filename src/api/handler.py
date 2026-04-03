from typing import Any
from time import time

import requests
import streamlit as st

from .jwthandler import JwtHandler


class APIHandler:
    """
    A handler class for making HTTP API requests.
    This class provides a simple interface for making GET and POST requests to a REST API
    with a specified base URL.
    Attributes:
        base_url (str): The base URL for all API requests.
    Methods:
        get(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            Makes a GET request to the specified endpoint.
            Args:
                endpoint (str): The API endpoint to request (relative to base_url).
                params (dict[str, Any] | None, optional): Query parameters to include in the request.
                    Defaults to None.
            Returns:
                dict[str, Any]: The JSON response from the API.
            Raises:
                requests.exceptions.HTTPError: If the request returns an error status code.
        post(endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
            Makes a POST request to the specified endpoint.
            Args:
                endpoint (str): The API endpoint to request (relative to base_url).
                data (dict[str, Any]): The JSON data to send in the request body.
            Returns:
                dict[str, Any]: The JSON response from the API.
            Raises:
                requests.exceptions.HTTPError: If the request returns an error status code.
    """

    def __init__(self, base_url: str, jwt_handler: JwtHandler) -> None:
        """
        Initialize the handler with a base URL.
        Args:
            base_url (str): The base URL for API requests.
        """

        self.base_url = base_url
        self.jwt_handler = jwt_handler

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Performs a GET request to the specified API endpoint.
        Args:
            endpoint (str): The API endpoint path to append to the base URL.
            params (dict[str, Any] | None, optional): Query parameters to include in the request. Defaults to None.
        Returns:
            dict[str, Any]: The JSON response from the API parsed as a dictionary.
        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns an unsuccessful status code.
            requests.exceptions.RequestException: If there's an error making the request.
            ValueError: If the response cannot be parsed as JSON.
        """

        url = f"{self.base_url}/{endpoint}"
        
        headers = {
                "Authorization": f"Bearer {self.jwt_handler.token}",
                "Content-Type": "application/json",
            }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    def post(
        self, endpoint: str, data: dict[str, Any], require_token: bool = True
    ) -> dict[str, Any]:
        """
        Send a POST request to the specified endpoint with the given data.
        Args:
            endpoint (str): The API endpoint to send the POST request to.
            data (dict[str, Any]): The data to be sent in the request body as JSON.
            session_token (str): The session token for authentication.
        Returns:
            dict[str, Any]: The JSON response from the API as a dictionary.
        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns an unsuccessful status code.
            requests.exceptions.RequestException: If there is a network-related error during the request.
        """

        url = f"{self.base_url}/{endpoint}"
        if require_token:
            headers = {
                "Authorization": f"Bearer {self.jwt_handler.token}",
                "Content-Type": "application/json",
            }
            response = requests.post(url, json=data, headers=headers)
        else:
            response = requests.post(url, json=data)    
            
        response.raise_for_status()
        return response.json()
    
    def put(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Send a PUT request to the specified endpoint with the given data.
        Args:
            endpoint (str): The API endpoint to send the PUT request to.
            data (dict[str, Any]): The data to be sent in the request body as JSON.
        Returns:
            dict[str, Any]: The JSON response from the API as a dictionary.
        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns an unsuccessful status code.
            requests.exceptions.RequestException: If there is a network-related error during the request.
        """

        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.jwt_handler.token}",
            "Content-Type": "application/json",
        }
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str, timeout: int = 30) -> None:
        # Verwijder de resource op het opgegeven endpoint.
        # timeout=30 is voldoende voor DELETE-verzoeken die geen zware verwerking vereisen.
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.jwt_handler.token}",
            "Content-Type": "application/json",
        }
        response = requests.delete(url, headers=headers, timeout=timeout)
        response.raise_for_status()

    def patch(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Send a PATCH request to the specified endpoint with the given data.
        Args:
            endpoint (str): The API endpoint to send the PATCH request to.
            data (dict[str, Any]): The data to be sent in the request body as JSON.
        Returns:
            dict[str, Any]: The JSON response from the API as a dictionary.
        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns an unsuccessful status code.
            requests.exceptions.RequestException: If there is a network-related error during the request.
        """

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.jwt_handler.token}",
            "Content-Type": "application/json",
        }
        response = self.session.patch(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()