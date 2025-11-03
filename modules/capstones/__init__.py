from fastapi import FastAPI

from modules.capstones.api_get_capstone import register_api_get_capstone_route
from modules.capstones.api_get_capstones import register_api_get_capstones_route
from modules.capstones.api_search_capstones import register_api_search_capstones_routes
from modules.capstones.api_search_capstones_orig import register_api_search_capstones_orig_route
from modules.capstones.api_summarize import register_api_summarize_route
from .get_capstone_overview import register_capstone_overview_route

def configure_capstone_module(app: FastAPI):
    register_capstone_overview_route(app)
    register_api_search_capstones_orig_route(app)
    register_api_get_capstones_route(app)
    register_api_get_capstone_route(app)
    register_api_search_capstones_routes(app)
    register_api_summarize_route(app)