import json
from time import sleep
import requests
from api.config import CURRENT_IP
from django.core.management.base import BaseCommand

test_email = "org1@test.com"
test_password = "123"
test_token = ""


def register_user():
    url = f"http://{CURRENT_IP}:8000/api/v1/register"
    test_data = {
        "email": test_email,
        "username": "testOrg",
        "password": test_password,
    }
    response = requests.post(url, json=test_data)
    print("register_user:", response.text)


def create_organization(api_client):
    response = api_client.request(
        endpoint="/organizations", method="POST", data={"name": "testOrg"}
    )
    print("create_organization:", response)
    return response.get("id")


def get_organization(api_client):
    response = api_client.request(endpoint="/organizations", method="GET")
    print("get_organization:", response)


def create_consortium(api_client, baseOrgId):
    response = api_client.request(
        endpoint="/consortiums",
        method="POST",
        data={"name": "testConsortium", "baseOrgId": baseOrgId},
    )
    print("create_consortium:", response)
    return response.get("id")


def create_memberships(api_client, consortium_id, org_id, membership_num):
    for i in range(membership_num - 1):
        response = api_client.request(
            endpoint=f"/consortium/{consortium_id}/memberships",
            method="POST",
            data={
                "org_uuid": org_id,
                "name": f"testMembership-{i+1}",
            },
        )
        print("create_membership:", response)


def create_environment(api_client, consortium_id):
    response = api_client.request(
        endpoint=f"/consortium/{consortium_id}/environments",
        method="POST",
        data={"name": "testEnv"},
    )
    print("create_environment:", response)
    return response.get("id")


def init_environment(api_client, environment_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/init",
        method="POST",
    )
    print("init environment:", response)


def get_memberships(api_client, consortium_id):
    response = api_client.request(
        endpoint=f"/consortium/{consortium_id}/memberships",
        method="GET",
    )
    print("get_memberships:", response)
    return response


def join_environment(api_client, environment_id, membership_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/join",
        method="POST",
        data={"membership_id": membership_id},
    )
    print(f"{membership_id} join_environment:", response)


def start_environment(api_client, environment_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/start",
        method="POST",
    )
    print("start_environment:", response)


def activate_environment(api_client, environment_id, org_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/activate",
        method="POST",
        data={"org_id": org_id},
    )
    print("activate_environment:", response)


def get_chaincodes(api_client, environment_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/chaincodes",
        method="GET",
    )
    print("get_chaincodes:", response)
    return response


def search_mem_peers(api_client, org_id, env_id):
    response = api_client.request(
        endpoint=f"/search/search-peers-membership?org_id={org_id}&env_id={env_id}",
        method="GET",
    )
    return response


def install_chaincode(api_client, environment_id, chaincode_id, peer_node_list):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/chaincodes/install",
        method="POST",
        data={"id": chaincode_id, "peer_node_list": peer_node_list},
    )
    print("install_chaincode:", response)


def get_resourceset_by_membership_org(
    api_client, membership_id, environment_id, org_id
):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/resource_sets?membership_id={membership_id}&org_id={org_id}",
        method="GET",
    )
    print("get_resourceset_by_membership:", response)
    return response


def approve_for_org(api_client, env_id, resource_set_id):
    response = api_client.request(
        endpoint=f"/environments/{env_id}/chaincodes/approve_for_my_org",
        method="POST",
        data={
            "chaincode_name": "Firefly",
            "chaincode_version": "1.0",
            "channel_name": "default",
            "resource_set_id": resource_set_id,
            "sequence": 1,
        },
    )
    print("approve_for_org:", response)


def commit_chaincode(api_client, environment_id, resource_set_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/chaincodes/commit",
        method="POST",
        data={
            "chaincode_name": "Firefly",
            "chaincode_version": "1.0",
            "channel_name": "default",
            "resource_set_id": resource_set_id,
            "sequence": 1,
        },
    )
    print("commit_chaincode:", response)


def start_firefly(api_client, environment_id):
    response = api_client.request(
        endpoint=f"/environments/{environment_id}/start_firefly",
        method="POST",
    )
    print("start_firefly:", response)


