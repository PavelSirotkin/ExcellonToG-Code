"""
Тесты для валидатора путей (защита от Path Traversal).
"""
import os
import tempfile
import pytest
from core.path_validator import validate_save_path, get_safe_filename


class TestValidateSavePath:
    """Тесты функции validate_save_path."""
    
    def test_valid_path(self):
        """Проверка валидного пути."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.tap")
            is_valid, error_msg = validate_save_path(filepath)
            assert is_valid is True
            assert error_msg == ""
    
    def test_empty_path(self):
        """Проверка пустого пути."""
        is_valid, error_msg = validate_save_path("")
        assert is_valid is True
        assert error_msg == ""
    
    def test_none_path(self):
        """Проверка None пути."""
        is_valid, error_msg = validate_save_path(None)
        assert is_valid is True
        assert error_msg == ""
    
    def test_path_with_double_dots(self):
        """Проверка пути с .. (path traversal)."""
        filepath = "C:\\Users\\test\\..\\..\\system32\\file.tap"
        is_valid, error_msg = validate_save_path(filepath)
        assert is_valid is False
        assert "Suspicious pattern" in error_msg
        assert ".." in error_msg
    
    def test_path_with_tilde(self):
        """Проверка пути с ~ (домашняя директория)."""
        filepath = "~/documents/file.tap"
        is_valid, error_msg = validate_save_path(filepath)
        assert is_valid is False
        assert "Suspicious pattern" in error_msg
        assert "~" in error_msg
    
    def test_path_with_dollar_sign(self):
        """Проверка пути с $ (переменная окружения)."""
        filepath = "C:\\$TEMP\\file.tap"
        is_valid, error_msg = validate_save_path(filepath)
        assert is_valid is False
        assert "Suspicious pattern" in error_msg
        assert "$" in error_msg
    
    def test_path_with_percent(self):
        """Проверка пути с % (переменная окружения Windows)."""
        filepath = "C:\\%TEMP%\\file.tap"
        is_valid, error_msg = validate_save_path(filepath)
        assert is_valid is False
        assert "Suspicious pattern" in error_msg
        assert "%" in error_msg
    
    def test_path_with_allowed_base_dirs(self):
        """Проверка пути с разрешёнными директориями (родитель существует)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Раньше тест полагался на побочный эффект os.makedirs внутри
            # валидатора. Теперь валидатор — чистая функция, поэтому
            # subdir создаём явно перед проверкой.
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            filepath = os.path.join(subdir, "file.tap")
            allowed_dirs = [tmpdir]
            is_valid, error_msg = validate_save_path(filepath, allowed_dirs)
            assert is_valid is True
            assert error_msg == ""
    
    def test_path_outside_allowed_dirs(self):
        """Проверка пути вне разрешённых директорий."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                filepath = os.path.join(tmpdir2, "file.tap")
                allowed_dirs = [tmpdir1]
                is_valid, error_msg = validate_save_path(filepath, allowed_dirs)
                assert is_valid is False
                assert "outside allowed directories" in error_msg
    
    def test_validator_does_not_create_parent_dir(self):
        """H3: валидатор НЕ должен создавать директории как побочный эффект.

        Раньше validate_save_path вызывал os.makedirs для несуществующего
        родителя — это нарушало контракт «валидация = чистая функция»
        и могло засорить FS до того, как пользователь подтвердит сохранение.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent_parent = os.path.join(tmpdir, "newdir")
            filepath = os.path.join(nonexistent_parent, "file.tap")
            assert not os.path.exists(nonexistent_parent)  # sanity

            is_valid, error_msg = validate_save_path(filepath)

            # Новое поведение: путь невалиден, потому что родителя нет
            assert is_valid is False
            assert "does not exist" in error_msg
            # Главное: директория НЕ должна быть создана как побочный эффект
            assert not os.path.exists(nonexistent_parent)

    def test_nonexistent_parent_directory_rejected(self):
        """Несуществующая родительская директория → валидация не проходит."""
        if os.name == 'nt':
            filepath = "Z:\\nonexistent\\path\\file.tap"
        else:
            filepath = "/nonexistent_root/path/file.tap"

        is_valid, error_msg = validate_save_path(filepath)
        assert is_valid is False
        assert "does not exist" in error_msg or "not writable" in error_msg

    def test_existing_writable_parent_passes(self):
        """Существующий и доступный для записи родитель → валидация проходит."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subfile.tap")
            is_valid, error_msg = validate_save_path(filepath)
            assert is_valid is True
            assert error_msg == ""


class TestGetSafeFilename:
    """Тесты функции get_safe_filename."""
    
    def test_safe_filename(self):
        """Проверка безопасного имени файла."""
        filename = "test_file.tap"
        safe = get_safe_filename(filename)
        assert safe == filename
    
    def test_filename_with_double_dots(self):
        """Проверка имени файла с ..."""
        filename = "test..file.tap"
        safe = get_safe_filename(filename)
        assert ".." not in safe
        assert safe == "test__file.tap"
    
    def test_filename_with_tilde(self):
        """Проверка имени файла с ~."""
        filename = "~test_file.tap"
        safe = get_safe_filename(filename)
        assert "~" not in safe
        assert safe == "_test_file.tap"
    
    def test_filename_with_dollar(self):
        """Проверка имени файла с $."""
        filename = "test$file.tap"
        safe = get_safe_filename(filename)
        assert "$" not in safe
        assert safe == "test_file.tap"
    
    def test_filename_with_percent(self):
        """Проверка имени файла с %."""
        filename = "test%file.tap"
        safe = get_safe_filename(filename)
        assert "%" not in safe
        assert safe == "test_file.tap"
    
    def test_filename_with_pipe(self):
        """Проверка имени файла с |."""
        filename = "test|file.tap"
        safe = get_safe_filename(filename)
        assert "|" not in safe
        assert safe == "test_file.tap"
    
    def test_filename_with_ampersand(self):
        """Проверка имени файла с &."""
        filename = "test&file.tap"
        safe = get_safe_filename(filename)
        assert "&" not in safe
        assert safe == "test_file.tap"
    
    def test_filename_with_semicolon(self):
        """Проверка имени файла с ;."""
        filename = "test;file.tap"
        safe = get_safe_filename(filename)
        assert ";" not in safe
        assert safe == "test_file.tap"
    
    def test_filename_with_backtick(self):
        """Проверка имени файла с `."""
        filename = "test`file.tap"
        safe = get_safe_filename(filename)
        assert "`" not in safe
        assert safe == "test_file.tap"
    
    def test_empty_filename(self):
        """Проверка пустого имени файла."""
        filename = ""
        safe = get_safe_filename(filename)
        assert safe == ""
    
    def test_none_filename(self):
        """Проверка None имени файла."""
        filename = None
        safe = get_safe_filename(filename)
        assert safe is None
    
    def test_filename_with_multiple_dangerous_chars(self):
        """Проверка имени файла с несколькими опасными символами."""
        filename = "test..~$%|&;`file.tap"
        safe = get_safe_filename(filename)
        assert ".." not in safe
        assert "~" not in safe
        assert "$" not in safe
        assert "%" not in safe
        assert "|" not in safe
        assert "&" not in safe
        assert ";" not in safe
        assert "`" not in safe
        assert safe == "test_________file.tap"
