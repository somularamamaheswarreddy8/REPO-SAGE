import pytest
from app.services.parser.filters import should_index_file
from app.services.parser.ast_visitor import parse_python_ast, parse_js_ts_symbols
from app.services.parser.chunker import chunk_file, detect_language, line_based_fallback_chunks


def test_should_index_file_filter():
    # Valid source files
    valid, _ = should_index_file("services/payment.py", 1024)
    assert valid is True

    valid, _ = should_index_file("frontend/src/App.tsx", 2048)
    assert valid is True

    # Excluded directories
    valid, reason = should_index_file(".git/config", 100)
    assert valid is False
    assert "excluded directory" in reason.lower()

    valid, reason = should_index_file("node_modules/react/index.js", 500)
    assert valid is False
    assert "excluded directory" in reason.lower()

    # Sensitive files
    valid, reason = should_index_file(".env", 50)
    assert valid is False
    assert "sensitive" in reason.lower()

    valid, reason = should_index_file("config/.env.production", 200)
    assert valid is False
    assert "sensitive" in reason.lower()

    valid, reason = should_index_file("keys/id_rsa", 1024)
    assert valid is False
    assert "sensitive" in reason.lower()

    # Excluded binary extensions
    valid, reason = should_index_file("assets/logo.png", 5000)
    assert valid is False
    assert "excluded file extension" in reason.lower()

    # File size limit
    valid, reason = should_index_file("huge_data.json", 600 * 1024)
    assert valid is False
    assert "exceeds maximum allowed size" in reason.lower()


def test_parse_python_ast():
    sample_code = '''"""Module docstring."""
import os
from datetime import datetime
from services.payment import PaymentService

class OrderProcessor:
    """Class docstring."""
    def __init__(self, service: PaymentService):
        self.service = service

    def process(self, order_id: int) -> bool:
        """Process order."""
        result = self.service.create_charge()
        return True
'''
    res = parse_python_ast(sample_code, "api/orders.py")
    symbols = res["symbols"]
    relationships = res["relationships"]

    # Symbols check
    sym_names = [s.name for s in symbols]
    assert "OrderProcessor" in sym_names
    assert "OrderProcessor.__init__" in sym_names
    assert "OrderProcessor.process" in sym_names

    # Relationship check
    import_targets = [r.target_symbol for r in relationships if r.relationship_type == "imports"]
    assert "os" in import_targets
    assert "datetime.datetime" in import_targets
    assert "services.payment.PaymentService" in import_targets


def test_parse_js_ts_symbols():
    sample_js = '''
import React, { useState } from 'react';
import { fetchOrders } from '../services/api';

class OrderList extends React.Component {
    render() { return <div>Orders</div>; }
}

export const calculateDiscount = (total) => {
    return total * 0.1;
};
'''
    res = parse_js_ts_symbols(sample_js, "src/components/OrderList.tsx")
    symbols = res["symbols"]
    relationships = res["relationships"]

    sym_names = [s.name for s in symbols]
    assert "OrderList" in sym_names
    assert "calculateDiscount" in sym_names

    import_rels = [r.target_symbol for r in relationships if r.relationship_type == "imports"]
    assert "react" in import_rels
    assert "../services/api" in import_rels


def test_chunk_file_python_and_fallback():
    # Python file
    py_code = '''def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
'''
    chunks, _ = chunk_file(py_code, "math_utils.py")
    assert len(chunks) >= 2
    assert chunks[0].symbol_name in {"add", "subtract"}
    assert chunks[0].content_hash is not None

    # Line-based fallback on markdown/text
    md_code = "\n".join([f"Line {i}: Documentation content" for i in range(1, 120)])
    md_chunks, _ = chunk_file(md_code, "docs/README.md")
    assert len(md_chunks) > 1
    assert md_chunks[0].start_line == 1
    assert md_chunks[0].end_line > 1