class APIClient:
    def __init__(self, backend_url):
        self.session = requests.Session()
        self.base_url = f"{backend_url}/api/v1"
        self.session.headers.update({"Content-Type": "application/json"})

    def login(self, email, password):
        """Log in to the API and store the token"""
        url = f"{self.base_url}/login"
        response = self.session.post(url, json={"email": email, "password": password})
        print("login:", response.text)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        token = response.json().get("data").get("token")
        print("token:", token)
        if token:
            self.session.headers["Authorization"] = f"JWT {token}"
            return token
        return None

    def request(self, endpoint, method="GET", data=None):
        """General method to make requests"""
        url = f"{self.base_url}{endpoint}"
        if method == "GET":
            response = self.session.get(url)
        elif method == "POST":
            response = self.session.post(url, json=data)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        if response.headers.get("Content-Type", "").startswith("application/json"):
            try:
                return response.json()
            except ValueError:
                print("Response is not valid JSON.")
        else:
            return response.text


class Command(BaseCommand):

    def add_arguments(self, parser):
        # 添加一个名为`membership_number`的必需参数
        parser.add_argument(
            "membership_number", type=int, help="Input the number of test memberships"
        )

    def handle(self, *args, **options):
        membership_num = options["membership_number"]

        # register a test user
        register_user()

        # login based the test user to get token
        api_client = APIClient(f"http://{CURRENT_IP}:8000")
        token = api_client.login(test_email, test_password)
        print(f"Logged in with token: {token}")

        # create a test Organization
        org_id = create_organization(api_client=api_client)
        print(f"Created Organization ID: {org_id}")

        # create a consortium based org
        consortium_id = create_consortium(api_client=api_client, baseOrgId=org_id)
        print(f"Created Consortium ID: {consortium_id}")

        # create memberships for the consortium
        create_memberships(
            api_client=api_client,
            consortium_id=consortium_id,
            org_id=org_id,
            membership_num=membership_num,
        )

        # create a test environment
        environment_id = create_environment(
            api_client=api_client, consortium_id=consortium_id
        )
        print(f"Created Environment ID: {environment_id}")

        # init the environment
        init_environment(api_client=api_client, environment_id=environment_id)

        # get the memberships
        memberships = get_memberships(
            api_client=api_client, consortium_id=consortium_id
        )

        # all memberships join the environment
        for membership in memberships:
            # join the environment
            join_environment(
                api_client=api_client,
                environment_id=environment_id,
                membership_id=membership.get("id"),
            )

        # start the environment
        start_environment(api_client=api_client, environment_id=environment_id)
        sleep(4)

        # activate the environment
        activate_environment(
            api_client=api_client, environment_id=environment_id, org_id=org_id
        )

        # get Firefly chaincode id
        chaincodes = get_chaincodes(
            api_client=api_client, environment_id=environment_id
        )
        chaincode_id = ""
        for chaincode in chaincodes:
            if chaincode.get("name") == "Firefly":
                chaincode_id = chaincode.get("id")
                print(f"Firefly Chaincode ID: {chaincode_id}")
                break

        # get the memberships and  peers
        mem_peers = search_mem_peers(
            api_client=api_client, org_id=org_id, env_id=environment_id
        )
        print("mem_peers:", mem_peers)

        # install Fireflys chaincode
        for mem_peer in mem_peers:
            install_chaincode(
                api_client=api_client,
                environment_id=environment_id,
                chaincode_id=chaincode_id,
                peer_node_list=[mem_peer["peer_node"]],
            )
            print(f"Installed Firefly Chaincode for {mem_peer['membership_name']}")

        # approve chaincode for all orgs
        for membership in memberships:
            resource_sets = get_resourceset_by_membership_org(
                api_client=api_client,
                membership_id=membership.get("id"),
                environment_id=environment_id,
                org_id=org_id,
            )
            approve_for_org(
                api_client=api_client,
                env_id=environment_id,
                resource_set_id=resource_sets[0].get("id"),
            )
            print(f"Approved for membership: {membership.get('name')}")

        # commit chaincode by membership0
        resource_sets = get_resourceset_by_membership_org(
            api_client=api_client,
            membership_id=memberships[0].get("id"),
            environment_id=environment_id,
            org_id=org_id,
        )
        commit_chaincode(
            api_client=api_client,
            environment_id=environment_id,
            resource_set_id=resource_sets[0].get("id"),
        )
        print(f"Committed chaincode by membership {memberships[0].get('name')}")

        # start firefly
        start_firefly(api_client=api_client, environment_id=environment_id)
        print("Started Firefly")
