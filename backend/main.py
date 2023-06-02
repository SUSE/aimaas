from fastapi_pagination import add_pagination

from . import create_app, models
from .database import engine


models.Base.metadata.create_all(engine)
app = create_app()
add_pagination(app)
