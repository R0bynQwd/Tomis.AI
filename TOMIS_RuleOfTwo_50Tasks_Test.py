#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOMIS.AI Rule-of-Two Consensus Test - 50 Tasks
Tests distributed task validation across heterogeneous cluster nodes
"""

import subprocess
import json
import random
import time
import sys
from datetime import datetime
from collections import defaultdict

# Fix Windows encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class RuleOfTwoValidator:
    def __init__(self):
        self.results = []
        self.consensus = defaultdict(int)
        self.start_time = datetime.now()
        
    def run_task(self, task_id, command):
        """Execute a task and capture output"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout.strip() if result.returncode == 0 else "ERROR"
            return {
                'task_id': task_id,
                'status': 'success' if result.returncode == 0 else 'error',
                'output': output[:100],  # First 100 chars
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'task_id': task_id,
                'status': 'timeout',
                'output': 'TIMEOUT',
                'returncode': -1
            }
        except Exception as e:
            return {
                'task_id': task_id,
                'status': 'exception',
                'output': str(e)[:100],
                'returncode': -1
            }
    
    def get_random_node(self):
        """Get a random node from the cluster"""
        nodes = [
            "k3d-tomis-cluster-server-0",  # Master (Windows)
            "jetson-nvidia",                 # Jetson GPU
            "raspberrypi"                    # Pi CPU
        ]
        return random.choice(nodes)
    
    def validate_pair(self, task_id, pair1_node, pair2_node, test_command):
        """Send task to two nodes and compare results"""
        # Run on both nodes
        cmd1 = f"kubectl exec -it {pair1_node} -- {test_command}"
        cmd2 = f"kubectl exec -it {pair2_node} -- {test_command}"
        
        result1 = self.run_task(f"{task_id}_node1", cmd1)
        result2 = self.run_task(f"{task_id}_node2", cmd2)
        
        # Compare results
        match = (
            result1['status'] == result2['status'] and
            result1['returncode'] == result2['returncode']
        )
        
        return {
            'task_id': task_id,
            'pair1': pair1_node,
            'pair2': pair2_node,
            'result1_status': result1['status'],
            'result2_status': result2['status'],
            'match': match,
            'timestamp': datetime.now().isoformat()
        }
    
    def run_consensus_test(self, num_tasks=50):
        """Run Rule-of-Two validation on multiple tasks"""
        print(f"\n[RULE-OF-TWO TEST] Starting {num_tasks} distributed tasks\n")
        
        task_commands = [
            "echo 'Kubernetes API health' && kubectl version --short",
            "kubectl get nodes --no-headers | wc -l",
            "kubectl get pods -n kube-system --no-headers | wc -l",
            "date +%s",
            "uname -a | head -c 50",
        ]
        
        consensus_count = 0
        divergence_count = 0
        
        for task_id in range(1, num_tasks + 1):
            # Select two random nodes
            node1 = self.get_random_node()
            node2 = self.get_random_node()
            
            # If same node selected, pick a different one
            if node1 == node2:
                all_nodes = ["k3d-tomis-cluster-server-0", "jetson-nvidia", "raspberrypi"]
                all_nodes.remove(node1)
                node2 = random.choice(all_nodes)
            
            # Select random test command
            cmd = random.choice(task_commands)
            
            # Validate task through both nodes
            validation = self.validate_pair(task_id, node1, node2, cmd)
            
            if validation['match']:
                consensus_count += 1
                status_icon = "[OK]"
            else:
                divergence_count += 1
                status_icon = "[NO]"
            
            self.results.append(validation)
            
            # Print progress
            pct = (task_id / num_tasks) * 100
            bar = int(pct / 5)
            print(f"[{bar:2d}/20] Task {task_id:3d}: {status_icon} {node1} vs {node2}")
            
            time.sleep(0.5)  # Throttle requests
        
        # Calculate statistics
        total_tasks = len(self.results)
        consensus_pct = (consensus_count / total_tasks * 100) if total_tasks > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"RULE-OF-TWO CONSENSUS RESULTS (50 tasks)")
        print(f"{'='*60}")
        print(f"Total Tasks:       {total_tasks}")
        print(f"Consensus:         {consensus_count}/{total_tasks} ({consensus_pct:.1f}%)")
        print(f"Divergence:        {divergence_count}/{total_tasks} ({100-consensus_pct:.1f}%)")
        print(f"Start Time:        {self.start_time}")
        print(f"End Time:          {datetime.now()}")
        print(f"Duration:          {(datetime.now() - self.start_time).total_seconds():.1f}s")
        print(f"{'='*60}\n")
        
        return {
            'total': total_tasks,
            'consensus': consensus_count,
            'divergence': divergence_count,
            'consensus_pct': consensus_pct,
            'results': self.results
        }

if __name__ == "__main__":
    validator = RuleOfTwoValidator()
    report = validator.run_consensus_test(num_tasks=50)
    
    # Save report
    with open('E:\\NAI\\TOMIS_RuleOfTwo_50tasks_Report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved to: E:\\NAI\\TOMIS_RuleOfTwo_50tasks_Report.json")
