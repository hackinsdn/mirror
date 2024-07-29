"""Main module of hackinsdn/mirror Kytos Napp."""

from kytos.core import KytosNApp, log, rest
from napps.optus.mirror import settings
from kytos.core.rest_api import (
    HTTPException,
    JSONResponse,
    Request,
    get_json_or_400
)
from uuid import uuid4
import requests
import json
import copy
import traceback
from .controllers import MongoController


class Main(KytosNApp):

    def setup(self):
        """
        Traffic Mirror Napp. Each mirror data contains:
        mirrors = {
            "mirror_id1" : {
                "name": "...",
                "type": "...",
                "status": "...",
                "target_port": "...",
                "...": "...",
                "original_flow": {},
                "mirror_flow": {},
            }
        }
        """
        self.mirrors = {}
        self.mongo_controller = self.get_mongo_controller()
        self.load_mirrors()

    def execute(self):
        """Do nothing."""
        log.info("Mirror NApp running...")

    @staticmethod
    def get_mongo_controller():
        """Get MongoController"""
        return MongoController()

    def load_mirrors(self):
        """Load mirrors from DB."""
        self.mirrors = self.mongo_controller.get_mirrors()

    def validate_switch(self, switch):
        """Validates that the specified switch exists in the topology."""
        url = 'http://0.0.0.0:8181/api/kytos/topology/v3/switches'
        headers = {'Content-Type': 'application/json'}
        current_switches = requests.get(url, headers=headers).json()

        return switch in [current_switch for current_switch in current_switches["switches"]]


    def validate_circuit(self, circuit):
        """Validates that the specified circuit exists in mef_eline."""
        if len(circuit) != 14:
            return False

        url = 'http://0.0.0.0:8181/api/kytos/mef_eline/v2/evc/'
        headers = {'Content-Type': 'application/json'}
        current_circuits = requests.get(url, headers=headers).json()

        return circuit in current_circuits.keys()


    def validate_interface(self, interface):
        """Validates that the specified interface exists in the topology."""
        url = 'http://0.0.0.0:8181/api/kytos/topology/v3/interfaces'
        headers = {'Content-Type': 'application/json'}
        current_interfaces = requests.get(url, headers=headers).json()

        return interface in [current_interfaces['interfaces'][key]['id'] for key in current_interfaces['interfaces']]


    def create_EVC_mirror(self, command):
        """Creates a mirror for a specified EVC."""
        try:
            name = command["name"]
            circuit_id = command["circuit_id"]
            switch = command["switch"]
            target_port = int(command["target_port"].split(":")[-1])

            if self.validate_switch(switch) and self.validate_circuit(circuit_id):

                #CREATE THE MIRROR
                cookie = int("0xaa" + circuit_id, 16)

                flow_NApp_url = f'http://0.0.0.0:8181/api/kytos/flow_manager/v2/flows/{switch}'
                headers = {'Content-Type': 'application/json'}

                flow_response = requests.get(flow_NApp_url, headers=headers).json()

                original_flow = {"flows":[]}
                new_flow = {"flows": []}

                for flow in flow_response[switch]["flows"]:
                    if (flow["cookie"] == cookie):
                        for extraneous_key in ["stats","hard_timeout","id","idle_timeout","switch", "cookie_mask"]:
                            flow.pop(extraneous_key,None)

                        original_flow['flows'].append(copy.deepcopy(flow))
                        flow["instructions"][0]["actions"].append({"action_type": "output", "port": target_port})
                        new_flow['flows'].append(flow)

                payload = json.dumps(new_flow)
                res = requests.post(flow_NApp_url, headers=headers, data=payload)
                if res.status_code != 202:
                    log.error(f"failed to create flows status={res.status_code} text={res.text} payload={payload}")
                    raise HTTPException(400, f"Fail to create mirror flows. Return from flow_manager: {res.text}")

                #ADD MIRROR TO MAIN/ACTIVE MIRROR LIST
                mirror_id = uuid4().hex[:14]

                self.mirrors[mirror_id] = {
                    "name": name,
                    "type": "EVC",
                    "status": "Enabled",
                    "circuit_id": circuit_id,
                    "switch": switch,
                    "target_port": target_port,
                    "original_flow": original_flow,
                    "mirror_flow": new_flow
                }

                self.mongo_controller.upsert_mirror(
                    mirror_id, self.mirrors[mirror_id]
                )

                return JSONResponse(f"Mirror created: {mirror_id}")

            else:
                raise HTTPException(400, f"Switch not found: {switch}")

        except KeyError as err:
            err_msg = traceback.format_exc().replace("\n", ", ")
            log.error(f"Error handling request: {err}. Traceback: {err_msg}")
            raise HTTPException(400, "Invalid request")


    def create_interface_mirror(self, command):
        """Creates a mirror for a specified interface."""
        try:
            name = command["name"]
            interface = command["interface"]
            target_port = int(command["target_port"].split(":")[-1])
            switch = ":".join(command["interface"].split(":")[:-1])
            interface_port = int(command["interface"].split(":")[-1])

            if self.validate_interface(interface):

                #CREATE THE MIRROR
                flow_NApp_url = f'http://0.0.0.0:8181/api/kytos/flow_manager/v2/flows/{switch}'
                headers = {'Content-Type': 'application/json'}

                flow_response = requests.get(flow_NApp_url, headers=headers).json()

                original_flow = {"flows":[]}
                new_flow = {"flows": []}

                for flow in flow_response[switch]["flows"]:
                    if "in_port" in flow["match"]:
                        in_port = flow["match"]["in_port"]
                    else:
                        in_port = []

                    out_ports = [action["port"] for action in flow["actions"] if "port" in action]

                    if (interface_port == in_port) or (interface_port in out_ports):
                        for extraneous_key in ["stats","hard_timeout","priority","id","idle_timeout","switch"]:
                            flow.pop(extraneous_key,None)

                        original_flow['flows'].append(copy.deepcopy(flow))
                        flow["actions"].append({"action_type": "output", "port": target_port})
                        new_flow['flows'].append(flow)

                payload = json.dumps(new_flow)
                res = requests.post(flow_NApp_url, headers=headers, data=payload)
                log.info(f"create flows status={res.status_code} text={res.text}")

                #ADD MIRROR TO MAIN/ACTIVEMIRROR LIST
                mirror_id = uuid4().hex[:14]

                self.mirrors[mirror_id] = {
                    "name": name,
                    "type": "interface",
                    "status": "Enabled",
                    "switch": switch,
                    "interface": interface,
                    "target_port": target_port,
                    "original_flow": original_flow,
                    "mirror_flow": new_flow
                }

                self.mongo_controller.upsert_mirror(
                    mirror_id, self.mirrors[mirror_id]
                )

                return JSONResponse(f"Mirror created: {mirror_id}")
            else:
                raise HTTPException(400, f"Interface not found: {interface}")

        except KeyError as e:
            raise HTTPException(400, f"Invalid request: {e}")

    @rest('/v1/', methods=['POST'])
    def create_mirror(self, request: Request) -> JSONResponse:
        """Creates a mirror according to the specified mirror type."""
        command = get_json_or_400(request, self.controller.loop)
        log.info(f"NApp hackinsdn/mirror received request: {command}")

        if "circuit_id" in command:
            if "to_tag" in command:
                raise HTTPException(400, "Unsupported feature")
            else:
                return self.create_EVC_mirror(command)
        elif "interface" in command:
            return self.create_interface_mirror(command)

        elif "match" in command:
            raise HTTPException(400, "Unsupported feature")
        else:
            log.info("NApp optus/mirror invalid request")
            raise HTTPException(400, "Invalid request")

    @rest('/v1/', methods=['GET'])
    def list_enabled_mirrors(self, request: Request) -> JSONResponse:
        """Returns a json with all the enabled mirrors."""
        return JSONResponse(
            {k: v for k, v in self.mirrors.items() if v["status"] == "Enabled"}
        )

    @rest('/v1/all', methods=['GET'])
    def list_all_mirrors(self, request: Request) -> JSONResponse:
        """Returns a json with all the created mirrors."""
        return JSONResponse(self.mirrors)

    @rest('/v1/{mirror_id}', methods=['PATCH'])
    def change_mirror_status(self, request: Request) -> JSONResponse:
        """Changes a mirror status, using the mirror_id specified in the API call url."""
        mirror_id = request.path_params["mirror_id"]
        command = get_json_or_400(request, self.controller.loop)
        change_attrs = {"enabled": bool, "name": str}

        if mirror_id not in self.mirrors:
            raise HTTPException(404, "Mirror not found (invalid mirror_id)")
        for attr in command:
            if attr not in change_attrs:
                raise HTTPException(400, f"Invalid parameter {attr}")
            cls = change_attrs[attr]
            if not isinstance(attr, cls):
                raise HTTPException(
                    400, f"Invalid parameter type {attr} (expecting {cls})"
                )

        if "enabled" in command:
            #DISABLE THE MIRROR BY REMOVING THE FLOW
            if self.mirrors[mirror_id]["type"] in ["EVC", "interface"]:
                switch = self.mirrors[mirror_id]["switch"]
                flow_NApp_url = f'http://0.0.0.0:8181/api/kytos/flow_manager/v2/flows/{switch}'
                headers = {'Content-Type': 'application/json'}
                current_status = self.mirrors[mirror_id]["status"]

                if status_request == False and current_status == "Enabled":
                    flow_to_send = self.mirrors[mirror_id]["original_flow"]
                    new_status = "Disabled"

                elif status_request == True and current_status == "Disabled":
                    flow_to_send = self.mirrors[mirror_id]["mirror_flow"]
                    new_status = "Enabled"

                else:
                    raise HTTPException(400, "Invalid request - nothing to do")

                payload = json.dumps(flow_to_send)
                flow_response = requests.post(flow_NApp_url, headers=headers, data=payload).json()

                self.mirrors["mirrors"][mirror_id]["status"] = new_status
                self.mongo_controller.upsert_mirror(
                    mirror_id, self.mirrors[mirror_id]
                )

                return JSONResponse(f"{new_status} mirror: {mirror_id}")

            else:
                raise HTTPException(400, f"Invalid mirror: {mirror_id}")

        else:
            raise HTTPException(400, "Invalid request")

    def shutdown(self):
        """Do nothing."""
        log.info("NApp optus/mirror shutting down.")
