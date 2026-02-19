"""API Discovery script for email task creation and scheduling.

Tests the Apollo API endpoints to discover the exact parameters needed
for creating, updating, and scheduling email tasks.

Usage:
    APOLLO_API_KEY=<key> uv run python test_email_task_discovery.py

Requires a real contact ID and optionally a user ID.
Set TEST_CONTACT_ID and TEST_USER_ID environment variables.
"""

import asyncio
import json
import os
import sys

from apollo import ApolloClient

CONTACT_ID = os.getenv("TEST_CONTACT_ID", "")
USER_ID = os.getenv("TEST_USER_ID", "")

if not os.getenv("APOLLO_API_KEY"):
    print("ERROR: APOLLO_API_KEY not set")
    sys.exit(1)

if not CONTACT_ID:
    print("ERROR: TEST_CONTACT_ID not set. Set it to a real contact ID.")
    sys.exit(1)


def pp(label: str, data: object) -> None:
    """Pretty print a result."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(json.dumps(data, indent=2, default=str))


async def delay(seconds: int = 12) -> None:
    """Rate-limit friendly delay."""
    print(f"\n  ... waiting {seconds}s (rate limit) ...")
    await asyncio.sleep(seconds)


async def main() -> None:
    print("EMAIL TASK API DISCOVERY")
    print(f"Contact ID: {CONTACT_ID}")
    print(f"User ID:    {USER_ID or '(not set)'}")

    async with ApolloClient() as client:
        # ============================================================
        # Experiment 1: Create email task with type outreach_manual_email
        # ============================================================
        print("\n\n>>> Experiment 1: Create email task")
        create_result = await client.create_task(
            contact_ids=[CONTACT_ID],
            note="Discovery test email task",
            type="outreach_manual_email",
            priority="medium",
            **({"user_id": USER_ID} if USER_ID else {}),
        )
        pp("Create task response", create_result)

        task_id = None
        if isinstance(create_result, dict):
            task_id = create_result.get("task", {}).get("id")
            if not task_id and isinstance(create_result.get("id"), str):
                task_id = create_result["id"]

        print(f"\n  Extracted task_id: {task_id}")
        rl = client.rate_limit_status
        print(f"  Rate limits - hourly left: {rl.get('hourly_left')}")

        if not task_id:
            print("\n  WARNING: Could not extract task_id from response.")
            print("  The create task endpoint may only return 'true'.")
            print("  Trying to find the task via search...")

            await delay()

            # Search for recently created tasks
            search_result = await client.search_tasks(
                task_type_cds=["outreach_manual_email"],
                limit=5,
            )
            pp(
                "Search tasks response",
                {
                    "total": search_result.total,
                    "items": [
                        {
                            "id": t.id,
                            "type": t.type,
                            "status": t.status,
                            "note": t.note,
                            "emailer_message": {
                                "id": t.emailer_message.id if t.emailer_message else None,
                                "subject": t.emailer_message.subject if t.emailer_message else None,
                                "status": t.emailer_message.status if t.emailer_message else None,
                            }
                            if t.emailer_message
                            else None,
                        }
                        for t in search_result.items
                    ],
                },
            )

            if search_result.items:
                task_id = search_result.items[0].id
                print(f"\n  Using task_id from search: {task_id}")

        if not task_id:
            print("\n  FATAL: Could not find task. Aborting.")
            return

        await delay()

        # ============================================================
        # Experiment 2: GET single task
        # ============================================================
        print("\n\n>>> Experiment 2: GET /tasks/{id}")
        try:
            get_result = await client._get(f"/tasks/{task_id}")
            pp("GET task response", get_result)
        except Exception as e:
            print(f"  GET /tasks/{{id}} FAILED: {e}")
            print("  Trying GET /tasks/{id} with different response key...")

        await delay()

        # ============================================================
        # Experiment 3: PUT /tasks/{id} with emailer_message
        # ============================================================
        print("\n\n>>> Experiment 3: PUT /tasks/{id} with emailer_message")
        try:
            put_result = await client._request(
                "PUT",
                f"/tasks/{task_id}",
                json={
                    "emailer_message": {
                        "subject": "Discovery Test Subject",
                        "body_text": "<p>Discovery test body.</p>",
                    },
                },
            )
            pp("PUT task with emailer_message response", put_result)
        except Exception as e:
            print(f"  PUT /tasks/{{id}} with emailer_message FAILED: {e}")

        await delay()

        # ============================================================
        # Experiment 4: Try direct update of emailer_message fields on task
        # ============================================================
        print("\n\n>>> Experiment 4: PUT /tasks/{id} with flat subject/body fields")
        try:
            put_result2 = await client._request(
                "PUT",
                f"/tasks/{task_id}",
                json={
                    "subject": "Discovery Test Subject v2",
                    "body_text": "<p>Discovery test body v2.</p>",
                },
            )
            pp("PUT task with flat fields response", put_result2)
        except Exception as e:
            print(f"  PUT /tasks/{{id}} with flat fields FAILED: {e}")

        await delay()

        # ============================================================
        # Experiment 5: Check if emailer_message has its own endpoint
        # ============================================================
        print("\n\n>>> Experiment 5: Check emailer_message endpoint")
        # First, get the task to find the emailer_message id
        try:
            task_data = await client._get(f"/tasks/{task_id}")
            em = task_data.get("task", task_data).get("emailer_message", {})
            em_id = em.get("id") if em else None
            print(f"  emailer_message id: {em_id}")

            if em_id:
                await delay()
                try:
                    em_result = await client._request(
                        "PUT",
                        f"/emailer_messages/{em_id}",
                        json={
                            "subject": "Discovery Test Subject v3",
                            "body_text": "<p>Discovery test body v3.</p>",
                        },
                    )
                    pp("PUT emailer_messages response", em_result)
                except Exception as e:
                    print(f"  PUT /emailer_messages/{{id}} FAILED: {e}")
            else:
                print("  No emailer_message id found, skipping.")
        except Exception as e:
            print(f"  Could not get task for emailer_message check: {e}")

        await delay()

        # ============================================================
        # Experiment 6: Verify final state
        # ============================================================
        print("\n\n>>> Experiment 6: Final task state")
        try:
            final = await client._get(f"/tasks/{task_id}")
            pp("Final task state", final)
        except Exception as e:
            print(f"  Final GET failed: {e}")

        # ============================================================
        # Summary
        # ============================================================
        print("\n\n" + "=" * 60)
        print("  DISCOVERY COMPLETE")
        print("=" * 60)
        rl = client.rate_limit_status
        print(f"  Rate limits - hourly left: {rl.get('hourly_left')}")
        print(f"  Task ID used: {task_id}")
        print("\n  NOTE: Clean up the test task manually in Apollo UI.")


if __name__ == "__main__":
    asyncio.run(main())
