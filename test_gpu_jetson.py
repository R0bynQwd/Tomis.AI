#!/usr/bin/env python3
"""
GPU Stress Test for Jetson via SSH and kubectl exec
Tests actual GPU usage on Jetson NVIDIA TX2/Xavier
"""

import subprocess
import json
import os
import sys
from pathlib import Path

def run_kubectl_exec(cmd):
    """Run command in Jetson pod via kubectl exec"""
    try:
        result = subprocess.run(
            ["kubectl", "exec", "-it", "gpu-test", "--", "bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

def test_gpu_hardware():
    """Test GPU hardware detection and tools"""
    print("=" * 60)
    print("GPU HARDWARE TEST - JETSON")
    print("=" * 60)
    
    tests = {
        "NVIDIA Device Files": "ls -la /dev/nvidia* 2>&1 || echo 'No NVIDIA devices'",
        "NVIDIA Tools": "which nvidia-smi && nvidia-smi -L 2>&1 || echo 'nvidia-smi not available'",
        "GPU Count": "nvidia-smi --query-gpu=count --format=csv,noheader 2>&1 || echo '0'",
        "GPU Memory": "nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>&1 || echo 'Unknown'",
    }
    
    for test_name, cmd in tests.items():
        print(f"\n[TEST] {test_name}")
        print(f"  Command: {cmd}")
        output = run_kubectl_exec(cmd)
        for line in output.split('\n')[:5]:  # First 5 lines
            if line.strip():
                print(f"  > {line}")

def test_gpu_workload():
    """Launch GPU-intensive workload"""
    print("\n" + "=" * 60)
    print("GPU WORKLOAD TEST - VECTORIZED MATRIX OPS")
    print("=" * 60)
    
    # Create a Python script that uses GPU if available
    gpu_test_py = """
import numpy as np
try:
    import cupy as cp
    print("✅ CuPy available - GPU acceleration enabled")
    gpu = True
except ImportError:
    print("⚠️  CuPy not available - using NumPy (CPU only)")
    gpu = False

# Matrix multiplication stress test
print("\\n[STRESS TEST] 1000x matrix mult (10000x10000)")
try:
    if gpu:
        a = cp.random.random((10000, 10000), dtype=cp.float32)
        b = cp.random.random((10000, 10000), dtype=cp.float32)
        result = cp.matmul(a, b)
        print(f"✅ GPU result shape: {result.shape}")
    else:
        a = np.random.random((10000, 10000)).astype(np.float32)
        b = np.random.random((10000, 10000)).astype(np.float32)
        result = np.matmul(a, b)
        print(f"✅ CPU result shape: {result.shape}")
except Exception as e:
    print(f"❌ Error: {e}")
"""
    
    cmd = f"python3 -c \"{gpu_test_py.replace(chr(10), '; ')}\""
    print("\nRunning GPU workload...")
    output = run_kubectl_exec(cmd)
    for line in output.split('\n'):
        if line.strip():
            print(f"  {line}")

def test_docker_runtime():
    """Check Docker GPU runtime configuration"""
    print("\n" + "=" * 60)
    print("DOCKER RUNTIME CHECK")
    print("=" * 60)
    
    cmd = "docker info 2>/dev/null | grep -i 'runtime\\|nvidia' || echo 'Docker info unavailable'"
    output = run_kubectl_exec(cmd)
    for line in output.split('\n'):
        if line.strip():
            print(f"  {line}")

def generate_report():
    """Generate JSON report"""
    report = {
        "test_name": "Jetson GPU Diagnostic",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "status": "IN_PROGRESS",
        "findings": []
    }
    
    # Check if nvidia-smi works
    nvidia_check = run_kubectl_exec("nvidia-smi -L 2>&1 | wc -l")
    gpu_count = 0
    try:
        gpu_count = int(nvidia_check.strip())
    except:
        pass
    
    if gpu_count > 0:
        report["findings"].append(f"✅ NVIDIA GPU found: {gpu_count} device(s)")
        report["status"] = "GPU_AVAILABLE"
    else:
        report["findings"].append("❌ No NVIDIA GPU detected on Jetson")
        report["status"] = "NO_GPU"
    
    return report

if __name__ == "__main__":
    print("\n>>> TOMIS.AI GPU Diagnostic Suite v1.0")
    print("Testing Jetson NVIDIA GPU via Kubernetes exec")
    print()
    
    # First ensure pod exists
    print("[SETUP] Verifying gpu-test pod...")
    result = subprocess.run(
        ["kubectl", "get", "pod", "gpu-test"],
        capture_output=True,
        text=True
    )
    if "gpu-test" not in result.stdout:
        print("❌ gpu-test pod not found. Create it first:")
        print("   kubectl apply -f gpu-test-pod.yaml")
        sys.exit(1)
    print("✅ gpu-test pod ready\n")
    
    # Run tests
    test_gpu_hardware()
    test_docker_runtime()
    test_gpu_workload()
    
    # Report
    report = generate_report()
    print("\n" + "=" * 60)
    print("REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    
    report_path = Path("E:/NAI/gpu_test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n✓ Report saved: {report_path}")
