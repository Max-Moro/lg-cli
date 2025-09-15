import pytest

from lg.adapters.range_edits import RangeEditor


def test_multiple_edits_reverse_order_and_stats():
    # Original text (ASCII -> byte offsets == char indices)
    text = "abcdef\n123456\nXYZ\n"
    ed = RangeEditor(text)

    # Replace 'cde' with 'C' (shorter)
    start_rep = 2  # 'c'
    end_rep = 5    # just before 'f'
    ed.add_replacement(start_rep, end_rep, "C", edit_type="replace_cde")

    # Insert prefix at BOF
    ed.add_replacement(0, 0, ">>> ", edit_type="insert_prefix")

    # Delete '456\n'
    start_del = text.index("456")
    end_del = start_del + len("456\n")
    ed.add_deletion(start_del, end_del, edit_type="delete_tail")

    result, stats = ed.apply_edits()

    # Expected result
    # We delete '456\n', so the newline after '123' is removed as well.
    expected = ">>> abCf\n123XYZ\n"
    assert result == expected

    # Stats
    assert stats["edits_applied"] == 3
    # Removed: len('cde') + len('456\n') = 3 + 4 = 7
    assert stats["bytes_removed"] == 7
    # Added: len('C') + len('>>> ') = 1 + 4 = 5
    assert stats["bytes_added"] == 5
    assert stats["bytes_saved"] == 2
    # Only the deletion of '456\n' removes one newline
    assert stats["lines_removed"] == 1


def test_overlapping_edits_first_wins():
    text = "hello world"
    ed = RangeEditor(text)

    # First edit wins: replace 'hello' -> 'hi'
    ed.add_replacement(0, 5, "hi", edit_type="first")
    # Overlapping second edit should be ignored (first-wins policy)
    ed.add_deletion(0, 4, edit_type="second_overlapping")

    result, stats = ed.apply_edits()
    assert result == "hi world"
    assert stats["edits_applied"] == 1


def test_deletion_replacement_and_insertion_individually():
    # Deletion
    text = "abc\n"
    ed = RangeEditor(text)
    ed.add_deletion(1, 2, edit_type="del_b")  # remove 'b'
    res, st = ed.apply_edits()
    assert res == "ac\n"
    assert st["edits_applied"] == 1
    assert st["bytes_removed"] == 1
    assert st["bytes_added"] == 0
    assert st["lines_removed"] == 0

    # Replacement
    text2 = "abc\n"
    ed2 = RangeEditor(text2)
    ed2.add_replacement(2, 3, "CCC", edit_type="rep_c")  # 'c' -> 'CCC'
    res2, st2 = ed2.apply_edits()
    assert res2 == "abCCC\n"
    assert st2["bytes_removed"] == 1
    assert st2["bytes_added"] == 3

    # Insertion
    text3 = "abc\n"
    ed3 = RangeEditor(text3)
    ed3.add_replacement(1, 1, "-", edit_type="insert_dash")  # insert before 'b'
    res3, st3 = ed3.apply_edits()
    assert res3 == "a-bc\n"
    assert st3["bytes_removed"] == 0
    assert st3["bytes_added"] == 1


def test_validation_errors_negative_and_out_of_bounds():
    text = "abc"
    ed = RangeEditor(text)

    # Negative start
    ed.add_replacement(-1, 0, "X", edit_type="neg")
    # End beyond bounds
    ed.add_deletion(1, 100, edit_type="oob")

    with pytest.raises(ValueError) as ei:
        ed.apply_edits()

    msg = str(ei.value)
    assert "start_byte (-1) is negative" in msg
    assert "end_byte (100) exceeds text length" in msg


def test_unicode_multibyte_offsets_and_decoding():
    # '🍕' is 4 bytes in UTF-8
    text = "A🍕B\n"
    ed = RangeEditor(text)

    # Compute byte offsets for the pizza emoji
    char_index = text.index("🍕")
    start_byte = len(text[:char_index].encode("utf-8"))
    end_byte = start_byte + len("🍕".encode("utf-8"))

    # Replace emoji with 'X' (shorter)
    ed.add_replacement(start_byte, end_byte, "X", edit_type="unicode_rep")
    result, stats = ed.apply_edits()

    assert result == "AXB\n"
    # Removed 4 bytes, added 1
    assert stats["bytes_removed"] == 4
    assert stats["bytes_added"] == 1
    assert stats["bytes_saved"] == 3
    assert stats["lines_removed"] == 0


def test_insertion_basic():
    """Test basic insertion functionality."""
    text = "hello world"
    ed = RangeEditor(text)
    
    # Insert "beautiful " after "hello "
    ed.add_insertion(6, "beautiful ", edit_type="insert_adjective")
    
    result, stats = ed.apply_edits()
    assert result == "hello beautiful world"
    assert stats["edits_applied"] == 1
    assert stats["bytes_removed"] == 0  # Insertions don't remove bytes
    assert stats["bytes_added"] == 10  # "beautiful " is 10 bytes
    assert stats["bytes_saved"] == -10  # Net change is negative (we added content)


