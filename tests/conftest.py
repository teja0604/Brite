"""Use a workspace-local temporary fixture because the host temp root is ACL-blocked."""
from pathlib import Path
import shutil
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path():
    path = Path("outputs") / ".pytest_tmp" / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield path
    shutil.rmtree(path, ignore_errors=True)
