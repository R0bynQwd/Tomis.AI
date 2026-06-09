import argparse
import base64
import datetime as dt
import hashlib
import itertools
import json
import os
import random
import time
from pathlib import Path

import paramiko


WORKERS = [
    {"name": "master-local", "kind": "local", "host": None},
    {"name": "jetson-116", "kind": "ssh", "host": "192.168.1.116"},
    {"name": "edge-117", "kind": "ssh", "host": "192.168.1.117"},
]

TASK_TYPES = ["asr", "ocr", "nlp", "vision", "tts", "rag", "lpr", "forensics"]


def now_iso():
    return dt.datetime.now().isoformat(timespec="seconds")


def fabricate_task(task_id: int):
    rng = random.Random(time.time_ns() ^ task_id)
    ttype = rng.choice(TASK_TYPES)
    text = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789 ") for _ in range(rng.randint(40, 120))).strip()
    nums = [rng.randint(0, 9999) for _ in range(rng.randint(8, 20))]
    return {
        "task_id": task_id,
        "task_type": ttype,
        "text": text,
        "numbers": nums,
        "ts": now_iso(),
    }


def ai_simulate(worker_name: str, payload: dict):
    seed_src = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(seed_src.encode("utf-8")).hexdigest()
    base = int(digest[:8], 16) / 0xFFFFFFFF
    jitter_rng = random.Random(hashlib.sha256((worker_name + digest).encode("utf-8")).hexdigest())
    noise = jitter_rng.uniform(-0.22, 0.22)
    score = max(0.0, min(1.0, base + noise))
    label = "accept" if score >= 0.55 else "reject"
    embedding = hashlib.md5((payload["text"] + worker_name).encode("utf-8")).hexdigest()[:12]
    return {
        "worker": worker_name,
        "label": label,
        "score": round(score, 4),
        "embedding": embedding,
        "payload_hash": digest,
    }


def run_local(worker_name: str, payload: dict):
    return {"ok": True, "result": ai_simulate(worker_name, payload), "error": None}


