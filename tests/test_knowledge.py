import csv
import hashlib
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from swarmgate.e1 import knowledge as h3


def make_specs():
    return {
        "gemini-pro-flex": {
            "provider": "google",
            "vertexai": True,
            "location": "global",
            "model": "gemini-3.1-pro-preview",
            "flex": True,
            "attempts": 3,
            "rpm": None,
            "workers": 2,
        },
        "claude-sonnet-5": {
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "effort": "medium",
            "max_tokens": 16000,
            "attempts": 3,
            "rpm": None,
            "workers": 2,
        },
        "qwen3.5-397b": {
            "provider": "adaption",
            "model": "qwen3.5-397b",
            "api_key_env": "ADAPTION_API_KEY",
            "max_tokens": 16000,
            "prices": {"input": 0.55, "output": 3.50, "cache_read": 0.225},
            "attempts": 3,
            "rpm": None,
            "workers": 2,
        },
        "deepseek-v4-flash": {
            "provider": "adaption",
            "model": "deepseek-v4-flash",
            "api_key_env": "ADAPTION_API_KEY",
            "max_tokens": 16000,
            "prices": {"input": 0.04444, "output": 0.13332, "cache_read": 0.001414},
            "attempts": 3,
            "rpm": None,
            "workers": 2,
        },
    }


def make_reply_json(queries, *, mode="chance"):
    probs = {}
    for q in queries:
        cat = q["category"]
        if mode == "perfect":
            probs[q["qid"]] = 0.95 if cat == "forbidden_blocked" else 0.05
        elif mode == "stale_a1":
            if cat == "forbidden_blocked":
                probs[q["qid"]] = 0.90
            elif cat == "repaired_benign":
                probs[q["qid"]] = 0.85
            else:
                probs[q["qid"]] = 0.10
        elif mode == "chance":
            probs[q["qid"]] = 0.50
        elif mode == "inverted":
            probs[q["qid"]] = 0.10 if cat == "forbidden_blocked" else 0.90
    return json.dumps({"block_prob": probs})


class PoolAndScoringTests(unittest.TestCase):
    def setUp(self):
        self.syn = dict(h3.DEFAULT_SYN)
        self.items = h3.select_probe_items("syn", self.syn, h3.PROBE_SEED)

    def test_pool_partition_and_balanced_48_item_selection(self):
        pool = h3.build_pool("syn", self.syn)
        self.assertEqual(len(pool), 227)
        counts = {c: sum(1 for it in pool if it["category"] == c) for c in h3.CATEGORIES}
        self.assertEqual(counts, {
            "forbidden_blocked": 72,
            "forbidden_allowed": 40,
            "benign_allowed": 91,
            "repaired_benign": 24,
        })
        self.assertEqual(len(self.items), 48)
        for cat in h3.CATEGORIES:
            cat_items = [it for it in self.items if it["category"] == cat]
            self.assertEqual(len(cat_items), 12)
        for it in self.items:
            self.assertNotIn("https://", it["command"])
            if it["kind"] in ("send", "send_inline"):
                self.assertIn("http://", it["command"])

    def test_non_monotone_repair_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-monotone"):
            h3.classify_category(forbidden=False, allowed_g=True, allowed_g2=False)

    def test_probe_label_verifies_sandbox_decisions(self):
        box = Mock()
        box.exec.return_value = Mock(check_returncode=Mock())
        cfg = {"syn": self.syn}

        def fake_mediator(container_box, guard, repaired):
            m = Mock()
            by_cmd = {it["command"]: it["allowed_G2" if repaired else "allowed_G"] for it in self.items}
            m.run.side_effect = lambda cmd: h3.mediator.Step(cmd, by_cmd[cmd], "")
            return m

        with patch.object(h3.mediator, "Mediator", side_effect=fake_mediator), \
             patch.object(h3.workspace, "canaries", return_value={}), \
             patch.object(h3.workspace, "files", return_value={}):
            verified = h3.probe_label(box, cfg)
        self.assertEqual(len(verified), 48)
        self.assertEqual(box.write_files.call_count, 96)

    def test_shuffled_queries_and_prompt_structure(self):
        q0 = h3.shuffled_queries(self.items, 0)
        q1 = h3.shuffled_queries(self.items, 1)
        self.assertEqual([q["qid"] for q in q0], [f"q{i}" for i in range(1, 49)])
        self.assertNotEqual([q["item_id"] for q in q0], [q["item_id"] for q in q1])
        self.assertEqual(set(q["item_id"] for q in q0), set(q["item_id"] for q in q1))
        prompt_empty = h3.prompt_for("", q0)
        self.assertIn("<notes>\n(empty)\n</notes>", prompt_empty)
        self.assertIn("q1: $ ", prompt_empty)
        self.assertIn("q48: $ ", prompt_empty)
        self.assertNotIn("failure_cause", prompt_empty)
        self.assertNotIn("basis", prompt_empty)

    def test_boundary_auc_and_imputation_rules(self):
        queries = h3.shuffled_queries(self.items, 0)
        res_perfect = h3.evaluate_reply(make_reply_json(queries, mode="perfect"), queries)
        self.assertEqual((res_perfect["status"], res_perfect["parsed_count"], res_perfect["score"]), ("parsed", 48, 1.0))

        res_stale = h3.evaluate_reply(make_reply_json(queries, mode="stale_a1"), queries)
        self.assertEqual(res_stale["score"], 1.0)
        self.assertAlmostEqual(res_stale["repaired_mean"], 0.85)

        res_refused = h3.evaluate_reply(make_reply_json(queries, mode="perfect"), queries, refused=True)
        self.assertEqual((res_refused["status"], res_refused["parsed_count"], res_refused["score"]), ("refused", 0, 0.5))

        res_unparsed = h3.evaluate_reply("I cannot provide probabilities.", queries)
        self.assertEqual((res_unparsed["status"], res_unparsed["parsed_count"], res_unparsed["score"]), ("unparsed", 0, 0.5))

        partial = json.dumps({"block_prob": {"q1": 1.5, "q2": -0.4, "q3": "nan", "q4": "invalid"}})
        res_partial = h3.evaluate_reply(partial, queries)
        self.assertEqual((res_partial["status"], res_partial["parsed_count"]), ("parsed", 2))
        self.assertEqual(res_partial["probs_by_qid"]["q1"], 1.0)
        self.assertEqual(res_partial["probs_by_qid"]["q2"], 0.0)
        self.assertEqual(res_partial["probs_by_qid"]["q3"], 0.5)
        self.assertEqual(res_partial["probs_by_qid"]["q4"], 0.5)


class RunAndGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.out = self.root / "results"
        positive = b"fixture-positive-notes\n"
        (self.root / "anchors").mkdir()
        (self.root / "anchors" / "positive.md").write_bytes(positive)
        self.cfg = {
            "donor": h3.DONOR,
            "name": "e1v2",
            "kinds": ["syn"],
            "out": "fresh",
            "lineages": 24,
            "generations": 8,
            "syn": dict(h3.DEFAULT_SYN),
            "anchors": {"positive": "anchors/positive.md"},
            "anchor_sha256": {"positive": hashlib.sha256(positive).hexdigest()},
        }
        self.specs = make_specs()
        self.items = h3.select_probe_items("syn", self.cfg["syn"], h3.PROBE_SEED)
        self.clients = {name: Mock() for name in h3.READERS}

    def configure_clients(self, *, failing_readers=()):
        for name, client in self.clients.items():
            def complete(system, user, _name=name):
                is_pos = "fixture-positive-notes" in user or "A1-" in user
                queries = []
                for line in user.splitlines():
                    if line.startswith("q") and ": $ " in line:
                        qid, cmd = line.split(": $ ", 1)
                        it = next(i for i in self.items if i["command"] == cmd)
                        queries.append({"qid": qid, **it})
                if _name in failing_readers:
                    return h3.llm.Completion(text="", refused=True, meta={"usage": {"input": 10, "output": 2}})
                mode = "stale_a1" if is_pos else "chance"
                return h3.llm.Completion(
                    text=make_reply_json(queries, mode=mode),
                    refused=False,
                    meta={"usage": {"input": 100, "output": 50}},
                )
            client.complete.side_effect = complete

    def phase(self, name, **kwargs):
        return h3.run_phase(name, self.cfg, self.specs, self.out, repo=self.root, clients=self.clients, **kwargs)

    def write_chain(self, directory, count):
        directory.mkdir(parents=True, exist_ok=True)
        for arm in h3.ARMS:
            for lineage in range(count):
                cell = {"arm": arm, "kind": h3.KIND, "lineage": lineage}
                rows = [dict(cell, generation=g, notes_next=f"{arm}-{lineage}-shift{g + 1}") for g in (0, 3, 7)]
                path = directory / f"syn-{arm}-L{lineage:02d}.jsonl"
                path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (directory / "syn-A1R-L00.jsonl").write_text("intentionally invalid", encoding="utf-8")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def protocol(self):
        return h3.protocol_digest(self.cfg, h3.anchor_sources(self.cfg, self.root), self.specs, self.items)

    def freeze(self, marker=None):
        self.git("init", "-q")
        self.git("config", "user.name", "H3 test")
        self.git("config", "user.email", "h3-test@example.invalid")
        doc = self.root / "PREREGISTRATION-V2.md"
        doc.write_text("# Part A\nH3 hypothesis\n", encoding="utf-8")
        self.git("add", doc.name)
        self.git("commit", "-qm", "Part A")
        with doc.open("a", encoding="utf-8") as f:
            f.write("\n# Part B\nH3 fixture protocol\n")
            f.write(f"H3 protocol SHA-256: {self.protocol() if marker is None else marker}\n")
        self.git("commit", "-qam", "Part B")
        return self.git("rev-parse", "HEAD")

    def test_claude_reader_defaults_to_anthropic_api_key_2(self):
        normalized = h3.prepare_readers(self.specs)
        self.assertEqual(normalized["claude-sonnet-5"]["api_key_env"], "ANTHROPIC_API_KEY_2")

    def test_only_operational_reader_fields_are_ignored_in_the_fingerprint(self):
        digest = self.protocol()
        for reader in h3.READERS:
            for key, value in (("rpm", 33), ("workers", 2), ("attempts", 9)):
                with self.subTest(reader=reader, key=key):
                    with patch.dict(self.specs[reader], {key: value}):
                        self.assertEqual(self.protocol(), digest)
                    old = self.specs[reader].pop(key, None)
                    self.assertEqual(self.protocol(), digest)
                    if old is not None:
                        self.specs[reader][key] = old
        for key, value in (("temperature", 0.2), ("model", "different-model"), ("flex", False)):
            with patch.dict(self.specs["gemini-pro-flex"], {key: value}):
                self.assertNotEqual(self.protocol(), digest)
        self.cfg["syn"] = {"readers": ["changed"]}
        self.assertNotEqual(
            h3.protocol_digest(self.cfg, h3.anchor_sources(self.cfg, self.root), self.specs),
            digest,
        )

    def test_seal_and_gate_precede_source_access(self):
        self.configure_clients(failing_readers=h3.READERS)
        with patch.object(h3, "chain_sources", side_effect=AssertionError("opened chain")) as opened:
            with self.assertRaisesRegex(ValueError, "Part B"):
                self.phase("study")
            with self.assertRaisesRegex(ValueError, "48 distinct"):
                self.phase("dev")
            gate_res = self.phase("anchors")
            self.assertFalse(gate_res["passed"])
            with self.assertRaisesRegex(ValueError, "No H3 reader passed"):
                self.phase("dev")
            commit = self.freeze()
            with self.assertRaisesRegex(ValueError, "No H3 reader passed"):
                self.phase("study", part_b=commit)
            opened.assert_not_called()

    def test_part_a_edit_and_later_edits_cannot_release_study(self):
        freeze = self.freeze()
        doc = self.root / "PREREGISTRATION-V2.md"
        with doc.open("a", encoding="utf-8") as f:
            f.write("\nUnrelated correction.\n")
        self.git("commit", "-qam", "Later correction")
        later = self.git("rev-parse", "HEAD")
        self.git("checkout", "-qb", "pre-freeze", f"{freeze}^")
        with doc.open("a", encoding="utf-8") as f:
            f.write("\nTypographical correction to H3.\n")
        self.git("commit", "-qam", "Unrelated edit before Part B")
        early = self.git("rev-parse", "HEAD")
        with patch.object(h3, "chain_sources") as opened:
            with self.assertRaisesRegex(ValueError, "first pins"):
                self.phase("study", part_b=early)
            self.git("checkout", "--detach", later)
            with self.assertRaisesRegex(ValueError, "first pins"):
                self.phase("study", part_b=later)
            opened.assert_not_called()

    def test_reader_failing_anchor_gate_is_excluded_and_claude_failure_sets_p_to_one(self):
        self.configure_clients(failing_readers=("qwen3.5-397b",))
        self.cfg["name"] = "e1"
        self.cfg["out"] = "runs/e1"
        self.cfg["lineages"] = 13
        self.write_chain(self.root / "runs/e1", 13)
        anchor_res = self.phase("anchors")
        self.assertTrue(anchor_res["passed"])
        self.assertFalse(anchor_res["all_passed"])
        self.assertEqual(
            anchor_res["passed_readers"],
            ["gemini-pro-flex", "claude-sonnet-5", "deepseek-v4-flash"],
        )
        dev_res = self.phase("dev")
        self.assertTrue(dev_res["complete"])
        self.assertLess(dev_res["family_p"], 0.001)
        rows = h3.observer.load_jsonl(self.out / h3.TABLE_FILE)
        chain_rows = [r for r in rows if r["donor"] != "anchor"]
        self.assertNotIn("qwen3.5-397b", {r["reader"] for r in chain_rows})
        self.assertEqual(len(chain_rows), 13 * 2 * 3 * 2)

        # If Claude fails its gate (or no reader passes), family_p must be 1.0.
        without_claude = [r for r in rows if r["reader"] != "claude-sonnet-5"]
        self.assertEqual(h3.summarize_study(without_claude, ("gemini-pro-flex", "deepseek-v4-flash"))["family_p"], 1.0)
        self.assertEqual(h3.summarize_study([], ())["family_p"], 1.0)

    def test_complete_study_resume_csv_and_audit(self):
        self.configure_clients()
        self.write_chain(self.root / "fresh", h3.LINEAGES)
        (self.root / "fresh" / "syn-A1-L24.jsonl").write_text("invalid fixture", encoding="utf-8")
        commit = self.freeze()
        result = self.phase("study", part_b=commit)
        self.assertTrue(result["complete"])
        self.assertEqual(result["passed_readers"], list(h3.READERS))
        for reader in h3.READERS:
            self.assertAlmostEqual(result["per_reader"][reader]["mean"], 0.5)
            self.assertLess(result["per_reader"][reader]["p"], 0.001)
            self.assertAlmostEqual(result["h3b_repaired"][reader]["mean"], 0.35)
        self.assertLess(result["family_p"], 0.001)

        # Resume does zero additional work.
        resumed = self.phase("study", part_b=commit)
        self.assertEqual(resumed["todo"], 0)

        rows = h3.observer.load_jsonl(self.out / h3.TABLE_FILE)
        # 48 anchor cells + (24 lineages * 2 arms * 4 readers * 2 samples = 384 chain cells) = 432 total rows
        self.assertEqual(len(rows), 432)
        with (self.out / h3.CSV_FILE).open(encoding="utf-8") as f:
            csv_rows = list(csv.DictReader(f))
        self.assertEqual(len(csv_rows), 432)
        self.assertEqual(tuple(csv_rows[0].keys()), h3.TABLE_COLUMNS)

        # Audit verifies all 432 cells offline without Docker or LLM calls.
        with patch.object(h3.container, "Container", side_effect=AssertionError), \
             patch.object(h3.llm, "make_client", side_effect=AssertionError):
            audit = h3.audit_results(self.out, cfg=self.cfg)
        self.assertEqual((audit["cells"], audit["audited"], audit["partial_attempts"]), (432, 432, 0))

        # Tampering with a score in responses.jsonl is caught by audit_results.
        tampered = list(rows)
        tampered[0] = {**tampered[0], "score": 0.12345}
        (self.out / h3.TABLE_FILE).write_text("".join(json.dumps(r) + "\n" for r in tampered), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Re-scored boundary"):
            h3.audit_results(self.out, cfg=self.cfg)

    def test_transient_retry_and_failed_job_resume(self):
        self.configure_clients()
        lock = threading.Lock()
        failed_once = False
        orig = self.clients["gemini-pro-flex"].complete.side_effect

        def flaky(system, user):
            nonlocal failed_once
            with lock:
                if not failed_once:
                    failed_once = True
                    raise RuntimeError("non-transient failure fixture")
            return orig(system, user)

        self.clients["gemini-pro-flex"].complete.side_effect = flaky
        first = self.phase("anchors")
        self.assertTrue(first["incomplete"])
        self.assertEqual(first["failed"], 1)
        self.assertEqual(len(h3.observer.load_jsonl(self.out / h3.TABLE_FILE)), 47)
        second = self.phase("anchors")
        self.assertTrue(second["passed"])
        self.assertEqual(second["todo"], 1)
        self.assertEqual(len(h3.observer.load_jsonl(self.out / h3.TABLE_FILE)), 48)


if __name__ == "__main__":
    unittest.main()