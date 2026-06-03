def test_package_imports_and_exposes_version():
    import ocr_yolo_engine

    assert ocr_yolo_engine.__version__ == "0.1.0"
