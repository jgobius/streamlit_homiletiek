import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


class PostalCodeAPI:

    def __init__(self):
        self.api_url = os.environ.get("POSTAL_CODE_API_URL")

    def validate_postal_code(
        self,
        postal_code: str,
        house_number: str,
        house_number_addition: str = "",
    ) -> dict[str, Any]:

        response = requests.get(f"{self.api_url}/{postal_code}/{house_number}")

        response.raise_for_status()

        data = response.json()

        return data[0]

