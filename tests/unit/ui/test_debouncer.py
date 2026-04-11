import time
import pytest
from src.platforms.common.ui.ui_utils import Debouncer

def test_debouncer_execution():
    """Verify that the action is executed after the delay."""
    results = []
    def action(val):
        results.append(val)
        
    debouncer = Debouncer(delay=0.1)
    debouncer.run(action, "hit")
    
    # Immediately after run, it should not be executed
    assert len(results) == 0
    
    # Wait for more than delay
    time.sleep(0.15)
    assert len(results) == 1
    assert results[0] == "hit"

def test_debouncer_reset():
    """Verify that multiple calls reset the timer and only the last one runs."""
    results = []
    def action(val):
        results.append(val)
        
    debouncer = Debouncer(delay=0.2)
    debouncer.run(action, "first")
    time.sleep(0.1)
    debouncer.run(action, "second") # This should cancel 'first'
    
    time.sleep(0.25)
    assert len(results) == 1
    assert results[0] == "second"

def test_debouncer_cancel():
    """Verify that cancel() stops any pending actions."""
    results = []
    def action():
        results.append(True)
        
    debouncer = Debouncer(delay=0.1)
    debouncer.run(action)
    debouncer.cancel()
    
    time.sleep(0.15)
    assert len(results) == 0
