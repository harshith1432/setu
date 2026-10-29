import json
import os
import pytest
from app.services.firestore_service import FirestoreService

def test_firestore_service_initialization():
    """Verify FirestoreService singleton initializes safely without crashing when ADC is absent."""
    service = FirestoreService()
    assert service is not None
    assert isinstance(service.is_available, bool)

def test_firestore_rules_file_exists_and_valid():
    """Ensure firestore.rules exists and contains core collection definitions."""
    rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "firestore.rules")
    assert os.path.exists(rules_path), "firestore.rules must exist at repository root"
    
    with open(rules_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "rules_version = '2';" in content
    assert "match /databases/{database}/documents" in content
    assert "match /shed_telemetry/{telemetryId}" in content
    assert "match /products/{productId}" in content
    assert "match /orders/{orderId}" in content
    assert "match /audit_logs/{logId}" in content

def test_firestore_indexes_file_valid_json():
    """Ensure firestore.indexes.json is valid JSON with target indexes defined."""
    indexes_path = os.path.join(os.path.dirname(__file__), "..", "..", "firestore.indexes.json")
    assert os.path.exists(indexes_path), "firestore.indexes.json must exist at repository root"
    
    with open(indexes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert "indexes" in data
    collections = [idx.get("collectionGroup") for idx in data["indexes"]]
    assert "shed_telemetry" in collections
    assert "orders" in collections

def test_migration_report_and_schema_docs():
    """Verify documentation artifacts exist and are properly populated."""
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    schema_doc = os.path.join(root, "docs", "firebase_schema.md")
    report_doc = os.path.join(root, "docs", "firestore_migration_report.md")
    rollback_doc = os.path.join(root, "docs", "rollback_procedure.md")
    deployment_doc = os.path.join(root, "docs", "firebase_deployment_guide.md")
    
    for path in [schema_doc, report_doc, rollback_doc, deployment_doc]:
        assert os.path.exists(path), f"Missing document: {path}"
        assert os.path.getsize(path) > 500, f"Document is unexpectedly small: {path}"
