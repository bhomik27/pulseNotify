import os
import sys
from dotenv import load_dotenv


def main():
    load_dotenv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsenotify.settings.local')
    # ...rest of the file unchanged