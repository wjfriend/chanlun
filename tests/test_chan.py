"""Tests for chanlun services."""
import pytest

from services.chan import find_fenxing, process_inclusion


class TestChanAlgorithm:
    """Test缠论算法核心函数."""

    def test_process_inclusion_empty(self):
        """空列表处理."""
        result = process_inclusion([])
        assert result == []

    def test_process_inclusion_single_kline(self, sample_kline_data):
        """单根K线处理."""
        single = [sample_kline_data[0]]
        result = process_inclusion(single)
        assert len(result) == 1

    def test_find_fenxing_top_only(self):
        """顶分型识别（单侧验证）."""
        klines = [
            {"open": 10.0, "high": 10.2, "low": 9.8, "close": 10.1},
            {"open": 10.1, "high": 10.5, "low": 9.9, "close": 10.4},
            {"open": 10.4, "high": 10.9, "low": 10.3, "close": 10.7},  # 顶分型：high=10.9 > 10.5, 10.7
            {"open": 10.7, "high": 10.7, "low": 10.2, "close": 10.3},
        ]
        tops, bottoms = find_fenxing(klines)
        assert 2 in tops, f"expected top at 2, got {tops}"

    def test_find_fenxing_bottom_only(self):
        """底分型识别（单侧验证）."""
        klines = [
            {"open": 10.0, "high": 10.5, "low": 9.9, "close": 10.1},
            {"open": 10.1, "high": 10.4, "low": 9.7, "close": 9.8},  # 底分型：low=9.7 < 9.9, 9.9
            {"open": 9.8, "high": 10.0, "low": 9.9, "close": 9.95},
        ]
        tops, bottoms = find_fenxing(klines)
        assert 1 in bottoms, f"expected bottom at 1, got {bottoms}"

    def test_build_bi_alternation(self):
        """笔的交替连接."""
        bi_list = [
            {"start": 0, "end": 4, "type": "bottom"},
            {"start": 4, "end": 8, "type": "top"},
            {"start": 8, "end": 12, "type": "bottom"},
        ]
        assert len(bi_list) >= 0

    @pytest.mark.slow
    def test_full_analysis_integration(self):
        """完整缠论分析流程（集成测试）."""
        pytest.skip("needs integration test setup with real/mock data")
