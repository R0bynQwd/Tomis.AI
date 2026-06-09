#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOMIS.AI Stress Test - 100 Concurrent Simulated AI Tasks
Fabricated data with diverse workloads across all 3 nodes
"""

import json
import random
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class AITaskSimulator:
    def __init__(self):
        self.tasks_completed = 0
        self.tasks_by_node = defaultdict(int)
        self.results = []
        self.start_time = datetime.now()
        
    def simulate_ai_task(self, task_id, task_type):
        """Simulate AI workload with fabricated results"""
        nodes = ["Master (CPU)", "Jetson (GPU)", "Pi (CPU)"]
        node = random.choice(nodes)
        
        # Simulate processing time based on node
        if "GPU" in node:
            duration = random.uniform(0.5, 2.0)  # GPU faster
        elif "Master" in node:
            duration = random.uniform(1.0, 3.0)  # Master normal
        else:
            duration = random.uniform(2.0, 5.0)  # Pi slower
        
        time.sleep(duration * 0.1)  # Scale down for demo
        
        # Generate synthetic result based on task type
        results_map = {
            "whisper_asr": {
                "text": f"Fabricated transcription task {task_id}",
                "confidence": round(random.uniform(0.85, 0.99), 3),
                "language": random.choice(["ro", "en"])
            },
            "vision_classify": {
                "objects": random.randint(1, 10),
                "primary_class": random.choice(["person", "car", "phone", "chair"]),
                "confidence": round(random.uniform(0.75, 0.98), 3)
            },
            "ocr_detect": {
                "text_regions": random.randint(1, 50),
                "languages": ["ro", "en"],
                "avg_confidence": round(random.uniform(0.80, 0.96), 3)
            },
            "tts_generate": {
                "duration_ms": random.randint(1000, 30000),
                "sample_rate": 22050,
                "quality": random.choice(["normal", "high"])
            },
            "llm_inference": {
                "tokens": random.randint(50, 500),
                "latency_ms": random.randint(100, 5000),
                "model": "Gemma-2-9B"
            }
        }
        
        result = {
            "task_id": task_id,
            "type": task_type,
            "node": node,
            "duration_ms": int(duration * 1000),
            "status": "completed",
            "result": results_map.get(task_type, {"status": "ok"}),
            "timestamp": datetime.now().isoformat()
        }
        
        self.tasks_completed += 1
        self.tasks_by_node[node] += 1
        self.results.append(result)
        
        return result
    
    def run_stress_test(self, num_tasks=100, max_workers=10):
        """Run concurrent stress test"""
        print(f"\n[STRESS TEST] Starting {num_tasks} concurrent AI tasks\n")
        print(f"Max concurrent workers: {max_workers}")
        print(f"Task types: whisper_asr, vision_classify, ocr_detect, tts_generate, llm_inference\n")
        
        task_types = [
            "whisper_asr", "vision_classify", "ocr_detect", 
            "tts_generate", "llm_inference"
        ]
        
        task_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            # Submit all tasks
            for i in range(1, num_tasks + 1):
                task_type = random.choice(task_types)
                future = executor.submit(self.simulate_ai_task, i, task_type)
                futures[future] = i
            
            # Process completed tasks
            for future in as_completed(futures):
                task_count += 1
                result = future.result()
                
                pct = (task_count / num_tasks) * 100
                bar = int(pct / 5)
                
                print(f"[{bar:2d}/20] Task {task_count:3d}: {result['type']:20s} on {result['node']:15s} - {result['duration_ms']:5d}ms")
        
        # Calculate statistics
        duration = (datetime.now() - self.start_time).total_seconds()
        throughput = num_tasks / duration
        
        print(f"\n{'='*70}")
        print(f"STRESS TEST RESULTS (100 concurrent AI tasks)")
        print(f"{'='*70}")
        print(f"Total Tasks:           {self.tasks_completed}")
        print(f"Success Rate:          {self.tasks_completed}/{num_tasks} (100%)")
        print(f"Total Duration:        {duration:.2f}s")
        print(f"Throughput:            {throughput:.2f} tasks/sec")
        print(f"\nTask Distribution:")
        print(f"  Master (CPU):        {self.tasks_by_node['Master (CPU)']:3d} tasks")
        print(f"  Jetson (GPU):        {self.tasks_by_node['Jetson (GPU)']:3d} tasks")
        print(f"  Pi (CPU):            {self.tasks_by_node['Pi (CPU)']:3d} tasks")
        print(f"\nLatency Statistics:")
        
        durations = [r['duration_ms'] for r in self.results]
        if durations:
            print(f"  Min latency:         {min(durations):.0f}ms")
            print(f"  Max latency:         {max(durations):.0f}ms")
            print(f"  Avg latency:         {sum(durations)/len(durations):.0f}ms")
        
        print(f"{'='*70}\n")
        
        return {
            'total_tasks': self.tasks_completed,
            'duration': duration,
            'throughput': throughput,
            'distribution': dict(self.tasks_by_node),
            'results': self.results[:20]  # Save first 20 for inspection
        }

if __name__ == "__main__":
    simulator = AITaskSimulator()
    report = simulator.run_stress_test(num_tasks=100, max_workers=10)
    
    # Save report
    with open('E:\\NAI\\TOMIS_StressTest_100tasks_Report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Full report saved to: E:\\NAI\\TOMIS_StressTest_100tasks_Report.json")
