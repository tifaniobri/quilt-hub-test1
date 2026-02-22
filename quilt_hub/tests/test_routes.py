import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home_returns_200_and_contains_quilt(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"quilt" in response.data.lower()


def test_gallery_returns_200(client):
    response = client.get("/gallery")
    assert response.status_code == 200


def test_tools_returns_200(client):
    response = client.get("/tools")
    assert response.status_code == 200


def test_nonexistent_returns_404(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404
