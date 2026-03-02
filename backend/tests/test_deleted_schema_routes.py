from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from .mixins import DefaultMixin


class TestDeletedSchemaRoutes(DefaultMixin):
    def test_openapi_schema_removed_after_deletion(
        self, dbsession: Session, authorized_client: TestClient
    ):
        # Verify 'Person' is in OpenAPI
        response = authorized_client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        # The paths in OpenAPI usually contain the operations.
        # /entity/person is the path for listing entities.
        assert "/entity/person" in openapi["paths"]

        # Delete 'Person' schema
        # We need to use the slug 'person' or the ID.
        response = authorized_client.delete("/schema/person")
        assert response.status_code == 200

        # Verify 'Person' is gone from OpenAPI
        response = authorized_client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        assert "/entity/person" not in openapi["paths"]

    def test_routes_removed_after_deletion(
        self, dbsession: Session, authorized_client: TestClient
    ):
        # Verify routes exist
        response = authorized_client.get("/entity/person")
        assert response.status_code == 200

        # Delete schema
        authorized_client.delete("/schema/person")

        # Verify route returns 404
        response = authorized_client.get("/entity/person")
        assert response.status_code == 404
