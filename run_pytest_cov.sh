#!/bin/bash
PYTHONPATH=. pytest --cov=graph --cov-report=term-missing graph/tests/
