#!/usr/bin/env python3
"""
Test script for the voice command detection system.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.task_detector import TaskDetector

async def test_task_detection():
    """Test the task detection system with sample voice commands."""
    
    detector = TaskDetector()
    
    # Test cases
    test_cases = [
        "Arnav will fix the login bug by tomorrow",
        "We need to update the API documentation",
        "Kunal should deploy this to production tonight",
        "Someone needs to review the pull request",
        "Fix the database connection issue ASAP",
        "The weather is nice today",  # Should not detect a task
        "Let's schedule a meeting for next week",
        "Sarah will handle the frontend updates by Friday",
        "We must implement the new authentication system",
        "Update the user interface when possible"
    ]
    
    print("🧠 Testing AI-Powered Task Detection System")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. Input: \"{text}\"")
        
        try:
            detected_tasks = await detector.detect_tasks(text)
            
            if detected_tasks:
                print(f"   ✅ Detected {len(detected_tasks)} task(s):")
                for task in detected_tasks:
                    print(f"      📋 Title: {task.title}")
                    print(f"      👤 Assignee: {task.assignee or 'Not specified'}")
                    print(f"      📅 Deadline: {task.deadline or 'Not specified'}")
                    print(f"      🎯 Priority: {task.priority}")
                    print(f"      📊 Confidence: {task.confidence:.2f}")
                    print(f"      📝 Description: {task.description}")
                    print()
            else:
                print("   ❌ No tasks detected")
                
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Task Detection Test Complete!")
    
    # Test participants
    print(f"\n👥 Known Participants: {detector.get_participants()}")
    
    # Add a new participant
    detector.add_participant("Alice")
    print(f"👥 After adding Alice: {detector.get_participants()}")

if __name__ == "__main__":
    asyncio.run(test_task_detection())