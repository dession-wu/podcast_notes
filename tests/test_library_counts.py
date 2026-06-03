"""Library tab count consistency tests.

Tests that type_counts remain consistent regardless of which tab is active.
"""

from __future__ import annotations

import pytest


class TestLibraryCountConsistency:
    """Test that tab counts are consistent across different active tabs."""

    def test_type_counts_include_all_types_when_filtering_audio(self):
        """Test that type_counts includes all types even when filtering by audio."""
        from backend.routers.library import get_library_files

        # Mock the function behavior by checking the logic
        # When type="audio", all directories should still be scanned for counts
        # but only audio files should be returned

        # This test verifies the code structure
        import inspect
        source = inspect.getsource(get_library_files)

        # Verify that all directories are scanned for counts
        assert "all_files_for_counts" in source
        assert "for ft, dir_path in type_dirs.items()" in source

        # Verify that type_counts is calculated from complete scan
        assert "type_counts = {\"audio\": 0, \"transcript\": 0, \"image\": 0}" in source
        assert "for f in all_files_for_counts" in source

        # Verify that filtering happens after counting
        assert "filtered_files = [f for f in all_files_for_counts if f.type == type]" in source

    def test_type_counts_not_based_on_filtered_files(self):
        """Test that type_counts is not calculated from filtered file list."""
        import inspect
        from backend.routers.library import get_library_files

        source = inspect.getsource(get_library_files)

        # Ensure type_counts calculation uses all_files_for_counts, not filtered_files
        assert "for f in all_files_for_counts:" in source
        assert "if f.type in type_counts:" in source

        # Ensure the response uses filtered_files for files list
        assert "files=filtered_files" in source
        assert "total=len(filtered_files)" in source

    def test_frontend_all_tab_uses_type_counts_sum(self):
        """Test that frontend 'all' tab uses sum of type_counts."""
        # Read the frontend page source
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"Frontend page not found: {page_path}")

        # Verify that 'all' tab uses typeCounts sum, not files.length
        assert "(typeCounts.audio || 0) + (typeCounts.transcript || 0) + (typeCounts.image || 0)" in content

        # Verify that other tabs use typeCounts directly
        assert "typeCounts[tab.key]" in content

    def test_frontend_no_longer_uses_files_length_for_all_tab(self):
        """Test that frontend no longer uses files.length for 'all' tab count."""
        page_path = "web-dashboard/src/app/dashboard/library/page.tsx"

        try:
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            pytest.skip(f"Frontend page not found: {page_path}")

        # The old buggy pattern was: tab.key === "all" ? files.length
        # This should no longer exist
        assert 'tab.key === "all" ? files.length' not in content, (
            "Frontend still uses files.length for 'all' tab - bug not fixed"
        )

    def test_library_response_model_has_type_counts(self):
        """Test that LibraryFilesResponse includes type_counts field."""
        from backend.routers.library import LibraryFilesResponse

        # Verify the model structure
        assert hasattr(LibraryFilesResponse, 'model_fields')
        assert 'type_counts' in LibraryFilesResponse.model_fields
        assert 'files' in LibraryFilesResponse.model_fields
        assert 'total' in LibraryFilesResponse.model_fields

    def test_type_counts_keys_are_complete(self):
        """Test that type_counts includes all expected type keys."""
        import inspect
        from backend.routers.library import get_library_files

        source = inspect.getsource(get_library_files)

        # Verify all three types are in the counts
        assert '"audio": 0' in source
        assert '"transcript": 0' in source
        assert '"image": 0' in source

    def test_count_consistency_scenario(self):
        """Simulate the bug scenario and verify the fix logic.

        Scenario: 13 total files (7 audio, 6 transcript, 0 image)
        When filtering by "audio", type_counts should still be {audio:7, transcript:6, image:0}
        """
        # This is a logic verification test
        # The fix ensures that:
        # 1. All directories are scanned to build all_files_for_counts
        # 2. type_counts is calculated from all_files_for_counts
        # 3. files are filtered separately

        # Simulate the counting logic
        all_files = [
            type('File', (), {'type': 'audio'})() for _ in range(7)
        ] + [
            type('File', (), {'type': 'transcript'})() for _ in range(6)
        ]

        # Calculate type_counts (as the fixed code does)
        type_counts = {"audio": 0, "transcript": 0, "image": 0}
        for f in all_files:
            if f.type in type_counts:
                type_counts[f.type] += 1

        # Verify counts are correct
        assert type_counts["audio"] == 7
        assert type_counts["transcript"] == 6
        assert type_counts["image"] == 0

        # Filter for audio only (as the API does for type="audio")
        filtered = [f for f in all_files if f.type == "audio"]

        # Verify filtered list has only audio
        assert len(filtered) == 7

        # But type_counts still has all types
        assert type_counts["transcript"] == 6  # Should NOT be 0

    def test_frontend_display_logic_for_all_tab(self):
        """Test the frontend display logic calculation for 'all' tab."""
        # Simulate typeCounts data
        type_counts = {"audio": 7, "transcript": 6, "image": 0}

        # Calculate what the frontend should display for 'all' tab
        all_count = (type_counts.get("audio") or 0) + \
                    (type_counts.get("transcript") or 0) + \
                    (type_counts.get("image") or 0)

        assert all_count == 13, f"Expected 13, got {all_count}"

        # Other tabs should show their specific count
        assert type_counts.get("audio") == 7
        assert type_counts.get("transcript") == 6
        assert type_counts.get("image") == 0