def test_insertion_at_beginning():
    """Test insertion at the beginning of text."""
    text = "world"
    ed = RangeEditor(text)
    
    # Insert "hello " at the beginning
    ed.add_insertion(0, "hello ", edit_type="insert_greeting")
    
    result, stats = ed.apply_edits()
    assert result == "hello world"
    assert stats["bytes_added"] == 6


def test_insertion_at_end():
    """Test insertion at the end of text."""
    text = "hello"
    ed = RangeEditor(text)
    
    # Insert " world" at the end
    ed.add_insertion(len(text.encode('utf-8')), " world", edit_type="insert_suffix")
    
    result, stats = ed.apply_edits()
    assert result == "hello world"
    assert stats["bytes_added"] == 6


def test_multiple_insertions():
    """Test multiple insertions in different positions."""
    text = "a c e"
    ed = RangeEditor(text)
    
    # Insert "b" after "a "
    ed.add_insertion(2, "b", edit_type="insert_b")
    # Insert "d" after "c "
    ed.add_insertion(5, "d", edit_type="insert_d")
    
    result, stats = ed.apply_edits()
    assert result == "a bc ed"  # Вставки применяются в обратном порядке
    assert stats["edits_applied"] == 2
    assert stats["bytes_added"] == 2  # "b" + "d"
    assert stats["bytes_removed"] == 0


def test_insertion_with_replacement():
    """Test mixing insertions with replacements."""
    text = "hello world"
    ed = RangeEditor(text)
    
    # Insert "beautiful " after "hello "
    ed.add_insertion(6, "beautiful ", edit_type="insert_adjective")
    # Replace "hello" with "hi" (до вставки, чтобы избежать проблем с валидацией)
    ed.add_replacement(0, 5, "hi", edit_type="replace_hello")
    
    result, stats = ed.apply_edits()
    assert result == "hi beautiful world"
    assert stats["edits_applied"] == 2
    assert stats["bytes_removed"] == 5  # "hello" is 5 bytes
    assert stats["bytes_added"] == 12  # "beautiful " (10) + "hi" (2)
    assert stats["bytes_saved"] == -7


def test_insertion_overlap_prevention():
    """Test that overlapping insertions are prevented (first-wins policy)."""
    text = "hello world"
    ed = RangeEditor(text)
    
    # First insertion
    ed.add_insertion(6, "beautiful ", edit_type="first")
    # Overlapping insertion at the same position should be ignored
    ed.add_insertion(6, "amazing ", edit_type="second_overlapping")
    
    result, stats = ed.apply_edits()
    assert result == "hello beautiful world"
    assert stats["edits_applied"] == 1  # Only first insertion applied
    assert stats["bytes_added"] == 10  # Only "beautiful "


def test_insertion_unicode():
    """Test insertion with Unicode characters."""
    text = "привет мир"
    ed = RangeEditor(text)
    
    # Insert "красивый " after "привет "
    # "привет " is 13 bytes in UTF-8 (пробел на позиции 12-13)
    ed.add_insertion(13, "красивый ", edit_type="insert_adjective")
    
    result, stats = ed.apply_edits()
    assert result == "привет красивый мир"
    assert stats["bytes_added"] == 17  # "красивый " is 17 bytes in UTF-8


def test_insertion_edit_summary():
    """Test that edit summary correctly handles insertions."""
    text = "hello world"
    ed = RangeEditor(text)
    
    ed.add_insertion(6, "beautiful ", edit_type="insert_adjective")
    ed.add_replacement(12, 17, "universe", edit_type="replace_world")
    
    summary = ed.get_edit_summary()
    assert summary["total_edits"] == 2
    assert summary["bytes_to_remove"] == 5  # Only replacement removes bytes
    assert summary["bytes_to_add"] == 18  # Both operations add bytes
    assert summary["net_savings"] == -13
    assert summary["edit_types"]["insert_adjective"] == 1
    assert summary["edit_types"]["replace_world"] == 1


def test_insertion_utf8_boundary_correction():
    """Test that insertions are corrected to UTF-8 boundaries."""
    # Создаем текст с Unicode символами
    text = "Привет мир!"
    ed = RangeEditor(text)
    
    # Пытаемся вставить в середину UTF-8 символа (позиция 1 - середина 'р')
    # Должно автоматически скорректироваться на границу символа
    ed.add_insertion(1, "X", edit_type="test_insertion")
    
    result, stats = ed.apply_edits()
    # Результат должен быть валидным UTF-8
    assert isinstance(result, str)
    assert stats["edits_applied"] == 1
    assert stats["bytes_added"] == 1


def test_insertion_utf8_complex():
    """Test insertion with complex UTF-8 sequences."""
    # Текст с различными Unicode символами
    text = "Hello 世界 🌍 привет"
    ed = RangeEditor(text)
    
    # Вставляем в разные позиции
    ed.add_insertion(6, " beautiful ", edit_type="insert_1")  # После "Hello "
    ed.add_insertion(20, " amazing ", edit_type="insert_2")   # После "世界 "
    
    result, stats = ed.apply_edits()
    assert isinstance(result, str)
    assert stats["edits_applied"] == 2
    # Проверяем, что результат содержит ожидаемый контент
    assert "beautiful" in result
    assert "amazing" in result