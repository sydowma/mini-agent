"""Tests for tools."""

import pytest
import tempfile
import os
from pathlib import Path

from mini_agent.tools.truncate import truncate_head, truncate_tail
from mini_agent.tools.read import ReadTool
from mini_agent.tools.write import WriteTool
from mini_agent.tools.edit import EditTool
from mini_agent.tools.ls import ListTool


class TestTruncate:
    def test_truncate_tail_no_truncation(self):
        content = "short content"
        result = truncate_tail(content, max_lines=100, max_bytes=1000)
        assert not result.was_truncated
        assert result.content == content

    def test_truncate_tail_by_lines(self):
        lines = ["line " + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_tail(content, max_lines=10)
        assert result.was_truncated
        assert result.lines_removed == 90
        assert "line 0" in result.content
        assert "line 99" not in result.content

    def test_truncate_head_by_lines(self):
        lines = ["line " + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_head(content, max_lines=10)
        assert result.was_truncated
        assert result.lines_removed == 90
        assert "line 99" in result.content
        assert "line 0" not in result.content

    def test_truncate_empty_content(self):
        result = truncate_tail("", max_lines=10)
        assert result.content == ""
        assert not result.was_truncated

    def test_truncate_by_bytes(self):
        content = "x" * 1000
        result = truncate_tail(content, max_lines=1000, max_bytes=100)
        assert result.was_truncated
        assert len(result.content.encode('utf-8')) <= 150


class TestReadTool:
    @pytest.mark.asyncio
    async def test_read_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello\nWorld\n")
            f.flush()
            temp_path = f.name

        try:
            tool = ReadTool()
            result = await tool.execute({"file_path": temp_path})
            assert "Hello" in result
            assert "World" in result
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        tool = ReadTool()
        result = await tool.execute({"file_path": "/nonexistent/file.txt"})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_read_with_offset(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            f.flush()
            temp_path = f.name

        try:
            tool = ReadTool()
            result = await tool.execute({"file_path": temp_path, "offset": 2})
            assert "Line 2" in result
            # Line 1 should not appear (offset starts from line 2)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_requires_absolute_path(self):
        tool = ReadTool()
        result = await tool.execute({"file_path": "relative/path.txt"})
        assert "must be absolute" in result


class TestWriteTool:
    @pytest.mark.asyncio
    async def test_write_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            tool = WriteTool()
            result = await tool.execute({
                "file_path": file_path,
                "content": "Hello World"
            })

            assert "Created" in result
            assert os.path.exists(file_path)

            with open(file_path) as f:
                assert f.read() == "Hello World"

    @pytest.mark.asyncio
    async def test_write_creates_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "nested", "test.txt")

            tool = WriteTool()
            result = await tool.execute({
                "file_path": file_path,
                "content": "Nested content"
            })

            assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")

            # Create initial file
            with open(file_path, 'w') as f:
                f.write("Original")

            tool = WriteTool()
            result = await tool.execute({
                "file_path": file_path,
                "content": "New content"
            })

            assert "Updated" in result
            with open(file_path) as f:
                assert f.read() == "New content"

    @pytest.mark.asyncio
    async def test_write_requires_absolute_path(self):
        tool = WriteTool()
        result = await tool.execute({
            "file_path": "relative/path.txt",
            "content": "test"
        })
        assert "must be absolute" in result


class TestEditTool:
    @pytest.mark.asyncio
    async def test_edit_replace(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello World\nGoodbye World")
            f.flush()
            temp_path = f.name

        try:
            tool = EditTool()
            result = await tool.execute({
                "file_path": temp_path,
                "old_string": "World",
                "new_string": "Universe",
                "replace_all": True
            })

            assert "Replaced 2" in result

            with open(temp_path) as f:
                content = f.read()
            assert content == "Hello Universe\nGoodbye Universe"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_single_occurrence(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello World")
            f.flush()
            temp_path = f.name

        try:
            tool = EditTool()
            result = await tool.execute({
                "file_path": temp_path,
                "old_string": "World",
                "new_string": "Universe"
            })

            assert "Replaced 1" in result
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_multiple_without_replace_all(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello World\nHello World")
            f.flush()
            temp_path = f.name

        try:
            tool = EditTool()
            result = await tool.execute({
                "file_path": temp_path,
                "old_string": "World",
                "new_string": "Universe"
            })

            assert "appears 2 times" in result
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_not_found(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello World")
            f.flush()
            temp_path = f.name

        try:
            tool = EditTool()
            result = await tool.execute({
                "file_path": temp_path,
                "old_string": "NotExist",
                "new_string": "Something"
            })

            assert "not found" in result
        finally:
            os.unlink(temp_path)


class TestListTool:
    @pytest.mark.asyncio
    async def test_list_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "file1.txt").touch()
            Path(tmpdir, "file2.txt").touch()
            os.mkdir(Path(tmpdir, "subdir"))

            tool = ListTool()
            result = await tool.execute({"path": tmpdir})

            assert "file1.txt" in result
            assert "file2.txt" in result
            assert "subdir" in result

    @pytest.mark.asyncio
    async def test_list_requires_absolute_path(self):
        tool = ListTool()
        result = await tool.execute({"path": "relative/path"})
        assert "must be absolute" in result

    @pytest.mark.asyncio
    async def test_list_nonexistent(self):
        tool = ListTool()
        result = await tool.execute({"path": "/nonexistent/directory"})
        assert "not found" in result or "Error" in result
