# local imports
# 3rd-party imports
import pytest
from unittest.mock import patch

from quicknxs.interfaces.data_handling.filepath import FilePath, RunNumbers, _find_file_in_ipts


def assert_equal_arrays(actual, expected):
    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


class TestRunNumber(object):
    """Test RunNumbers class."""

    def test_init(self):
        assert_equal_arrays(RunNumbers(123).numbers, [123])
        assert_equal_arrays(RunNumbers("123").numbers, [123])
        assert_equal_arrays(RunNumbers(["123", 126, "125"]).numbers, [123, 125, 126])
        assert_equal_arrays(RunNumbers("7:10+3:5+1").numbers, [1, 3, 4, 5, 7, 8, 9, 10])
        assert_equal_arrays(RunNumbers("7:10 + 3:5 + 1").numbers, [1, 3, 4, 5, 7, 8, 9, 10])

    def test_long(self):
        runs = RunNumbers([7, 8, 9, 10, 3, 4, 5, 1])
        assert runs.long == "1+3+4+5+7+8+9+10"

    def test_short(self):
        runs = RunNumbers([7, 8, 9, 10, 3, 4, 5, 1])
        assert runs.short == "1+3:5+7:10"

    def test_statement(self):
        assert RunNumbers([7]).statement == "7"
        assert RunNumbers([7, 8]).statement == "7 and 8"
        assert RunNumbers([7, 8, 9]).statement == "7, 8, and 9"


