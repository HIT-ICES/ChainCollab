from django.core.management.base import BaseCommand
from api.models import BPMN
import threading
import logging

# In-memory data structure to track events with created listeners
created_listeners = set()


def listener_exists(event):
    # Check if the listener for the event already exists in the set
    return event in created_listeners


def create_listener(event):
    # Logic to create a listener for the given event
    logging.info(f"Creating listener for event: {event}")
    # Simulate listener creation
    # After successfully creating a listener, add the event to the set
    created_listeners.add(event)


def scan_database():
    for bpmn in BPMN.objects.all():
        if bpmn.events:
            events = bpmn.events.split(
                ","
            )  # Assuming events are separated by semicolons
            for event in events:
                chaincode_name = bpmn.chaincode.name
                if not listener_exists(event + "-" + chaincode_name):
                    thread = threading.Thread(target=create_listener, args=(event,))
                    thread.start()
                    thread.join()  # Consider managing thread joins outside the loop


class Command(BaseCommand):
    help = "Scans the database for updates"

    def handle(self, *args, **options):
        self.stdout.write("Scanning the database...")
        scan_database()
        self.stdout.write("Database scan complete.")
