import os

class Build:
    release = "RELEASE" in os.environ
    release = True

    PRODUCT_NAME = "Marvel Champions Digital: Ronin Edition"
    RELEASE_CODENAME = "Echo"

    # Version
    MAJOR = 0
    MINOR = 6
    PATCH = 1
    BUILD = 0

    RELEASE_VERSION = f"{MAJOR}.{MINOR}.{PATCH}"
    RELEASE_LABEL = f'Version {RELEASE_VERSION} — “{RELEASE_CODENAME}”'