class TestFilePath(object):
    """Test FilePath class."""

    def test_init(self):
        assert FilePath("/SNS/REF_M_1.nxs").path == "/SNS/REF_M_1.nxs"
        assert FilePath(["/SNS/REF_M_2.nxs", "/SNS/REF_M_1.nxs"]).path == "/SNS/REF_M_1.nxs+/SNS/REF_M_2.nxs"
        assert (
            FilePath(["/SNS/REF_M_2.nxs", "/SNS/REF_M_1.nxs"], sort=False).path == "/SNS/REF_M_2.nxs+/SNS/REF_M_1.nxs"
        )
        assert FilePath("/SNS/REF_M_2.nxs+/SNS/REF_M_1.nxs").path == "/SNS/REF_M_1.nxs+/SNS/REF_M_2.nxs"

    def test_join(self):
        assert FilePath.join("/SNS", "REF_M_1.nxs") == "/SNS/REF_M_1.nxs"
        assert FilePath.join("/SNS", "REF_M_2.nxs+REF_M_1.nxs") == "/SNS/REF_M_1.nxs+/SNS/REF_M_2.nxs"

    def test_unique_dirname(self):
        assert FilePath.unique_dirname("/SNS/REF_M_1.nxs+/SNS/REF_M_2.nxs")
        assert FilePath.unique_dirname("/NSN/REF_M_1.nxs+/SNS/REF_M_2.nxs") is False

    def test_single_paths(self):
        assert_equal_arrays(
            FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").single_paths, ["/SNS/REF_M_1.nxs", "/SNS/REF_M_3.nxs"]
        )

    def test_is_composite(self):
        assert FilePath("/SNS/REF_M_3.nxs").is_composite is False
        assert FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").is_composite

    def test_dirname(self):
        assert FilePath("/SNS/REF_M_3.nxs").dirname == "/SNS"
        assert FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").dirname == "/SNS"

    def test_basename(self):
        assert FilePath("/SNS/REF_M_3.nxs").basename == "REF_M_3.nxs"
        assert FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").basename == "REF_M_1.nxs+REF_M_3.nxs"

    def test_first_path(self):
        assert FilePath("/SNS/REF_M_3.nxs").first_path == "/SNS/REF_M_3.nxs"
        assert FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").first_path == "/SNS/REF_M_1.nxs"

    def test_split(self):
        assert_equal_arrays(FilePath("/SNS/REF_M_3.nxs").split(), ("/SNS", "REF_M_3.nxs"))
        assert_equal_arrays(FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").split(), ("/SNS", "REF_M_1.nxs+REF_M_3.nxs"))

    def test_run_numbers(self):
        assert_equal_arrays(FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs").run_numbers(), [1, 3])
        file_path = FilePath("/SNS/REF_M_3.nxs+/SNS/REF_M_1.nxs+/SNS/REF_M_6.nxs+/SNS/REF_M_2.nxs")
        assert file_path.run_numbers(string_representation="long") == "1+2+3+6"
        assert file_path.run_numbers(string_representation="short") == "1:3+6"


class TestFindFileInIPTS:
    """Tests for the _find_file_in_ipts() module-level function."""

    BASE = "/SNS/REF_M"
    CANDIDATES = [("nexus", "REF_M_40205.nxs.h5"), ("data", "REF_M_40205_event.nxs")]

    def test_file_found(self):
        """Returns the correct absolute path when isfile returns True for a candidate."""
        expected = "/SNS/REF_M/IPTS-1/nexus/REF_M_40205.nxs.h5"

        def fake_isfile(path):
            return path == expected

        with patch("quicknxs.interfaces.data_handling.filepath.os.listdir", return_value=["IPTS-1", "IPTS-2"]), patch(
            "quicknxs.interfaces.data_handling.filepath.os.path.isfile", side_effect=fake_isfile
        ):
            result = _find_file_in_ipts(self.BASE, self.CANDIDATES)

        assert result == expected

    def test_file_not_found(self):
        """Returns None when no candidate exists in any IPTS directory."""
        with patch("quicknxs.interfaces.data_handling.filepath.os.listdir", return_value=["IPTS-1"]), patch(
            "quicknxs.interfaces.data_handling.filepath.os.path.isfile", return_value=False
        ):
            result = _find_file_in_ipts(self.BASE, [("nexus", "REF_M_99999.nxs.h5")])
        assert result is None

    def test_prefers_first_candidate(self):
        """When both candidates exist in the same IPTS dir, the first candidate wins."""
        with patch("quicknxs.interfaces.data_handling.filepath.os.listdir", return_value=["IPTS-1"]), patch(
            "quicknxs.interfaces.data_handling.filepath.os.path.isfile", return_value=True
        ):
            result = _find_file_in_ipts(self.BASE, self.CANDIDATES)
        assert result == "/SNS/REF_M/IPTS-1/nexus/REF_M_40205.nxs.h5"

    def test_instrument_dir_not_accessible(self):
        """Returns None when os.listdir raises OSError (e.g. mount not available)."""
        with patch("quicknxs.interfaces.data_handling.filepath.os.listdir", side_effect=OSError):
            result = _find_file_in_ipts(self.BASE, self.CANDIDATES)
        assert result is None

    def test_no_ipts_dirs(self):
        """Returns None when no directory names start with 'IPTS'."""
        with patch(
            "quicknxs.interfaces.data_handling.filepath.os.listdir", return_value=["archive", "shared", "logs"]
        ), patch("quicknxs.interfaces.data_handling.filepath.os.path.isfile", return_value=True):
            result = _find_file_in_ipts(self.BASE, self.CANDIDATES)
        assert result is None

    def test_isfile_oserror_falls_through_to_next_ipts(self):
        """Returns a valid path even when isfile raises OSError for some directories."""
        expected = "/SNS/REF_M/IPTS-3/nexus/REF_M_40205.nxs.h5"

        def fake_isfile(path):
            if "IPTS-1" in path or "IPTS-2" in path:
                raise OSError("Permission denied")
            return path == expected

        with patch(
            "quicknxs.interfaces.data_handling.filepath.os.listdir",
            return_value=["IPTS-1", "IPTS-2", "IPTS-3"],
        ), patch("quicknxs.interfaces.data_handling.filepath.os.path.isfile", side_effect=fake_isfile):
            result = _find_file_in_ipts(self.BASE, [("nexus", "REF_M_40205.nxs.h5")])
        assert result == expected

    def test_second_candidate_fallback(self):
        """Returns second candidate path when first candidate doesn't exist but second does."""
        expected = "/SNS/REF_M/IPTS-1/data/REF_M_40205_event.nxs"

        def fake_isfile(path):
            return path == expected

        with patch("quicknxs.interfaces.data_handling.filepath.os.listdir", return_value=["IPTS-1"]), patch(
            "quicknxs.interfaces.data_handling.filepath.os.path.isfile", side_effect=fake_isfile
        ):
            result = _find_file_in_ipts(self.BASE, self.CANDIDATES)
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])
