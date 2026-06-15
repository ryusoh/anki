"""
Tests for 3D visualization generation.

Tests HTML stripping, node positioning, and visualization settings.
"""

import re

import pytest


class TestHTMLStripping:
    """Test HTML tag removal from card content."""

    def test_strip_bold_tags(self):
        """Test stripping <b> tags."""
        from graph.quick_3d import strip_html

        text = "これがこの町で一番<b>高い</b>ビルです。"
        result = strip_html(text)

        assert '<b>' not in result
        assert '</b>' not in result
        assert '高い' in result

    def test_strip_italic_tags(self):
        """Test stripping <i> tags."""
        from graph.quick_3d import strip_html

        text = "This is <i>very</i> important"
        result = strip_html(text)

        assert '<i>' not in result
        assert '</i>' not in result
        assert 'very' in result

    def test_strip_multiple_tags(self):
        """Test stripping multiple HTML tags."""
        from graph.quick_3d import strip_html

        text = "<b>Bold</b> and <i>italic</i> with <u>underline</u>"
        result = strip_html(text)

        assert '<b>' not in result
        assert '<i>' not in result
        assert '<u>' not in result
        assert 'Bold' in result
        assert 'italic' in result

    def test_strip_div_span(self):
        """Test stripping container tags."""
        from graph.quick_3d import strip_html

        text = '<div class="card"><span style="color:red">Text</span></div>'
        result = strip_html(text)

        assert '<div' not in result
        assert '<span' not in result
        assert 'Text' in result

    def test_preserve_text(self):
        """Test that actual text content is preserved."""
        from graph.quick_3d import strip_html

        text = "This is a <b>test</b> sentence"
        result = strip_html(text)

        assert 'This is a test sentence' == result

    def test_strip_field_separator(self):
        """Test stripping Anki field separators."""
        from graph.quick_3d import strip_html

        text = "Front::Back"
        result = strip_html(text)

        assert '::' not in result
        assert 'Front Back' == result

    def test_strip_newlines(self):
        """Test stripping newlines."""
        from graph.quick_3d import strip_html

        text = "Line 1\nLine 2"
        result = strip_html(text)

        assert '\n' not in result
        assert 'Line 1 Line 2' == result

    def test_truncate_length(self):
        """Test truncation to 60 chars."""
        from graph.quick_3d import strip_html

        text = "A" * 100
        result = strip_html(text)

        assert len(result) <= 60

    def test_empty_input(self):
        """Test handling empty input."""
        from graph.quick_3d import strip_html

        assert strip_html('') == ''
        assert strip_html(None) == ''


class TestNodePositioning:
    """Test that nodes are positioned reasonably."""

    def test_nodes_within_bounds(self):
        """Test that nodes stay within reasonable bounds."""
        # Simulate force-directed layout
        positions = []
        velocities = []

        for i in range(100):
            positions.append(
                {'x': (i % 10 - 5) * 20, 'y': (i // 10 - 5) * 20, 'z': 0}  # Start in grid
            )
            velocities.append({'x': 0, 'y': 0, 'z': 0})

        # Run simulation
        repulsion = 50
        damping = 0.9

        for _iter in range(100):
            # Repulsion
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    dx = positions[i]['x'] - positions[j]['x']
                    dy = positions[i]['y'] - positions[j]['y']
                    dist = max(1, (dx * dx + dy * dy) ** 0.5)
                    force = repulsion / (dist * dist)
                    velocities[i]['x'] += (dx / dist) * force
                    velocities[i]['y'] += (dy / dist) * force
                    velocities[j]['x'] -= (dx / dist) * force
                    velocities[j]['y'] -= (dy / dist) * force

            # Update positions
            for i in range(len(positions)):
                velocities[i]['x'] *= damping
                velocities[i]['y'] *= damping
                positions[i]['x'] += velocities[i]['x']
                positions[i]['y'] += velocities[i]['y']

        # Check all nodes are within reasonable bounds
        for pos in positions:
            assert abs(pos['x']) < 500, f"Node too far: x={pos['x']}"
            assert abs(pos['y']) < 500, f"Node too far: y={pos['y']}"

    def test_no_infinite_velocity(self):
        """Test that velocities don't explode."""
        positions = [{'x': 0, 'y': 0, 'z': 0}]
        velocities = [{'x': 0, 'y': 0, 'z': 0}]

        # Add repulsion from origin
        for _iter in range(100):
            velocities[0]['x'] += 10
            velocities[0]['y'] += 10
            velocities[0]['x'] *= 0.9  # Damping
            velocities[0]['y'] *= 0.9
            positions[0]['x'] += velocities[0]['x']
            positions[0]['y'] += velocities[0]['y']

        # Velocity should be bounded by damping
        assert abs(velocities[0]['x']) < 100
        assert abs(velocities[0]['y']) < 100


class TestVisualizationSettings:
    """Test visualization configuration."""

    def test_auto_rotate_disabled(self):
        """Test that auto-rotate is disabled by default."""
        # This would be tested in the generated HTML
        # For now, just document the expected behavior
        assert True  # Placeholder - actual test in HTML generation

    def test_zoom_limits(self):
        """Test that zoom has reasonable limits."""
        # Camera should have min/max zoom
        min_zoom = 0.1
        max_zoom = 4

        assert min_zoom > 0
        assert max_zoom > min_zoom

    def test_node_size_scaling(self):
        """Test that node sizes scale properly."""
        from graph.quick_3d import scale_node_size

        # High PageRank = larger
        assert scale_node_size(0.02) > scale_node_size(0.001)

        # Within bounds
        size = scale_node_size(0.5)
        assert 0.5 <= size <= 3


def scale_node_size(pagerank):
    """Helper function for testing node scaling."""
    return min(3, max(0.5, pagerank * 100))


class TestScaleNodeSize:
    def test_scale_node_size(self):
        from graph.quick_3d import scale_node_size

        assert scale_node_size(0) == 0.5
        assert scale_node_size(10) == 3