def run_ssh(host: str, username: str, password: str, worker_name: str, payload: dict, timeout=25):
    enc = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    script = (
        "python3 - <<'PY'\n"
        "import base64, hashlib, json, random\n"
        f"worker_name={json.dumps(worker_name)}\n"
        f"enc={json.dumps(enc)}\n"
        "payload=json.loads(base64.b64decode(enc).decode('utf-8'))\n"
        "seed_src=json.dumps(payload, sort_keys=True, ensure_ascii=False)\n"
        "digest=hashlib.sha256(seed_src.encode('utf-8')).hexdigest()\n"
        "base=int(digest[:8],16)/0xFFFFFFFF\n"
        "jitter_rng=random.Random(hashlib.sha256((worker_name+digest).encode('utf-8')).hexdigest())\n"
        "noise=jitter_rng.uniform(-0.22,0.22)\n"
        "score=max(0.0,min(1.0,base+noise))\n"
        "label='accept' if score>=0.55 else 'reject'\n"
        "embedding=hashlib.md5((payload['text']+worker_name).encode('utf-8')).hexdigest()[:12]\n"
        "print(json.dumps({'worker':worker_name,'label':label,'score':round(score,4),'embedding':embedding,'payload_hash':digest}, ensure_ascii=False))\n"
        "PY"
    )
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(hostname=host, username=username, password=password, timeout=10, banner_timeout=10, auth_timeout=10)
        _, stdout, stderr = cli.exec_command(script, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace").strip()
        err = stderr.read().decode("utf-8", "replace").strip()
        if err and not out:
            return {"ok": False, "result": None, "error": err}
        line = out.splitlines()[-1] if out else ""
        result = json.loads(line)
        return {"ok": True, "result": result, "error": None}
    except Exception as exc:
        return {"ok": False, "result": None, "error": str(exc)}
    finally:
        try:
            cli.close()
        except Exception:
            pass


def execute_on(worker: dict, payload: dict, username: str, password: str):
    if worker["kind"] == "local":
        return run_local(worker["name"], payload)
    return run_ssh(worker["host"], username, password, worker["name"], payload)


def very_different(a: dict, b: dict):
    if a["label"] != b["label"]:
        return True
    if abs(a["score"] - b["score"]) > 0.18:
        return True
    return False


def choose_alternate_pair(initial_pair_names):
    all_pairs = list(itertools.combinations([w["name"] for w in WORKERS], 2))
    for pair in all_pairs:
        if set(pair) != set(initial_pair_names):
            return pair
    return initial_pair_names


def worker_by_name(name):
    for w in WORKERS:
        if w["name"] == name:
            return w
    raise KeyError(name)


def run_soak(minutes: int, interval: int, out_dir: Path, ssh_user: str, ssh_pass: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl = out_dir / f"rule2_soak_{run_id}.jsonl"
    summary_file = out_dir / f"rule2_summary_{run_id}.json"

    end_at = time.time() + minutes * 60
    task_id = 1
    stats = {
        "total_tasks": 0,
        "initial_matches": 0,
        "initial_mismatches": 0,
        "escalations": 0,
        "final_consensus": 0,
        "final_inconclusive": 0,
        "worker_success": {w["name"]: 0 for w in WORKERS},
        "worker_fail": {w["name"]: 0 for w in WORKERS},
    }

    pairs = [("jetson-116", "edge-117"), ("master-local", "jetson-116"), ("master-local", "edge-117")]
    pair_index = 0

    while time.time() < end_at:
        payload = fabricate_task(task_id)
        p1 = pairs[pair_index % len(pairs)]
        pair_index += 1

        w1 = worker_by_name(p1[0])
        w2 = worker_by_name(p1[1])
        r1 = execute_on(w1, payload, ssh_user, ssh_pass)
        r2 = execute_on(w2, payload, ssh_user, ssh_pass)

        for w, r in ((w1, r1), (w2, r2)):
            if r["ok"]:
                stats["worker_success"][w["name"]] += 1
            else:
                stats["worker_fail"][w["name"]] += 1

        record = {
            "ts": now_iso(),
            "task_id": task_id,
            "task_type": payload["task_type"],
            "initial_pair": list(p1),
            "initial": {
                w1["name"]: r1,
                w2["name"]: r2,
            },
            "escalated": False,
            "alternate_pair": None,
            "alternate": {},
            "final_status": "inconclusive",
        }

        stats["total_tasks"] += 1
        initial_ok = r1["ok"] and r2["ok"]
        if initial_ok and not very_different(r1["result"], r2["result"]):
            stats["initial_matches"] += 1
            stats["final_consensus"] += 1
            record["final_status"] = "consensus_initial"
        else:
            stats["initial_mismatches"] += 1
            stats["escalations"] += 1
            record["escalated"] = True
            p2 = choose_alternate_pair(p1)
            record["alternate_pair"] = list(p2)
            aw1 = worker_by_name(p2[0])
            aw2 = worker_by_name(p2[1])
            ar1 = execute_on(aw1, payload, ssh_user, ssh_pass)
            ar2 = execute_on(aw2, payload, ssh_user, ssh_pass)
            record["alternate"] = {aw1["name"]: ar1, aw2["name"]: ar2}

            for w, r in ((aw1, ar1), (aw2, ar2)):
                if r["ok"]:
                    stats["worker_success"][w["name"]] += 1
                else:
                    stats["worker_fail"][w["name"]] += 1

            if ar1["ok"] and ar2["ok"] and not very_different(ar1["result"], ar2["result"]):
                stats["final_consensus"] += 1
                record["final_status"] = "consensus_alternate"
            else:
                stats["final_inconclusive"] += 1
                record["final_status"] = "inconclusive"

        with jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(
            f"[{record['ts']}] task={task_id} type={payload['task_type']} "
            f"pair={p1[0]}+{p1[1]} escalated={record['escalated']} final={record['final_status']}"
        )
        task_id += 1
        time.sleep(max(2, interval))

    stats["started"] = now_iso()
    stats["ended"] = now_iso()
    stats["jsonl"] = str(jsonl)
    summary_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(summary_file), "jsonl": str(jsonl), "stats": stats}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="TOMIS Rule-of-Two AI random soak")
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--interval", type=int, default=12)
    parser.add_argument("--out-dir", default="soak_artifacts")
    parser.add_argument("--ssh-user", default=os.getenv("TOMIS_SSH_USER", "root"))
    parser.add_argument("--ssh-pass", default=os.getenv("TOMIS_SSH_PASS", ""))
    args = parser.parse_args()
    if not args.ssh_pass:
        raise SystemExit("Missing ssh password: use --ssh-pass or TOMIS_SSH_PASS")
    run_soak(args.minutes, args.interval, Path(args.out_dir), args.ssh_user, args.ssh_pass)


if __name__ == "__main__":
    main()
