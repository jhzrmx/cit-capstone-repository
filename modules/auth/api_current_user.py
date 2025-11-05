from fastapi import Depends, FastAPI

from helpers.session import get_current_user_jwt


def register_api_current_user_route(app: FastAPI):
    @app.get("/api/users/current")
    def read_current_user(claims=Depends(get_current_user_jwt)):
        if not claims:
            return {
                "status": "error",
                "message": "Unauthorized"
            }
        return {
            "status": "ok",
            "message": "OK",
            "data": {
                "email": claims["sub"], 
                "role": claims["role"]
            }
        }
