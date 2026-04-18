import os
import asyncio
import unittest
import uuid

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

from app.api.deps import get_grammar_provider, get_summarize_provider
from app.main import app


class FakeGrammarProvider:
    async def analyze(self, text: str, language: str = "en-US") -> list[dict]:
        lowered = text.lower()
        start = lowered.find("ths")
        original = text[start : start + 3] if start >= 0 else "Ths"
        return [
            {
                "start": 0 if start < 0 else start,
                "length": 3,
                "message": "Spelling mistake",
                "rule_id": "TEST_SPELL",
                "category": "typo",
                "severity": "warning",
                "original": original,
                "replacements": ["This"],
            }
        ]


class FakeSummarizeProvider:
    async def summarize(
        self,
        source_text: str,
        language: str = "en",
        style: str = "paragraph",
        max_tokens: int | None = None,
    ) -> dict:
        prefix = source_text.strip().replace("\n", " ")[:60]
        return {
            "summary": f"[{language}/{style}] {prefix}",
            "model": "fake-summarizer",
            "prompt_tokens": len(source_text.split()),
            "completion_tokens": 12,
            "total_tokens": len(source_text.split()) + 12,
        }


class ApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.async_database_url = os.environ["DATABASE_URL"]

    def setUp(self):
        self.suffix = uuid.uuid4().hex[:10]
        self.username = f"itest_{self.suffix}"
        self.email = f"{self.username}@example.com"
        self.password = "Passw0rd!"

        app.dependency_overrides[get_grammar_provider] = lambda: FakeGrammarProvider()
        app.dependency_overrides[get_summarize_provider] = lambda: FakeSummarizeProvider()

        self._cleanup_test_users()
        self.client_cm = TestClient(app)
        self.client = self.client_cm.__enter__()

    def tearDown(self):
        self.client_cm.__exit__(None, None, None)
        app.dependency_overrides.clear()
        self._cleanup_test_users()

    def _cleanup_test_users(self):
        asyncio.run(self._cleanup_test_users_async())

    async def _cleanup_test_users_async(self):
        engine = create_async_engine(self.async_database_url, future=True)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "DELETE FROM users "
                        "WHERE username LIKE :username_pattern "
                        "OR email LIKE :email_pattern"
                    ),
                    {
                        "username_pattern": "itest_%",
                        "email_pattern": "itest_%@example.com",
                    },
                )
        finally:
            await engine.dispose()

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_route_surface(self):
        routes = {
            (tuple(sorted((getattr(route, "methods", set()) or set()) - {"HEAD"})), route.path)
            for route in app.router.routes
            if hasattr(route, "path")
        }

        self.assertIn((("GET",), "/folders/{folder_id}/notes/"), routes)
        self.assertIn((("POST",), "/summarize/notes/{note_id}"), routes)
        self.assertIn((("GET",), "/users/active/"), routes)

    def test_full_application_flow(self):
        unauthorized = self.client.get("/tags/")
        self.assertEqual(unauthorized.status_code, 401, unauthorized.text)

        create_user = self.client.post(
            "/users/",
            json={
                "username": self.username,
                "email": self.email,
                "password": self.password,
                "dob": "1998-01-01",
                "phone_number": "123456789",
            },
        )
        self.assertEqual(create_user.status_code, 201, create_user.text)
        user = create_user.json()
        user_id = user["id"]

        login = self.client.post(
            "/auth/login",
            json={"username": self.username, "password": self.password},
        )
        self.assertEqual(login.status_code, 200, login.text)
        token = login.json()["access_token"]
        headers = self._auth_headers(token)

        get_user = self.client.get(f"/users/{user_id}")
        self.assertEqual(get_user.status_code, 200, get_user.text)
        self.assertEqual(get_user.json()["username"], self.username)

        all_users = self.client.get("/users/")
        self.assertEqual(all_users.status_code, 200, all_users.text)
        self.assertTrue(any(row["id"] == user_id for row in all_users.json()))

        active_users = self.client.get("/users/active/")
        self.assertEqual(active_users.status_code, 200, active_users.text)
        self.assertTrue(any(row["id"] == user_id for row in active_users.json()))

        update_user = self.client.put(
            f"/users/{user_id}",
            json={"phone_number": "987654321"},
        )
        self.assertEqual(update_user.status_code, 200, update_user.text)
        self.assertEqual(update_user.json()["phone_number"], "987654321")

        create_tag = self.client.post("/tags/", headers=headers, json={"title": "Integration Tag"})
        self.assertEqual(create_tag.status_code, 201, create_tag.text)
        tag_id = create_tag.json()["id"]

        update_tag = self.client.put(
            f"/tags/{tag_id}",
            headers=headers,
            json={"title": "Integration Tag Updated"},
        )
        self.assertEqual(update_tag.status_code, 200, update_tag.text)
        self.assertEqual(update_tag.json()["title"], "Integration Tag Updated")

        create_folder = self.client.post(
            "/folders/",
            headers=headers,
            json={"title": "Integration Folder", "parent_id": None},
        )
        self.assertEqual(create_folder.status_code, 201, create_folder.text)
        folder_id = create_folder.json()["id"]

        get_folder = self.client.get(f"/folders/{folder_id}", headers=headers)
        self.assertEqual(get_folder.status_code, 200, get_folder.text)

        list_folders = self.client.get("/folders/", headers=headers)
        self.assertEqual(list_folders.status_code, 200, list_folders.text)
        self.assertTrue(any(row["id"] == folder_id for row in list_folders.json()))

        update_folder = self.client.put(
            f"/folders/{folder_id}",
            headers=headers,
            json={"title": "Integration Folder Updated"},
        )
        self.assertEqual(update_folder.status_code, 200, update_folder.text)
        self.assertEqual(update_folder.json()["title"], "Integration Folder Updated")

        create_note = self.client.post(
            "/notes/",
            headers=headers,
            json={
                "title": "Integration Note",
                "content_md": "Ths is teh first body.",
                "folder_id": folder_id,
                "tag_ids": [tag_id, 999999999],
                "is_public": False,
            },
        )
        self.assertEqual(create_note.status_code, 201, create_note.text)
        note = create_note.json()
        note_id = note["id"]
        self.assertEqual(note["version"], 1)
        self.assertEqual(create_note.headers.get("X-Ignored-Tags"), "999999999")

        get_note = self.client.get(f"/notes/{note_id}", headers=headers)
        self.assertEqual(get_note.status_code, 200, get_note.text)
        self.assertEqual(get_note.json()["title"], "Integration Note")

        list_notes = self.client.get("/notes/", headers=headers)
        self.assertEqual(list_notes.status_code, 200, list_notes.text)
        self.assertTrue(any(row["id"] == note_id for row in list_notes.json()))

        folder_notes = self.client.get(f"/folders/{folder_id}/notes/", headers=headers)
        self.assertEqual(folder_notes.status_code, 200, folder_notes.text)
        self.assertEqual(folder_notes.json()["folder"]["id"], folder_id)
        self.assertTrue(any(row["id"] == note_id for row in folder_notes.json()["notes"]))

        update_note = self.client.put(
            f"/notes/{note_id}",
            headers=headers,
            json={
                "title": "Integration Note Updated",
                "content_md": "Ths is teh updated body.",
                "tag_ids": [tag_id],
            },
        )
        self.assertEqual(update_note.status_code, 200, update_note.text)
        updated_note = update_note.json()
        self.assertEqual(updated_note["version"], 2)
        self.assertEqual(updated_note["title"], "Integration Note Updated")

        revisions_for_note = self.client.get(
            f"/revisions/notes/{note_id}/revisions",
            headers=headers,
        )
        self.assertEqual(revisions_for_note.status_code, 200, revisions_for_note.text)
        revisions = revisions_for_note.json()
        self.assertGreaterEqual(len(revisions), 2)
        initial_revision_id = next(row["id"] for row in revisions if row["version"] == 1)

        create_revision = self.client.post(
            "/revisions/",
            headers=headers,
            json={
                "note_id": note_id,
                "version": 1,
                "title": "Manual Revision",
                "content_md": "Ths manual revision body.",
                "is_public": False,
                "folder_id": folder_id,
                "tag_ids": [tag_id],
            },
        )
        self.assertEqual(create_revision.status_code, 201, create_revision.text)
        manual_revision = create_revision.json()
        manual_revision_id = manual_revision["id"]

        update_revision = self.client.put(
            f"/revisions/{manual_revision_id}",
            headers=headers,
            json={"title": "Manual Revision Updated"},
        )
        self.assertEqual(update_revision.status_code, 200, update_revision.text)
        self.assertEqual(update_revision.json()["title"], "Manual Revision Updated")

        render_json = self.client.get(
            f"/revisions/notes/{note_id}/revisions/{manual_revision_id}/render",
            headers={**headers, "Accept": "application/json"},
        )
        self.assertEqual(render_json.status_code, 200, render_json.text)
        etag = render_json.headers.get("ETag")
        self.assertTrue(etag)
        self.assertIn("<p>", render_json.json()["html"])

        render_not_modified = self.client.get(
            f"/revisions/notes/{note_id}/revisions/{manual_revision_id}/render",
            headers={**headers, "If-None-Match": etag},
        )
        self.assertEqual(render_not_modified.status_code, 304, render_not_modified.text)

        get_etag = self.client.get(
            f"/revisions/notes/{note_id}/revisions/{manual_revision_id}/etag",
            headers=headers,
        )
        self.assertEqual(get_etag.status_code, 200, get_etag.text)
        self.assertEqual(get_etag.headers.get("ETag"), etag)

        render_by_etag = self.client.get(
            f"/revisions/notes/{note_id}/revisions/{manual_revision_id}/render-by-etag",
            headers=headers,
            params={"etag": etag},
        )
        self.assertEqual(render_by_etag.status_code, 304, render_by_etag.text)

        create_issue = self.client.post(
            "/issues/",
            headers=headers,
            json={
                "note_id": note_id,
                "revision_id": manual_revision_id,
                "rule": "SPELLING",
                "description": "Found a spelling issue",
                "suggestion": "Replace typo",
                "start_offset": 0,
                "end_offset": 3,
            },
        )
        self.assertEqual(create_issue.status_code, 201, create_issue.text)
        issue_id = create_issue.json()["id"]

        get_issue = self.client.get(f"/issues/{issue_id}", headers=headers)
        self.assertEqual(get_issue.status_code, 200, get_issue.text)

        list_issues = self.client.get("/issues/", headers=headers)
        self.assertEqual(list_issues.status_code, 200, list_issues.text)
        self.assertTrue(any(row["id"] == issue_id for row in list_issues.json()))

        update_issue = self.client.put(
            f"/issues/{issue_id}",
            headers=headers,
            json={"suggestion": "Use the corrected word"},
        )
        self.assertEqual(update_issue.status_code, 200, update_issue.text)
        self.assertEqual(update_issue.json()["suggestion"], "Use the corrected word")

        audit = self.client.post(
            f"/revisions/notes/{note_id}/revisions/{manual_revision_id}/grammar/audit",
            headers=headers,
            json={"provider": "languagetool", "language": "en-US", "level": "picky"},
        )
        self.assertEqual(audit.status_code, 200, audit.text)
        audit_payload = audit.json()
        self.assertEqual(audit_payload["issue_count"], 1)

        apply_fixes = self.client.post(
            f"/revisions/notes/{note_id}/revisions/{manual_revision_id}/grammar/apply-fixes",
            headers=headers,
            json={"min_severity": "info", "strategy": "first_suggestion"},
        )
        self.assertEqual(apply_fixes.status_code, 200, apply_fixes.text)
        apply_payload = apply_fixes.json()
        self.assertIsNotNone(apply_payload["new_revision_id"])
        self.assertIn("This", apply_payload["patched_content_md"])

        summarize_note = self.client.post(
            f"/summarize/notes/{note_id}",
            headers=headers,
            json={"style": "paragraph", "language": "en", "max_tokens": 128},
        )
        self.assertEqual(summarize_note.status_code, 200, summarize_note.text)
        self.assertEqual(summarize_note.json()["scope"], "note")
        self.assertEqual(summarize_note.json()["model"], "fake-summarizer")

        summarize_folder = self.client.post(
            f"/summarize/folders/{folder_id}",
            headers=headers,
            json={"style": "bullets", "language": "en", "max_tokens": 128},
        )
        self.assertEqual(summarize_folder.status_code, 200, summarize_folder.text)
        self.assertEqual(summarize_folder.json()["scope"], "folder")

        restore_revision = self.client.post(
            f"/revisions/notes/{note_id}/revisions/{initial_revision_id}/restore",
            headers=headers,
        )
        self.assertEqual(restore_revision.status_code, 200, restore_revision.text)
        self.assertEqual(restore_revision.json()["note_id"], note_id)

        delete_issue = self.client.delete(f"/issues/{issue_id}", headers=headers)
        self.assertEqual(delete_issue.status_code, 200, delete_issue.text)

        delete_note = self.client.delete(f"/notes/{note_id}", headers=headers)
        self.assertEqual(delete_note.status_code, 200, delete_note.text)

        deleted_note_lookup = self.client.get(f"/notes/{note_id}", headers=headers)
        self.assertEqual(deleted_note_lookup.status_code, 404, deleted_note_lookup.text)

        delete_tag = self.client.delete(f"/tags/{tag_id}", headers=headers)
        self.assertEqual(delete_tag.status_code, 200, delete_tag.text)

        delete_folder = self.client.delete(f"/folders/{folder_id}", headers=headers)
        self.assertEqual(delete_folder.status_code, 200, delete_folder.text)

        delete_user = self.client.delete(f"/users/{user_id}")
        self.assertEqual(delete_user.status_code, 200, delete_user.text)


if __name__ == "__main__":
    unittest.main()
