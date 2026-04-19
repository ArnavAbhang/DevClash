#!/usr/bin/env python3
"""
🚨 QUICK TEST - CRITICAL CHECKLIST
Test the buffered task detection system.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.task_detector import TaskDetector

async def test_buffered_processing():
    """Test the new buffered processing system."""
    
    detector = TaskDetector()
    
    print("🚨 CRITICAL CHECKLIST - QUICK TEST")
    print("=" * 50)
    
    # ✅ 1. Test buffering
    print("\n1️⃣ TESTING BUFFERING:")
    print("-" * 30)
    
    # Simulate partial chunks (should buffer)
    chunks = ["Arnav", "will", "fix", "the", "login", "bug", "by", "tomorrow", "morning", "please", "do", "it", "fast"]
    
    all_tasks = []
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: '{chunk}'")
        tasks = await detector.process_transcript_chunk(chunk)
        all_tasks.extend(tasks)
        
        if tasks:
            print(f"  🎯 TASKS DETECTED: {len(tasks)}")
            for task in tasks:
                print(f"    📋 {task.title}")
                print(f"    👤 {task.assignee}")
                print(f"    📅 {task.deadline}")
    
    # ✅ 2. Flush remaining buffer
    print(f"\n2️⃣ FLUSHING BUFFER:")
    print("-" * 30)
    final_tasks = await detector.flush_buffer()
    all_tasks.extend(final_tasks)
    
    if final_tasks:
        print(f"  🎯 FINAL TASKS: {len(final_tasks)}")
        for task in final_tasks:
            print(f"    📋 {task.title}")
    
    # ✅ 3. Test complete sentence
    print(f"\n3️⃣ TESTING COMPLETE SENTENCE:")
    print("-" * 30)
    
    complete_text = "Kunal will deploy the new features to production tonight"
    print(f"Input: '{complete_text}'")
    
    tasks = await detector.detect_tasks(complete_text)
    print(f"Tasks detected: {len(tasks)}")
    
    for task in tasks:
        print(f"  📋 Title: {task.title}")
        print(f"  👤 Assignee: {task.assignee}")
        print(f"  📅 Deadline: {task.deadline}")
        print(f"  🎯 Priority: {task.priority}")
        print(f"  📊 Confidence: {task.confidence:.2f}")
    
    # ✅ 4. Summary
    print(f"\n4️⃣ SUMMARY:")
    print("-" * 30)
    print(f"  📊 Total tasks from chunks: {len(all_tasks)}")
    print(f"  📊 Tasks from complete sentence: {len(tasks)}")
    
    if len(all_tasks) > 0 or len(tasks) > 0:
        print("  ✅ BUFFERING SYSTEM WORKING!")
    else:
        print("  ❌ NO TASKS DETECTED - CHECK LLM PROMPT")
    
    print("\n" + "=" * 50)
    print("🎯 QUICK TEST COMPLETE!")

if __name__ == "__main__":
    asyncio.run(test_buffered_processing())