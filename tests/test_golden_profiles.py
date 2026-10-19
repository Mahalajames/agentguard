import subprocess
import sys
from pathlib import Path


def test_all_golden_profiles_pass():
    """Run the standalone validator for all 30 golden profiles."""
    script = Path(__file__).with_name("check_golden_profiles.py")

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All golden profiles passed." in result.stdout
