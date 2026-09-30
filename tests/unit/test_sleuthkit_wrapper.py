"""
Unit tests for SleuthKitWrapper.
"""

from forensics_platform.external.sleuthkit_wrapper import SleuthKitWrapper


def test_sleuthkit_wrapper_availability():
    """Test checking TSK tools availability."""
    wrapper = SleuthKitWrapper()
    status = wrapper.check_availability()
    assert isinstance(status, dict)
    assert "fls" in status
    assert "mmls" in status
    assert "icat" in status


def test_parse_mmls_output():
    """Test parsing mmls text output."""
    wrapper = SleuthKitWrapper()
    sample_mmls = """
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000001   0000002047   0000002047   Unallocated
002:  000:000   0000002048   0000206847   0000204800   NTFS / exFAT (0x07)
003:  000:001   0000206848   0000411647   0000204800   Linux (0x83)
"""
    partitions = wrapper._parse_mmls_output(sample_mmls, "dummy.dd")
    assert len(partitions) == 4

    ntfs_part = partitions[2]
    assert ntfs_part["slot"] == "000:000"
    assert ntfs_part["start_sector"] == 2048
    assert ntfs_part["length_sectors"] == 204800
    assert ntfs_part["offset_bytes"] == 2048 * 512
    assert ntfs_part["is_allocated"] is True

    unalloc_part = partitions[1]
    assert unalloc_part["is_allocated"] is False


def test_parse_fls_output():
    """Test parsing fls directory and deleted file listing output."""
    wrapper = SleuthKitWrapper()
    sample_fls = """
d/d 144: SomeDocuments
r/r 145: report.pdf
r/r * 146(realloc): secret_deleted.txt
r/r * 147: evidence_photo.jpg
v/v 148: $Volume
"""
    files = wrapper._parse_fls_output(sample_fls)
    assert len(files) == 5

    # Directory
    assert files[0]["name"] == "SomeDocuments"
    assert files[0]["is_directory"] is True
    assert files[0]["is_deleted"] is False

    # Allocated file
    assert files[1]["name"] == "report.pdf"
    assert files[1]["is_deleted"] is False
    assert files[1]["type"] == "file"

    # Deleted file 1
    assert files[2]["name"] == "secret_deleted.txt"
    assert files[2]["is_deleted"] is True
    assert files[2]["inode"] == "146(realloc)"

    # Deleted file 2
    assert files[3]["name"] == "evidence_photo.jpg"
    assert files[3]["is_deleted"] is True


def test_parse_fls_output_recursive_and_uppercase():
    """Test parsing fls output with recursion depth markers, tabs, and uppercase mode tags."""
    wrapper = SleuthKitWrapper()
    sample_fls = """
d/d 10: /root
+ r/r 11: /root/child.txt
++ r/r * 12(realloc):\t/root/sub/deleted_nested.pdf
V/V 8193:\t$OrphanFiles
r/r * 145-128-3:\t$DATA_stream
"""
    files = wrapper._parse_fls_output(sample_fls)
    assert len(files) == 5

    # Directory
    assert files[0]["name"] == "/root"
    assert files[0]["is_directory"] is True

    # Recursive level 1
    assert files[1]["name"] == "/root/child.txt"
    assert files[1]["is_deleted"] is False
    assert files[1]["type"] == "file"

    # Recursive level 2 deleted
    assert files[2]["name"] == "/root/sub/deleted_nested.pdf"
    assert files[2]["is_deleted"] is True
    assert files[2]["inode"] == "12(realloc)"

    # Virtual volume entry
    assert files[3]["name"] == "$OrphanFiles"
    assert files[3]["inode"] == "8193"

    # NTFS compound stream inode
    assert files[4]["name"] == "$DATA_stream"
    assert files[4]["inode"] == "145-128-3"
    assert files[4]["is_deleted"] is True


def test_list_files_error_propagation():
    """Test that list_files raises ExternalToolError on invalid image."""
    import pytest
    from forensics_platform.core.exceptions import ExternalToolError

    wrapper = SleuthKitWrapper()
    if not wrapper.is_tool_available("fls"):
        pytest.skip("fls not installed")

    # Running fls on /dev/null should raise ExternalToolError (cannot determine filesystem)
    with pytest.raises(ExternalToolError):
        wrapper.list_files("/dev/null", offset_sectors=0)

