"""Test the Main class"""

from unittest.mock import MagicMock, patch

from napps.hackinsdn.mirror.main import Main

from kytos.lib.helpers import get_controller_mock, get_test_client


class TestMain:
    """Test the Main class"""

    def setup_method(self):
        """Execute steps before each test"""
        Main.get_pipeline_controller = MagicMock()
        controller = get_controller_mock()
        self.napp = Main(controller)
        self.api_client = get_test_client(controller, self.napp)
        self.base_endpoint = "hackinsdn/mirror/v1"

    def test_list_mirror_non_empty(self):
        """Test if list return all mirror stored."""
        mirrors = {
            "1": {
                "circuit_id": "xyz",
                "name": "test1",
                "status": "Enabled",
                "switch": "00:00:00:00:00:00:00:01",
                "target_port": 2,
                "type": "EVC",
                "inserted_at": "2024-07-29T06:39:23.939000",
                "updated_at": "2024-07-29T06:39:23.939000",
                "original_flow": '{"flows": []}',
                "mirror_flow": '{"flows": []}',
            },
            "2": {
                "circuit_id": "xyz",
                "name": "test1",
                "status": "Disabled",
                "switch": "00:00:00:00:00:00:00:01",
                "target_port": 2,
                "type": "EVC",
                "inserted_at": "2024-07-29T06:39:23.939000",
                "updated_at": "2024-07-29T06:39:23.939000",
                "original_flow": '{"flows": []}',
                "mirror_flow": '{"flows": []}',
            },
        }
        get_mirrors = self.napp.mongo_controller.get_mirrors
        get_mirrors.return_value = mirrors

        response = self.api_client.get(self.base_endpoint)
        assert response.status_code == 200, response.data
        assert response.json() == mirrors
        get_circuits.assert_called()
