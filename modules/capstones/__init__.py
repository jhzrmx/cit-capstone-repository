from fastapi import FastAPI

from modules.capstones.api_search_capstones import register_api_search_capstones_route
from .get_capstone_overview import register_capstone_overview_route

def configure_capstone_module(app: FastAPI):
    register_capstone_overview_route(app)
    register_api_search_capstones_route(app)